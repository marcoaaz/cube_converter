
'''
main_functions.py

File containing set of dependencies and functions to use within main_script.py. 

Created: 2-Aug-2025, Marco Acevedo
Updated: 12-Sep-2025

Documentation:
https://stackoverflow.com/questions/3103178/how-to-get-the-system-info-with-python
https://superfastpython.com/multiprocessing-pool-initializer/

'''
#Dependencies

#Basic
import os
import sys
import gc
import psutil
import shutil 
import re
import glob
import math
import time

import numpy as np
import pandas as pd
import json

from itertools import compress
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

#Write ome
import uuid
from ome_types.model import Channel
from ome_types.model import Image
from ome_types.model import OME
from ome_types.model import Pixels
from ome_types.model import TiffData

#Javabridge
import javabridge 
import atexit
#Note: to avoid console print issue, I modified javabridge/locate.py --> find_javahome()

#Bioformats
import bioformats
import bioformats.formatreader as F
from bioformats import metadatatools

#relative to script path
from helperFunctions.mkdir_options import mkdir2 
from ray_tracing_module import calculate_statistic, img_rescaled, channel_uint8

#VIPS
add_dll_dir = getattr(os, 'add_dll_directory', None) #Windows=True
vipsbin = 'c:/vips-dev-8.16/bin' #r'c:\vips-dev-8.16\bin'
if getattr(sys, 'frozen', False):	# Running in a PyInstaller bundle		

	bundle_dir = os.path.abspath(os.path.dirname(__file__)) #relative path	
	vip_dlls = os.path.join(bundle_dir, 'vips')

else: # for regular Python environment
	vip_dlls = vipsbin

if callable(add_dll_dir): 
	add_dll_dir(vip_dlls)
else:
	os.environ['PATH'] = os.pathsep.join((vip_dlls, os.environ['PATH']))

import pyvips
# print("vips version: " + str(pyvips.version(0))+"."+str(pyvips.version(1))+"."+str(pyvips.version(2)))


#region Helper functions

def parse_system_info():
	RAM_percentage = 50 #for JVM

	#number of cores
	available_cores = os.cpu_count()

	#RAM tuple
	svmem = psutil.virtual_memory()
	process_RAM = get_size(RAM_percentage, svmem.total) #'31.66GB'
	available_RAM = get_size(100, svmem.available) 

	return available_cores, process_RAM, available_RAM

def get_size(RAM_percentage, bytes, suffix=""): #suffix="B"

	"""
	Scale bytes to its proper format
	e.g:
		1253656 => '1.20MB'
		1253656678 => '1.17GB'
	"""	

	factor = 1024
	for unit in ["", "K", "M", "G", "T", "P"]:
		if bytes < factor:
			bytes2 = bytes*(RAM_percentage/100)

			return1 = f"{bytes:.0f}{unit}{suffix}"
			return2 = f"{bytes2:.0f}{unit}{suffix}"

			return return1, return2 #bytes:.2f
		bytes /= factor

def init_worker(assigned_RAM):	
	
	#BioFormats path list
	if getattr(sys, 'frozen', False): #within a PyInstaller bundle
		
		#assuming it sits next to main.py
		bundle_dir = os.path.abspath(os.path.dirname(__file__)) #relative path
		# bundle_dir = sys._MEIPASS	

		#when: --add-data "path/to/site-packages/bioformats/jars:bioformats/jars"	
		bioformats_jars = [os.path.join(bundle_dir, 'bioformats', 'jars', os.path.basename(jar)) for jar in bioformats.JARS]
		jars2 = [os.path.join(bundle_dir, 'javabridge', 'jars', os.path.basename(jar)) 
		   for jar in bioformats.JARS] #patch
		bioformats_jars.extend(jars2)

	else: #within Python environment
		bioformats_jars = bioformats.JARS

	# print(bioformats_jars)

	# Initialize JVM in each worker process
	javabridge.start_vm(
		class_path= bioformats_jars, 
		max_heap_size=assigned_RAM, 
		run_headless=True
		) #'24G'
	#add -Djava.awt.headless=true just to be safe for server/HPC environments

	#Avoid printing terminal warnings
	try:
		myloglevel="ERROR" 
		rootLoggerName = javabridge.get_static_field("org/slf4j/Logger","ROOT_LOGGER_NAME", "Ljava/lang/String;")
		rootLogger = javabridge.static_call("org/slf4j/LoggerFactory","getLogger", "(Ljava/lang/String;)Lorg/slf4j/Logger;", rootLoggerName)
		logLevel = javabridge.get_static_field("ch/qos/logback/classic/Level",myloglevel, "Lch/qos/logback/classic/Level;")
		javabridge.call(rootLogger, "setLevel", "(Lch/qos/logback/classic/Level;)V", logLevel)
	except:
		pass # Fallback if logback isn't in the jar provided

def delete_intermediate_files(workingDir1):
	#custom to sub-folder names

	all_folders = glob.glob(f"{workingDir1}/*", recursive = False) #only in current dir 	
	delete_list = ['bf_tiles', 'rt_ppl', 'rt_xpl']
	for folder_path in all_folders:
		folder_name = os.path.basename(folder_path)

		if folder_name in delete_list:							
			try:
				shutil.rmtree(folder_path)
			except OSError as e:
				print(f"Error deleting {folder_path}: {e}")		

def qListWidget_list(list_widget):
	#function for GUI

	item_texts = []
	for i in range(list_widget.count()):
		item_texts.append(list_widget.item(i).text())
	return item_texts

#endregion

#region Read metadata

def metadata_reader_section(image_path, dirname1):
	
	basename1 = os.path.basename(image_path).replace(".vsi", "")	

	#Read part of metadata
	xml1 = bioformats.get_omexml_metadata(image_path, url=None)      
	xml2 = bioformats.OMEXML(xml1)

	#Generate Reader
	
	omeMeta = metadatatools.createOMEXMLMetadata() #for output
	ImageReader = F.make_image_reader_class()
	reader = ImageReader()
	reader.setMetadataStore(omeMeta)
	reader.setId(image_path)            

	#Learning about levels
	series_count = reader.getSeriesCount()

	values = []
	acquisition = 0
	for series in range(series_count): #pyramid levels
		
		reader.setSeries(series)
		
		sizeX = reader.getSizeX()
		sizeY = reader.getSizeY()
		sizeC = reader.getSizeC()
		sizeZ = reader.getSizeZ()		  
		sizeT = reader.getSizeT()  
		type = reader.getPixelType() #bit depth

		#Z-stacks convention (only first layer explains image pyramid)
		levelZero = xml2.image(series)
		
		image_ID = levelZero.ID
		layer_name = levelZero.Name		
		dimension_order = levelZero.Pixels.DimensionOrder

		try: #special metadata
		
			acquisition_date = levelZero.AcquisitionDate		
			pixel_calibration_sel = levelZero.Pixels.PhysicalSizeX #equal to Y
		except:
			acquisition_date = ""
			pixel_calibration_sel = 0		

		#Finding scans (Slide scanner convention)
		sub_str1 = ".vsi #"		
		sub_str2 = "label"
		sub_str3 = "overview"
		sub_str4 = "macro image"
		condition1 = (layer_name.find(sub_str1) == -1)
		condition2 = ( (layer_name.find(sub_str2) != -1) or 
				(layer_name.find(sub_str3) != -1) or 
				(layer_name.find(sub_str4) != -1) )		
		condition = condition1 & ~condition2
		
		if condition:
			acquisition = acquisition + 1
			acquisition_out = acquisition			
		elif condition2:
			acquisition_out = 0
		else:			
			acquisition_out = acquisition

		values.append([series, 
				 image_ID, layer_name, dimension_order, acquisition_date, pixel_calibration_sel, 
				 sizeX, sizeY, sizeC, sizeZ, sizeT, type, acquisition_out])	

	df_sizes = pd.DataFrame(values, columns =['series', 
										   'ID', 'Name', 'dimension_order', 'acquisition_date', 'pixel_calibration_sel',
										   'sizeX', 'sizeY', 'sizeC', 'sizeZ', 'sizeT', 'type',
										   'Acquisition'
										   ])

	#Saving in readable format	
	file1 = os.path.join(dirname1, f'pyramid_sizes_{basename1}.csv')
	df_sizes.to_csv(file1, sep=',', index=False)

	reader.close()	
	atexit.register(javabridge.kill_vm)
	

def read_metadata_function(image_path, dirname1, assigned_RAM):	

	#Save VSI metadata as CSV
	args = [(image_path, dirname1)] #list of tuples (note: strings are unpacked)		
	
	pool = multiprocessing.Pool(processes=1, 
							 initializer=init_worker, initargs=(assigned_RAM,))	
	pool.starmap(metadata_reader_section, args)	

#endregion	


#region Re-write pyramids

def save_tiles_function(image_path, conditions, sel_level, tileSize, n_cores, assigned_RAM, dirname1):	

	#Default	
	tileSizeX = tileSize #512 		

	#Output folders
	basename1 = os.path.basename(image_path).replace(".vsi", "")
	folder1 = os.path.join(dirname1, f"processed_level{sel_level:02d}_{basename1}")
	folder2 = os.path.join(folder1, "bf_tiles")	
	table_file1 = os.path.join(folder2, "tileConfiguration.csv")
	table_file2 = os.path.join(folder2, "tileConfiguration2.csv")

	#Checkpoint 2: final output exists
	if os.path.exists(table_file2):
		print(f"Final stack table found at {table_file2}. Skipping all computation.")
		return pd.read_csv(table_file2)
	
	mkdir2(folder1)
	mkdir2(folder2)

	#Checkpoint 1: intermediate output exists
	if os.path.exists(table_file1):
		print(f"Initial tile configuration found at {table_file1}. Skipping generation.")
		tile_table = pd.read_csv(table_file1)
	
	else:	
		#Read metadata (user readable)	
		file1 = os.path.join(dirname1, f'pyramid_sizes_{basename1}.csv')
		file2 = os.path.join(folder1, 'experimental_metadata.json')

		#Learn about experiment
		df_sizes = pd.read_csv(file1, sep=',')
			
		acquisition_list = df_sizes["Acquisition"]
		idx = (acquisition_list == 1) #convention (similar acquisitions)

		dimension_orders = df_sizes.loc[idx, "dimension_order"].to_list()
		pixel_sizes = df_sizes.loc[idx, "pixel_calibration_sel"].to_list()	
		dimension_order = dimension_orders[0]	
		pixel_size = pixel_sizes[0]  
		pixel_size_sel = pixel_size*(2**sel_level)
		
		n_levels = np.sum(idx)
		if n_levels < sel_level + 1:
			print('Select a lower pyramid level')
			sys.exit()

		#Find all scans
		_, indices = np.unique(acquisition_list, return_index=True) #sorted	
		indices2 = indices[1:]	#all  

		indices3 = indices2 + sel_level		
		layer_names = [df_sizes.loc[x, "Name"] for x in indices2]
		series_span = indices3.tolist() #images requested from data tree and pyramids	

		#Subset microscopy modalities (time-saver)	
		ASW_prefix = ["ppl", "xpl", "RL BF"]
		if conditions[0]: #all
			ASW_prefix2 = ASW_prefix
		else:
			chosen = []
			if conditions[1]: #ppl
				chosen.append(ASW_prefix[0])
			if conditions[2]: #xpl
				chosen.append(ASW_prefix[1])
			if conditions[3]: #RL BF
				chosen.append(ASW_prefix[2])
			ASW_prefix2 = chosen	

		#Matching scan names
		all_matches = [next((p for p in ASW_prefix2 if p in layer), None) for layer in layer_names]
		layer_logical = [m is not None for m in all_matches]

		layer_names2 = list(compress(layer_names, layer_logical))
		series_span2 = list(compress(series_span, layer_logical))
		matched_prefixes2 = list(compress(all_matches, layer_logical))	

		#Return user feedback
		found_set = set(matched_prefixes2)
		prefix_not_found_logical = [p not in found_set for p in ASW_prefix2]
		missing_elements = [p for p, not_found in zip(ASW_prefix2, prefix_not_found_logical) if not_found]
		if any(prefix_not_found_logical):
			print(f"Warning: The optical scan does not contain: {missing_elements}")		

		#Save process metadata
		data = {
			"image_path": image_path, "tileSizeX": tileSizeX, "dimension_order": dimension_order,
			"sel_level": sel_level, "pixel_size_sel": pixel_size_sel,
			"layer_names": layer_names2, "series_span": series_span2, "matched_prefixes": matched_prefixes2,		
			}
		
		with open(file2, 'w') as f:
			json.dump(data, f, indent=4) # indent for pretty printing	
		
		print('Generating tile configuration..')
		tile_table = generate_tile_config_BF(data, folder2)	
		tile_table.to_csv(table_file1, sep=',', encoding='utf-8', index=False, header=True) #save CSV

	print('Saving individual scans as TIF..')
	args = ((image_path, series, tile_table) for series in series_span2)		
	
	#Context manager to handle the pool lifecycle
	with multiprocessing.Pool(
		processes=n_cores, 
		initializer=init_worker, 
		initargs=(assigned_RAM,)
	) as pool:		
		#Convert generator to list to ensure all args are ready
		task_args = list(args) 		
		montage_paths = pool.starmap(reader_section, task_args)	
	
	print('Saving modality stacks..')
	new_tile_table = save_modality_stack_bigtiff(tile_table, n_cores_max=2)	#n_cores=2 loses sequential access	
	new_tile_table.to_csv(table_file2, index=False) #save CSV

	return new_tile_table

def save_modality_stack_bigtiff(tile_table, n_cores_max=2):
	
	parentDir = os.path.dirname(tile_table.iloc[0]['filepath'])
	tileSize = int(tile_table.iloc[0]['W'])
	modalities = tile_table['prefix'].unique()
	n_channels = 3
	
	#calculating cache
	available_ram = psutil.virtual_memory().available
	target_cache_bytes = available_ram * 0.4
	tile_size_bytes = tileSize * tileSize * 3 * 4
	dynamic_max_tiles = int(target_cache_bytes / tile_size_bytes) #8000
	#Note: >8000 tiles for 25/32 GB RAM (~2 GB buffer) prevents I/O bottlenecks with SSD at flat 90% use

	def process_single_modality(modality): #closure: nested function see parent variables

		output_name = f'stack_{modality}.tif'
		output_file = os.path.join(parentDir, output_name)
		tile_table_mod = tile_table[tile_table['prefix'] == modality].copy()
		montage_paths = tile_table_mod['filepath'].unique().tolist()

		if len(montage_paths) > 1:			
			
			# Map indices
			path_to_indices = {p: (i*n_channels, (i*n_channels)+n_channels) 
							  for i, p in enumerate(montage_paths)}
			
			tile_table_mod['stack_path'] = output_file
			tile_table_mod['from_index'] = tile_table_mod['filepath'].map(lambda x: path_to_indices[x][0])
			tile_table_mod['to_index'] = tile_table_mod['filepath'].map(lambda x: path_to_indices[x][1])
						
			pages = [pyvips.Image.new_from_file(path, access="sequential") for path in montage_paths]
			image_stack = pages[0].bandjoin(pages[1:])

			#tile cache			
			image_stack = image_stack.tilecache(tile_width= tileSize, tile_height= tileSize, max_tiles=dynamic_max_tiles)

			image_final = image_stack.copy(interpretation="multiband")
			
			image_final.tiffsave(output_file, 
								bigtiff=True, tile=True, 
								tile_width=tileSize, tile_height=tileSize,
								compression="none") 
			#compression=none if disk is fast, try "lz4" if disk is slow
			
			#Clear up RAM
			del pages, image_stack, image_final
			pyvips.cache_set_max(0)
			pyvips.cache_set_max(100)
			gc.collect()
			
			print(f"BigTIFF saved for {output_name}")

			return tile_table_mod
		else:
			tile_table_mod['stack_path'] = None

			return tile_table_mod
	
	# Parallelizing 2 lets one read while the other writes. Don't go to 8—your disk will choke.
	with ThreadPoolExecutor(max_workers= n_cores_max) as executor:
		updated_rows = list( executor.map(process_single_modality, modalities) )

	new_tile_table = pd.concat(updated_rows).reset_index(drop=True)	

	return new_tile_table

#endregion

#region BioFormats section

def generate_tile_config_BF(data, folder2):
	#Read VSI and save tiles following Fiji's Stitching plugin

	init_worker('2G')

	#Default
	image_path = data["image_path"] 
	series_span2 = data["series_span"] 
	layer_names2 = data["layer_names"] 
	matched_prefixes2 = data["matched_prefixes"]   
	tileSizeX = data["tileSizeX"] 
	tileSizeY = tileSizeX #convetion

	#Generate Reader			
	omeMeta = metadatatools.createOMEXMLMetadata() #for output	
	ImageReader = F.make_image_reader_class()
	
	reader = ImageReader()
	reader.setMetadataStore(omeMeta)
	reader.setId(image_path)

	image_count = reader.getImageCount() #Data tree = 1; z-stack = # of planes		  	
	image_span = range(image_count)

	all_rows = []

	for i, series in enumerate(series_span2): #XPL		
		layer_temp = layer_names2[i] #scan in VS200
		prefix_temp = matched_prefixes2[i] #modality

		reader.setSeries(series)
		sizeX = reader.getSizeX()
		sizeY = reader.getSizeY()			

		for image in image_span: 		
			
			#output file
			# basename2 = f"series{series}_z{image}.tif"
			basename2 = f"{layer_temp}_z{image}.tif"
			output_1 = os.path.join(folder2, basename2)	    		
		
			#Calculate tiles
			nXTiles = int(math.floor(sizeX / tileSizeX))
			nYTiles = int(math.floor(sizeY / tileSizeY))
			if nXTiles * tileSizeX != sizeX:
				nXTiles = nXTiles + 1
			if nYTiles * tileSizeY != sizeY:
				nYTiles = nYTiles + 1

			#Calculate grid (pythonic order)
			for row_idx, y in enumerate(range(0, nYTiles)):
				for col_idx, x in enumerate(range(0, nXTiles)):
					# The x and y coordinates for the current tile
					tileX = x * tileSizeX
					tileY = y * tileSizeY

					current_w = tileSizeX
					if (tileX + tileSizeX) >= sizeX:
						current_w = sizeX - tileX
						
					current_h = tileSizeY
					if (tileY + tileSizeY) >= sizeY:
						current_h = sizeY - tileY	

					all_rows.append({
						'filepath': output_1,
						'layer': layer_temp, 
						'prefix': prefix_temp,
						'series': series,
						'image': image,
						'x': col_idx, 
						'y': row_idx,
						'W': current_w,
						'H': current_h,
						'pixel_x': tileX, # Start pixel X
						'pixel_y': tileY  # Start pixel Y
					})
		
	# Create DataFrame
	tile_table = pd.DataFrame(all_rows)
	tile_table2 = tile_table.sort_values(['series', 'image', 'y', 'x'], ascending=[True, True, True, True])	

	reader.close()	
	atexit.register(javabridge.kill_vm)

	return tile_table2

def reader_section(image_path, series, tile_table):		
	#Read VSI and save tiles following Fiji's Stitching plugin

	#Subsetting
	table_sub = tile_table[tile_table['series'] == series]
	
	#Generate Reader			
	omeMeta = metadatatools.createOMEXMLMetadata() #for output	
	
	ImageReader = F.make_image_reader_class()
	reader = ImageReader()
	reader.setMetadataStore(omeMeta)
	reader.setId(image_path)

	image_count = reader.getImageCount() #Data tree = 1; z-stack = # of planes		  	
	image_span = range(image_count)

	reader.setSeries(series)
	
	montage_paths = []
	for image in image_span: #XPL		

		table_sub1 = table_sub[table_sub['image'] == image]		
		n_tiles = table_sub1.shape[0]

		tiles_accross = table_sub1["x"].unique().max() + 1
		montage_path = table_sub1.iloc[0]['filepath']
		tileSize = table_sub1.iloc[0]['W'] #top left tile		
		
		image_tiles = []
		for k in range(0, n_tiles):
			tileX = table_sub1.iloc[k]['pixel_x']
			tileY = table_sub1.iloc[k]['pixel_y']
			current_w = table_sub1.iloc[k]['W']
			current_h = table_sub1.iloc[k]['H']
			
			#Read tiles				
			buf = reader.openBytesXYWH(image, tileX, tileY, current_w, current_h)
			buf.shape = (current_h, current_w, 3) #interleaved (according to VSI metadata
			
			vips_tile = pyvips.Image.new_from_array(buf)                            
			
			image_tiles.append(vips_tile)

			#clear up RAM
			del buf, vips_tile 
			
		#Build montage				
		image_stitched = pyvips.Image.arrayjoin(image_tiles, across= tiles_accross)
		
		image_stitched.tiffsave(montage_path, 
						bigtiff=True, 
						tile=True, 
						tile_width = tileSize,
						tile_height = tileSize,
						compression="none",
						predictor="none") 
		
		del image_stitched
		gc.collect() #for each image

		montage_paths.append(montage_path)

	reader.close()
	
	atexit.register(javabridge.kill_vm)

	return montage_paths
	
#endregion

#region Ray Tracing

def ray_tracing_function(tile_table, modality_list, statistic_list, percentOut, n_cores, workingDir1):  		

	#destination
	path0 = os.path.join(workingDir1, 'montages_rt_bigtiff')
	mkdir2(path0)

	montage_paths = [] #for next function

	for modality_item in modality_list:
		print(f'Running {modality_item}..') 

		output_folder = os.path.join(workingDir1, f"rt_{modality_item}")
		mkdir2(output_folder)

		tile_table2 = tile_table[tile_table['prefix'] == modality_item] 
		z_list = tile_table2['image'].unique()              

		for sel_stats in statistic_list:
			condition_rescale = sel_stats in ["std", "minIndex", "maxIndex", "edges", "modulation"] 
			
			for z in z_list:    
				
				#Checkpoint 1: skip if montage already exists
				file_output = f"{modality_item}_{sel_stats}_z{z}.tif"
				output_path = os.path.join(path0, file_output)  

				if os.path.exists(output_path):
					print(f"Skipping: {file_output} already exists.")
					montage_paths.append(output_path)
					continue
	
				print(f"Computing: modality={modality_item}, z={z}, calculation={sel_stats}..")
				tile_table3 = tile_table2[tile_table2['image'] == z] #.copy()
				
				#quick metadata
				y_list = sorted(tile_table3['y'].unique())
				tileSizeX = tile_table3.iloc[0]['W']
				tileSizeY = tile_table3.iloc[0]['H']

				# Sub-folder for temporary strips to manage I/O for large magnifications
				strip_folder = os.path.join(output_folder, f"strips_z{z:03.0f}_{sel_stats}")
				mkdir2(strip_folder)								
				
				# Stitch horizontal image strips vertically to avoid I/O and resource bottlenecks
				with multiprocessing.Pool(processes=n_cores) as pool:
					for y in y_list:
						
						#Checkpoint 2: 
						strip_file = os.path.join(strip_folder, f"strip_y{y:03.0f}.v") #tif
						#Note: *.v format has zero compression overhead and provides efficient random access												

						tile_table_row = tile_table3[tile_table3['y'] == y].sort_values('x')
						x_list_row = tile_table_row['x'].unique()

						args = ((tile_table_row, x, y, sel_stats) for x in x_list_row)
						
						#Process row
						results = pool.starmap(process_tile_rt, args)                       
						
						#Stitch row strip
						image_tiles = [pyvips.Image.new_from_array(r) for r in results]
						row_stitched = pyvips.Image.arrayjoin(image_tiles, across=len(results))
						
						# Save strip to disk to clear RAM for high-res objectives
						row_stitched.write_to_file(strip_file)							
						
						del results, image_tiles, row_stitched
						

				#Stitching: Load strips back using sequential access
				print(f"Stitching: modality={modality_item}, z={z}, calculation={sel_stats}..")
				
				strip_paths = [os.path.join(strip_folder, f"strip_y{y:03.0f}.v") for y in y_list]
				row_strips = [pyvips.Image.new_from_file(p, access="sequential") for p in strip_paths] #cannot be access="sequential"
				image_stitched = pyvips.Image.arrayjoin(row_strips, across=1)				
				# Using access="sequential" here is what allows 100GB+ montages

				save_rt_bigtiff(image_stitched, condition_rescale, percentOut, tileSizeX, tileSizeY, output_path)

				# Cleanup Z-plane resources
				del row_strips, image_stitched
				pyvips.cache_set_max(0) #release file handles to prevent 
				pyvips.cache_set_max(100)				
				gc.collect()				
				
				montage_paths.append(output_path)	
		 
	del tile_table
	gc.collect()

	return montage_paths

def process_tile_rt(tile_table3, x, y, sel_stats):                           
	
	#Subsetting (fast)
	table_index = (tile_table3['x'] == x) & (tile_table3['y'] == y)
	tile_table4 = tile_table3.loc[table_index]  
	
	series_span = tile_table4['series'].unique()
	n_layers = len(series_span)     
	
	stack_path = tile_table4.iloc[0]['stack_path']              
	pixel_x = tile_table4.iloc[0]['pixel_x']
	pixel_y = tile_table4.iloc[0]['pixel_y']
	tile_width = tile_table4.iloc[0]['W']
	tile_height = tile_table4.iloc[0]['H']      
	
	#Load tile
	tile_image = pyvips.Image.new_from_file(stack_path, access="random")                                    
	tile_image2 = tile_image.crop(pixel_x, pixel_y, tile_width, tile_height)            
	
	del tile_image

	#Main analysis
	shape1 = (tile_height, tile_width, n_layers, 3) #for reshape
	tile_temp2 = tile_image2.numpy().astype(np.float32).reshape(shape1).transpose(0, 1, 3, 2)   
	tile_temp3 = calculate_statistic(tile_temp2, sel_stats) #np array    
	
	#clear up RAM
	del tile_temp2 
	gc.collect()                    
	
	return tile_temp3
			
#endregion

#region OME TIFF converter

def ready_for_OME(channel_list, file_output, dimension_order, dimension_sizes, pixel_size_sel):		
	# Note: to convert to OME, we need a tall, thin mono image with page-height set to
	# indicate where the joins are. https://github.com/libvips/pyvips/issues/502
	
	#default
	filename_without_extension = os.path.splitext(file_output)[0]	
	size_y = dimension_sizes[1]	

	#Write XML
	ome = OME(uuid=f"urn:uuid:{uuid.uuid4()}")

	pixels = Pixels(
		dimension_order=dimension_order,
		physical_size_x=pixel_size_sel,
		physical_size_y=pixel_size_sel,
		physical_size_z="1",
		size_x= dimension_sizes[0],
		size_y= size_y,
		size_c= dimension_sizes[2],
		size_z= dimension_sizes[3],		
		size_t= dimension_sizes[4],
		type='uint8' #default pixel type
		)

	pixels.channels.extend([
		Channel(color="-16777216", name="R", samples_per_pixel=1),
		Channel(color="16711680", name="G", samples_per_pixel=1),
		Channel(color="65280", name="B", samples_per_pixel=1)])				
	
	# file_output_info = f"montage_series{series}_z{z}.tif" #informative to QuPath
	file_output_info = filename_without_extension #file_output (the extension is not an issue)
	ome.images.append(Image(name= file_output_info, pixels=pixels))

	tiff_uuid = f"urn:uuid:{uuid.uuid4()}"
	tiff = TiffData(
		first_c=0, first_t=0, first_z=0, plane_count=1,
		uuid=TiffData.UUID(value=tiff_uuid, file_name= file_output),
		) 	
	#Notes:
	#file_output requires extension
	#file_name cannot change

	pixels.tiff_data_blocks.append(tiff)
	temp_ome = ome.to_xml() 							

	#stack vertically ready for OME 
	montage_roll = pyvips.Image.arrayjoin(channel_list, across= 1) #for OME (only)
	montage_roll = montage_roll.copy()
	montage_roll.set_type(pyvips.GValue.gint_type, "page-height", size_y)			
	montage_roll.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)
	
	#clear up RAM
	del channel_list
	gc.collect()

	return montage_roll

#endregion

#region Reformat as OME

def process_single_montage(path, path0, tileSizeX, tileSizeY, dimension_order, pixel_size_sel):
	#"picklable"

	try:
		file_output = os.path.basename(path)
		output_path = os.path.join(path0, file_output)

		image_stitched = pyvips.Image.new_from_file(path, access="sequential")
		
		montage = channel_uint8(image_stitched)

		dimension_sizes = [montage.width, montage.height, 3, 1, 1]
		montage_roll = ready_for_OME(
			montage.bandsplit(), 
			file_output, 
			dimension_order, 
			dimension_sizes, 
			pixel_size_sel
		)

		montage_roll.tiffsave(
			output_path, compression="none", 
			tile=True, tile_width=tileSizeX, tile_height=tileSizeY,
			pyramid=True, subifd=True, bigtiff=True
			) #"lzw"
		
		return f"Success: {file_output}"
	except Exception as e:
		return f"Error on {path}: {str(e)}"


def process_wrapper(args):
	#to handle the tuple of arguments
	return process_single_montage(*args)

def join_original_tiles_function(tile_table, n_cores=4):

	tile_table2 = tile_table.drop_duplicates(subset=['filepath'])

	# Path Setup
	a = tile_table2.iloc[0]['filepath']
	workingDir1 = os.path.dirname(os.path.dirname(a))   
	path0 = os.path.join(workingDir1, 'montages_original')
	if not os.path.exists(path0):
		os.makedirs(path0)

	# Metadata Recovery
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')
	with open(path1, 'r') as f:
		data = json.load(f)

	#Checkpoint: Filter out old montages
	args_list = []
	skipped_files = []

	for row in tile_table2.itertuples():
		# Based on process_single_montage: file_output = os.path.basename(path)
		file_name = os.path.basename(row.filepath)
		expected_output_path = os.path.join(path0, file_name)

		if os.path.exists(expected_output_path):
			skipped_files.append(file_name)
			continue
		
		#Prepare arguments
		args_list.append((
			row.filepath, path0, 
			data["tileSizeX"], data["tileSizeX"], 
			data["dimension_order"], data["pixel_size_sel"]
			))	

	#Use the wrapper function instead of the lambda
	with ProcessPoolExecutor(max_workers=n_cores) as executor:
		results = list(executor.map(process_wrapper, args_list))	

	gc.collect()


def save_rt_bigtiff(image_stitched, condition_rescale, percentOut, tileSizeX, tileSizeY, output_path):        	

	#Add cache to handle the global statistics scan without saturating RAM
	available_ram = psutil.virtual_memory().available
	target_cache_bytes = available_ram * 0.2 #0.4
	tile_size_bytes = tileSizeX * tileSizeY * 3 * 4
	dynamic_max_tiles = int(target_cache_bytes / tile_size_bytes) #8000
	#Note: >8000 tiles for 25/32 GB RAM (~2 GB buffer) prevents I/O bottlenecks with SSD at flat 90% use

	image_stitched = image_stitched.tilecache(tile_width=tileSizeX, tile_height=tileSizeY, max_tiles=dynamic_max_tiles)

	if condition_rescale:                                                               
		montage = img_rescaled(image_stitched, percentOut) 
	else:
		montage = channel_uint8(image_stitched)                                                                   
	
	del image_stitched

	#Save flat tiled image	
	montage.tiffsave(output_path, compression="lzw", tile=True, 
				tile_width=tileSizeX, tile_height=tileSizeY,
				pyramid=False, subifd=False, bigtiff=True) #"lzw"
	#Note: LZW is a single-threaded compression algorithm allowing the SSD to write less bytes 
	#and reduce data friction. This is the I/O throttling paradox

	del montage 
	gc.collect()
	

def join_rt_tiles_function(rt_montage_paths, n_cores=4):
	
	# Path Setup
	a = rt_montage_paths[0]
	workingDir1 = os.path.dirname(os.path.dirname(a))   
	path0 = os.path.join(workingDir1, 'montages_rt')
	if not os.path.exists(path0):
		os.makedirs(path0)

	# Metadata Recovery
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')
	with open(path1, 'r') as f:
		data = json.load(f)

	#Checkpoint: Filter out old montages
	args_list = []
	skipped_files = []

	for path in rt_montage_paths:
		# Based on process_single_montage: file_output = os.path.basename(path)
		file_name = os.path.basename(path)
		expected_output_path = os.path.join(path0, file_name)

		if os.path.exists(expected_output_path):
			skipped_files.append(file_name)
			continue
		
		#Prepare arguments
		args_list.append((
			path, path0, 
			data["tileSizeX"], data["tileSizeX"], 
			data["dimension_order"], data["pixel_size_sel"]
			))	

	#Use the wrapper function instead of the lambda
	with ProcessPoolExecutor(max_workers=n_cores) as executor:
		results = list(executor.map(process_wrapper, args_list))	

	gc.collect()

#endregion


#endregion

#region GUI (2) Z-stack

def read_img_convention(im_temp, file):
	#Ensures most image formats can be read as 
	#3-channel, SamplesPerPixel=3, MetaDataPhotometricInterpretation = RGB (not Monochrome)

	#medicine: drop alpha channel after OpenSlide/PNG (prevents artefacts)
	if im_temp.hasalpha():					
		im_temp = im_temp.flatten()#im_temp[:-1] 
		#4-band VIPS_INTERPRETATION_sRGB    

	n_channels2 = im_temp.bands		

	if n_channels2 == 1:
		plane_list = []

		#force reading
		try:				
			c_count = 3
			for i in range(0, 3):
				
				plane_temp = pyvips.Image.new_from_file(file, page=i)
				plane_list.append(plane_temp)
			
			im_temp2 = plane_list[0].bandjoin(plane_list[1:])
			

		#repeat for compatibility
		except:
			c_count = 1
			plane_list = [im_temp, im_temp, im_temp]
			im_temp2 = plane_list[0].bandjoin(plane_list[1:])

	else:  				
		c_count = n_channels2		
		im_temp2 = im_temp			
		if c_count > 3:
			print('Note that images with >3 channels might cause errors.')

	return im_temp2, c_count

def generate_zStack(fileList2, pixel_size_sel, tileSize, output_path):

	#info
	im_temp = pyvips.Image.new_from_file(fileList2[0]) #lazy loading			
	
	#Default dimensions   		
	tileSizeX = tileSize #512
	tileSizeY = tileSizeX	
	dimension_order = "XYCZT" #equal to original VSI file	
	dimension_sizes = [im_temp.width , im_temp.height, 3, len(fileList2), 1] #3 channels to comply with z-stack

	channel_list = []   
	for file in fileList2:     
		
		im_temp = pyvips.Image.new_from_file(file) 
		#cannot be 'sequential': 'tiff2vips: out of order read'                 						

		im_temp2, c_count_original = read_img_convention(im_temp, file) #		
		
		r, g, b = im_temp2.bandsplit()  
		
		channel_list.append(r) #.copy_memory()
		channel_list.append(g) 
		channel_list.append(b)  

		del im_temp, im_temp2, r, g, b               		
	
	#Save as pyramidal OME-TIFF  	
	file_output = os.path.basename(output_path)	 #requirement		
	montage_roll = ready_for_OME(channel_list, file_output, dimension_order, dimension_sizes, pixel_size_sel)	
	
	montage_roll.tiffsave(output_path, compression="none", tile=True, 
				tile_width= tileSizeX, tile_height=tileSizeY,
				pyramid=True, subifd=True, bigtiff=True) #"lzw"
	
	#clear up RAM
	del channel_list, montage_roll
	gc.collect
	
def generate_individualImages(fileList2, pixel_size_sel, tileSize, output_path):

	output_folder = os.path.dirname(output_path)
	file_output = os.path.basename(output_path)
	filename_without_extension = os.path.splitext(file_output)[0]

	output_folder1 = os.path.join(output_folder, f'{filename_without_extension}_individual')
	mkdir2(output_folder1)

	#info
	im_temp = pyvips.Image.new_from_file(fileList2[0]) #lazy loading			
		

	#Default dimensions   	
	
	dimension_order = "XYCZT" #equal to original VSI file
	tileSizeX = tileSize #512
	tileSizeY = tileSizeX		
	
	for file in fileList2:  		
		
		im_temp = pyvips.Image.new_from_file(file)                  						
		size_x = im_temp.width 
		size_y = im_temp.height					

		im_temp2, c_count_original = read_img_convention(im_temp, file) #not allowed to have 1 channel		
		
		r, g, b = im_temp2.bandsplit()  
		
		channel_list = [r, g, b]  			
	
		#Save as pyramidal OME-TIFF  	
		file_output = os.path.basename(file)	 #requirement		
		file_path = os.path.join(output_folder1, file_output)		
		dimension_sizes = [size_x, size_y, 3, 1, 1]

		montage_roll = ready_for_OME(channel_list, file_output, dimension_order, 
							   dimension_sizes, pixel_size_sel)		
		
		montage_roll.tiffsave(file_path, compression="none", tile=True,
						tile_width= tileSizeX, tile_height=tileSizeY,
						pyramid=True, subifd=True, bigtiff=True) #"lzw"
		
		#clear up RAM
		del im_temp, im_temp2, r, g, b, channel_list, montage_roll
		gc.collect()
		

def generate_dz(fileList2, tileSize, output_path):

	output_folder = os.path.dirname(output_path)
	file_output = os.path.basename(output_path)
	filename_without_extension = os.path.splitext(file_output)[0]

	output_folder1 = os.path.join(output_folder, f'{filename_without_extension}_dz')
	mkdir2(output_folder1)	
	
	for file in fileList2:  		
		
		im_temp = pyvips.Image.new_from_file(file) #lazy loading                 						
		im_temp2, c_count_original = read_img_convention(im_temp, file) #not allowed to have 1 channel		
		
		#Save as pyramidal OME-TIFF  	
		file_output1 = os.path.basename(file)
		filename_without_extension1 = os.path.splitext(file_output1)[0]
		output_folder2 = os.path.join(output_folder1, filename_without_extension1)
		
		im_temp2.dzsave(output_folder2, suffix='.tif', 
						skip_blanks=-1, background=0, 
						depth='onetile', overlap=0, tile_size= tileSize, 
						layout='dz') #Tile overlap in pixels*2, depth= 'one', 'onetile'  	
	 	
		#clear up RAM
		del im_temp, im_temp2
		gc.collect()

	metadata = learn_tileConfiguration(output_folder1)	

	return metadata
	
def generate_flatImages(fileList2, output_path):

	output_folder = os.path.dirname(output_path)
	file_output = os.path.basename(output_path)
	filename_without_extension = os.path.splitext(file_output)[0]

	output_folder1 = os.path.join(output_folder, f'{filename_without_extension}_flat')
	mkdir2(output_folder1)	
	
	for file in fileList2:  		
		
		im_temp = pyvips.Image.new_from_file(file) #lazy loading                 						
		im_temp1, c_count_original = read_img_convention(im_temp, file) #not allowed to have 1 channel						
		
		im_temp2 = im_temp1.copy(interpretation="srgb") #doesnt process pixels

		#Save as flat image  	
		file_output1 = os.path.basename(file)
		filename_without_extension1 = os.path.splitext(file_output1)[0]		
		file_path = os.path.join(output_folder1, filename_without_extension1 + '.tif')		

		#compression="jpeg", 'deflate' (huge files), 'lzw', 'none',		
		# The photometric interpretation will be RGB by default for 3-band uchar images

		im_temp2.tiffsave(file_path, 					
					compression="none", 
					tile=False,
					pyramid=False,  
					bitdepth=8,
					bigtiff=False,
					) #lzw		

		#clear up RAM
		del im_temp, im_temp1, im_temp2
		gc.collect()
	
	return

#endregion

#region Save Deep Zoom tiles

def learn_tileConfiguration(destDir):
	#Note: edited from dimReduction_v2 > functions_pyramids.py
	#..\teresa\trial_2\recoloured_pctOut0.5\test2_dz\91702-Ca_linear_files\0\0_2.tif"
	
	# scan tileset    
	fileList = glob.glob(f"{destDir}/*/*/*_*.tif")
	pattern = re.compile(r".*\\(.+)_files\\(\d+)\\(\d+)_(\d+)\.tif") #edited
	#r".*/(\d+)_(\d+)\.tif" in Linux
	
	out2 = []
	for filename in fileList:
		match = pattern.match(filename)

		if match:     
			#Parsed info
			type = match.group(1)
			level = match.group(2)
			x = match.group(3)
			y = match.group(4)

			#dim
			image_temp = pyvips.Image.new_from_file(filename)
			W = image_temp.width
			H = image_temp.height

			out2.append([filename, type, level, x, y, W, H])

	out3 = np.array(out2) 
	file_table = pd.DataFrame(out3)
	file_table.columns =['filepath', 'type', 'level', 'x', 'y', 'W', 'H']    
	#medicine
	file_table['level'] = file_table['level'].astype(int)
	file_table['x'] = file_table['x'].astype(int)
	file_table['y'] = file_table['y'].astype(int)
	file_table2 = file_table.sort_values(['type', 'level', 'y', 'x'], ascending=[True, True, True, True]) #for pyvips.Image.arrayjoin

	file_name1 = os.path.join(destDir, "tileConfiguration.csv")
	file_table2.to_csv(file_name1, sep=',', encoding='utf-8', index=False, header=True)

	#Console
	tiles_down = int(file_table2['y'].max()) + 1
	tiles_across = int(file_table2['x'].max()) + 1
	print(f"Deep Zoom pyramid with {tiles_down}x{tiles_across} tiles")

	return file_table2
