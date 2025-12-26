
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
import re
import psutil
import glob
import shutil 

import math
import numpy as np
import pandas as pd
import json

from itertools import compress
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
from ray_tracing_module import calculate_statistic, understand_tiling, img_rescaled, channel_uint8

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

	#number of cores
	available_cores = os.cpu_count()

	#RAM tuple
	svmem = psutil.virtual_memory()
	total_RAM = get_size(svmem.total) #'31.66GB'
	available_RAM = get_size(svmem.available) 

	return available_cores, total_RAM, available_RAM

def get_size(bytes, suffix=""): #suffix="B"

	"""
	Scale bytes to its proper format
	e.g:
		1253656 => '1.20MB'
		1253656678 => '1.17GB'
	"""
	
	RAM_percentage = 75 #for JVM

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
	if getattr(sys, 'frozen', False):	# Running in a PyInstaller bundle
		
		#assuming it sits next to main.py
		bundle_dir = os.path.abspath(os.path.dirname(__file__)) #relative path
		# bundle_dir = sys._MEIPASS	

		#when: --add-data "path/to/site-packages/bioformats/jars:bioformats/jars"	
		bioformats_jars = [os.path.join(bundle_dir, 'bioformats', 'jars', os.path.basename(jar)) for jar in bioformats.JARS]
		jars2 = [os.path.join(bundle_dir, 'javabridge', 'jars', os.path.basename(jar)) for jar in bioformats.JARS] #patch
		bioformats_jars.extend(jars2)

	else: # for regular Python environment
		bioformats_jars = bioformats.JARS
	# print(bioformats_jars)

	# Initialize JVM in each worker process
	javabridge.start_vm(class_path= bioformats_jars, max_heap_size=assigned_RAM, run_headless=True) #'24G'
	#javabridge.start_vm(run_headless=True)	

	#Optional (avoids printing terminal warnings):
	myloglevel="ERROR" 
	rootLoggerName = javabridge.get_static_field("org/slf4j/Logger","ROOT_LOGGER_NAME", "Ljava/lang/String;")
	rootLogger = javabridge.static_call("org/slf4j/LoggerFactory","getLogger", "(Ljava/lang/String;)Lorg/slf4j/Logger;", rootLoggerName)
	logLevel = javabridge.get_static_field("ch/qos/logback/classic/Level",myloglevel, "Lch/qos/logback/classic/Level;")
	javabridge.call(rootLogger, "setLevel", "(Lch/qos/logback/classic/Level;)V", logLevel)
	
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

def metadata_reader_section(image_path):

	dirname1 = os.path.dirname(image_path)
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
	

def read_metadata_function(image_path, assigned_RAM):	

	#Save VSI metadata as CSV
	args = [(image_path,)] #list of tuples (note: strings are unpacked)		
	
	pool = multiprocessing.Pool(processes=1, 
							 initializer=init_worker, initargs=(assigned_RAM,))	
	pool.starmap(metadata_reader_section, args)	

#endregion	


#region Save tiles

def save_tiles_function(image_path, sel_level, tileSize, n_cores, assigned_RAM, conditions):	

	#Default
	sizeC = 3 #for optical microscopy
	tileSizeX = tileSize #512 
	tileSizeY = tileSizeX
	# n_cores = 8	#benchmarked

	#Output folders
	dirname1 = os.path.dirname(image_path)
	basename1 = os.path.basename(image_path).replace(".vsi", "")
	folder1 = os.path.join(dirname1, f"processed_level{sel_level:02d}_{basename1}")
	folder2 = os.path.join(folder1, "bf_tiles")
	mkdir2(folder1)
	mkdir2(folder2)

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
	if conditions[0]:
		ASW_prefix2 = ASW_prefix
	else:
		chosen = []
		if conditions[1]:
			chosen.append(ASW_prefix[0])
		if conditions[2]:
			chosen.append(ASW_prefix[1])
		if conditions[3]:
			chosen.append(ASW_prefix[2])
		ASW_prefix2 = chosen	

	#logical list with matches 
	layer_logical = [ any([layer.find(str) != -1 for str in ASW_prefix2 ]) for layer in layer_names ]
	layer_names2 = list(compress(layer_names, layer_logical)) #subset list with logical list		
	series_span2 = list(compress(series_span, layer_logical)) 

	#Save process metadata
	data = {
		"image_path": image_path,        
		"tileSizeX": tileSizeX,
		"tileSizeY": tileSizeY,
		"dimension_order": dimension_order,
		"sel_level": sel_level,
		"pixel_size_sel": pixel_size_sel,
		"layer_names": layer_names2,
		"series_span": series_span2,		
		}
	
	with open(file2, 'w') as f:
		json.dump(data, f, indent=4) # indent for pretty printing	
	
	#Save VSI montage as TIF tiles
	args = ((image_path, series, tileSizeX, sizeC, folder2)
		 for series in series_span2)		
	
	pool = multiprocessing.Pool(processes=n_cores, 
							 initializer=init_worker, initargs=(assigned_RAM,))	
	pool.starmap(reader_section, args)	


def reader_section(image_path, series, tileSizeX, sizeC, folder2):		
	#Read VSI and save tiles following Fiji's Stitching plugin

	#Generate Reader			
	omeMeta = metadatatools.createOMEXMLMetadata() #for output	
	
	ImageReader = F.make_image_reader_class()
	reader = ImageReader()
	reader.setMetadataStore(omeMeta)
	reader.setId(image_path)

	image_count = reader.getImageCount() #Data tree = 1; z-stack = # of planes		  	
	image_span = range(image_count)

	reader.setSeries(series)
	sizeX = reader.getSizeX()
	sizeY = reader.getSizeY()

	#Default
	tileSizeY = tileSizeX	

	for image in image_span: #XPL		
		
		#output folder
		basename2 = f"series{series}_z{image}"
		output_1 = os.path.join(folder2, basename2)	    
		mkdir2(output_1)
	
		#Calculate tiles
		nXTiles = int(math.floor(sizeX / tileSizeX))
		nYTiles = int(math.floor(sizeY / tileSizeY))
		if nXTiles * tileSizeX != sizeX:
			nXTiles = nXTiles + 1
		if nYTiles * tileSizeY != sizeY:
			nYTiles = nYTiles + 1

		#Extract, row-wise (pythonic order)
		for y in range(nYTiles):
			for x in range(nXTiles):
				# The x and y coordinates for the current tile
				tileX = x * tileSizeX
				tileY = y * tileSizeY
				effTileSizeX = tileSizeX
				if (tileX + tileSizeX) >= sizeX:
					effTileSizeX = sizeX - tileX
					
				effTileSizeY = tileSizeY
				if (tileY + tileSizeY) >= sizeY:
					effTileSizeY = sizeY - tileY					
					
				#Read tiles				
				buf = reader.openBytesXYWH(image, tileX, tileY, effTileSizeX, effTileSizeY)
				buf.shape = (effTileSizeY, effTileSizeX, sizeC) #interleaved (see VSI metadata)					

				#Write tiles
				name_str = f'tile_x{x:03.0f}_y{y:03.0f}.tif' #following Fiji's Stitching plugin
				file_temp = os.path.join(output_1, name_str)
				image_output = pyvips.Image.new_from_array(buf)                            
				image_output.write_to_file(file_temp) 
	reader.close()
	
	atexit.register(javabridge.kill_vm)
	
#endregion

#region Ray Tracing

def ray_tracing_function(workingDir1, modality_list, statistic_list, n_cores):	
	# n_cores = 8 #performance of 8-12 flattens

	#Recovering metadata	
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')	

	#Default	
	n_channels = 3 #for optical microscopy
	
	#JSON
	with open(path1, 'r') as f:
		data = json.load(f)

	
	series_span = data["series_span"] 
	layer_names = data["layer_names"] #follows series_span	

	#Learning tile arrangement
	fileList = glob.glob(f"{workingDir1}/**/**/*.tif", recursive = False) #only in current dir 	
	pattern = re.compile(r".+\\series(\d+)_z(\d+)\\tile_x(\d+)_y(\d+)\.tif")			
	
	df1 = understand_tiling(fileList, pattern, workingDir1)

	#Processing metadata	
	z_list = df1['z'].unique() #assuming it applies to all the file		
	
	#logical list within a list
	series_lists = [ [layer.find(modality_str) != -1 for layer in layer_names] for modality_str in modality_list ]
	
	values2 = [] #table

	for items, modality_str in zip(series_lists, modality_list):
		print(modality_str)

		#Output folder
		output_folder = os.path.join(workingDir1, f"rt_{modality_str}")
		mkdir2(output_folder)

		series_span2 = list(compress(series_span, items)) #subset list with logical list	 			 
		n_layers = len(series_span2)
		
		#Getting x-y information		        
		series_1 = series_span2[0] #assuming selection covers only one level
		idx1 = df1['series'] == series_1        
		df_a = df1.loc[idx1, :] #df
		y_list = df_a['y'].unique()
		x_list = df_a['x'].unique()
		
		#Loop (assuming no missing tiles)	
		for sel_stats in statistic_list:
			for z in z_list:	

				idx1 = df1['z'] == z
				df2 = df1.loc[idx1, :] #shortened

				#Process tiles in parallel
				args = ((df2, x, y, z, series_span2, sel_stats, modality_str, n_channels, n_layers, output_folder)
					for y in y_list
					for x in x_list)					
				
				pool = multiprocessing.Pool(processes=n_cores)	
				values1 = pool.starmap(process_tile_rt, args)				
				
				values2.extend(values1)					
			
	#Write setup	
	items_str2 = ['z', 'x', 'y', 'width', 'height', 'image_path', 'statistic', 'modality']	
	df_rt = pd.DataFrame(values2, columns = items_str2)		
	df_rt.to_csv(os.path.join(workingDir1, 'files2.csv'), index=False)      

def process_tile_rt(df2, x, y, z, series_span2, sel_stats, modality_str, n_channels, n_layers, output_folder):							

	idx2 = df2['x'] == x
	idx3 = df2['y'] == y
	idx = idx2 & idx3

	df3 = df2.loc[idx, :] #shortened					 
	
	tile_width = df3['width'].array[0] #when dissimilar tiles
	tile_height = df3['height'].array[0]
	shape = (tile_height, tile_width, n_channels, n_layers) 

	tile_temp = np.zeros(shape, dtype= np.float32) #pre-allocate						
	
	for series, i in zip(series_span2, range(n_layers)):
		# print(f"{x}, {y}, {z}, {series}")						

		idx4 = df3['series'] == series							
		path_temp = df3.loc[idx4, 'image_path'].array[0]

		#Load image
		im_temp = pyvips.Image.new_from_file(path_temp)    							
		tile_temp[:, :, :, i] = im_temp.numpy()							

	tile_temp2 = calculate_statistic(tile_temp, sel_stats)						
	
	
	#Write tiles
	name_str = f'tile_x{x:03.0f}_y{y:03.0f}_z{z:03.0f}_{sel_stats}.tif' #Stitching plugin
	file_temp = os.path.join(output_folder, name_str)
	
	image_output = pyvips.Image.new_from_array(tile_temp2) #requires float32                            
	image_output.write_to_file(file_temp)  

	values_tile = [z, x, y, tile_width, tile_height, file_temp, sel_stats, modality_str]
			
	return values_tile
			
#endregion

#region Write OME

def ready_for_OME(channel_list, file_output, dimension_order, dimension_sizes, pixel_size_sel):		
	# Note: to convert to OME, we need a tall, thin mono image with page-height set to
	# indicate where the joins are. https://github.com/libvips/pyvips/issues/502
	
	filename_without_extension = os.path.splitext(file_output)[0]

	size_x = dimension_sizes[0]
	size_y = dimension_sizes[1]
	size_c = dimension_sizes[2]
	size_z = dimension_sizes[3]
	size_t = dimension_sizes[4]

	#Write XML
	ome = OME(uuid=f"urn:uuid:{uuid.uuid4()}")

	pixels = Pixels(
		dimension_order=dimension_order,
		physical_size_x=pixel_size_sel,
		physical_size_y=pixel_size_sel,
		physical_size_z="1",
		size_x=size_x,
		size_y=size_y,
		size_c=size_c,
		size_z=size_z,		
		size_t=size_t,
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
		first_c=0,
		first_t=0,
		first_z=0,
		plane_count=1,
		uuid=TiffData.UUID(value=tiff_uuid, file_name= file_output) #file_output requires extension
	) #file_name cannot change

	pixels.tiff_data_blocks.append(tiff)
	temp_ome = ome.to_xml() 							

	#stack vertically ready for OME 
	montage_roll = pyvips.Image.arrayjoin(channel_list, across= 1) #for OME (only)
	montage_roll = montage_roll.copy()
	montage_roll.set_type(pyvips.GValue.gint_type, "page-height", size_y)			
	montage_roll.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)

	return montage_roll

#endregion

#region Join ray tracing tiles

def join_rt_tiles_function(workingDir1, statistic_list, percentOut):

	#Output folder
	path0 = os.path.join(workingDir1, 'montages_rt')
	mkdir2(path0)

	#Recovering metadata	
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')
	path2 = os.path.join(workingDir1, 'files2.csv')	
	
	#JSON
	with open(path1, 'r') as f:
		data = json.load(f)

	dimension_order = data["dimension_order"]
	tileSizeX = data["tileSizeX"]
	tileSizeY = tileSizeX	
	pixel_size_sel = data["pixel_size_sel"]

	#Processing metadata
	df_rt = pd.read_csv(path2)
	x_list = df_rt["x"].unique()
	y_list = df_rt["y"].unique()
	z_list = df_rt["z"].unique()	
	modality_list = df_rt["modality"].unique()

	if not statistic_list: #empty
		statistic_list = df_rt["statistic"].unique()

	tiles_accross = x_list.max() + 1 #assuming same pyramid level

	#Loop (assuming no missing tiles)	
	for modality_str in modality_list:		

		for sel_stats in statistic_list:
			
			print(f"{modality_str} montage {sel_stats}")
			condition = (sel_stats == "std") or (sel_stats == "minIndex") or (sel_stats == "maxIndex")			

			for z in z_list:
				
				idx1 = df_rt["z"] == z
				idx2 = df_rt["statistic"] == sel_stats
				idx3 = df_rt["modality"] == modality_str
				idx = (idx1 & idx2 & idx3)
				df_rt2 = df_rt.loc[idx, :] #shortened
		
				image_tiles = []
				for y in y_list:
					for x in x_list:
						idx4 = df_rt2["x"] == x
						idx5 = df_rt2["y"] == y
						idx_b = (idx4 & idx5)

						path_temp = df_rt2.loc[idx_b, 'image_path'].array[0]

						#Load image
						im_temp = pyvips.Image.new_from_file(path_temp)     #, access="sequential"					

						image_tiles.append(im_temp)
			
				#Build montage				
				image_stitched = pyvips.Image.arrayjoin(image_tiles, across= tiles_accross)
				
				#Optional steps:
				
				if condition:						
					#Rescale to uint8 (with extra computational cost)
					montage = img_rescaled(image_stitched, percentOut)		
				
				else:
					montage = channel_uint8(image_stitched)								

				size_x = montage.width #image are of = XY size
				size_y = montage.height
				size_c = 3
				
				# #(1) Crop background borders
				# left, top, width, height = image_stitched.find_trim(threshold=0.001, background=[0])
				# image_stitched2 = image_stitched.crop(left, top, width, height) #modify accordingly  									
				
				#Save as pyramidal OME-TIFF			
				file_output = f"{modality_str}_{sel_stats}_z{z}.tif"
				output_path = os.path.join(path0, file_output)
				
				dimension_sizes = [size_x, size_y, size_c, 1, 1] #[X, Y, C, Z, T]				
				montage_roll = ready_for_OME(montage.bandsplit(), file_output, dimension_order, dimension_sizes, pixel_size_sel)

				montage_roll.tiffsave(output_path, compression="lzw", tile=True, 
							tile_width= tileSizeX, tile_height=tileSizeY,
							pyramid=True, subifd=True, bigtiff=True) #output > 4 GB requires 64-bit big tiff format

#endregion

#region Join original tiles

def join_original_tiles_function(workingDir1, conditions):

	#Output folder
	path0 = os.path.join(workingDir1, 'montages_original')
	mkdir2(path0)

	#Recovering metadata	
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')		
	
	#JSON
	with open(path1, 'r') as f:
		data = json.load(f)

	dimension_order = data["dimension_order"]
	tileSizeX = data["tileSizeX"]
	tileSizeY = data["tileSizeY"]	
	pixel_size_sel = data["pixel_size_sel"]	
	layer_names = data["layer_names"]
	series_list = data["series_span"]	

	#Remembering tile arrangement
	fileList = glob.glob(f"{workingDir1}/**/**/*.tif", recursive = False) #only in current dir 	
	pattern = re.compile(r".+\\series(\d+)_z(\d+)\\tile_x(\d+)_y(\d+)\.tif")	
	
	df1	= understand_tiling(fileList, pattern, workingDir1)	
		
	z_list = df1['z'].unique()	
	x_list = df1["x"].unique()
	y_list = df1['y'].unique()
	tiles_accross = x_list.max() + 1 #assuming same pyramid level

	#Loop (assuming no missing tiles)
	for series, layer_name in zip(series_list, layer_names):
		for z in z_list:
			
			#info
			idx1 = df1['series'] == series
			idx2 = df1['z'] == z
			idx = idx1 & idx2

			df2 = df1.loc[idx, :] #df			

			image_tiles = []
			for y in y_list:
				for x in x_list:
					idx3 = df2['x'] == x
					idx4 = df2['y'] == y
					idx_b = idx3 & idx4
					path_temp = df2.loc[idx_b, 'image_path'].array[0]

					#Load image
					im_temp = pyvips.Image.new_from_file(path_temp)    					  			

					image_tiles.append(im_temp)
			
			#Build montage
			
			image_stitched = pyvips.Image.arrayjoin(image_tiles, across= tiles_accross)
			
			#Optional steps:	
			montage = channel_uint8(image_stitched)			

			size_x = montage.width #image are of = XY size
			size_y = montage.height
			size_c = 3

			#(1) Crop background borders
			# left, top, width, height = image_stitched.find_trim(threshold=0.001, background=[0])
			# montage = image_stitched.crop(left, top, width, height) #modify accordingly								

			#Save as pyramidal OME-TIFF			
			file_output = layer_name + f"_z{z}.tif"
			output_path = os.path.join(path0, file_output)
			
			dimension_sizes = [size_x, size_y, size_c, 1, 1] #[size_c, size_z, size_t]
			montage_roll = ready_for_OME(montage.bandsplit(), file_output, dimension_order, dimension_sizes, pixel_size_sel)
			#optional: add QuPath information allowing to pass filename 'series'			

			montage_roll.tiffsave(output_path, compression="jpeg", tile=True, 
						tile_width= tileSizeX, tile_height=tileSizeY,
						pyramid=True, subifd=True, bigtiff=True)

#endregion

#region Z-stack

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
	size_x = im_temp.width 
	size_y = im_temp.height		

	#Default dimensions   
	c_count = 3 #to comply with z-stack
	z_count = len(fileList2)
	t_count = 1
	dimension_order = "XYCZT" #equal to original VSI file
	tileSizeX = tileSize #512
	tileSizeY = tileSizeX	

	dimension_sizes = [size_x, size_y, c_count, z_count, t_count] 

	channel_list = []   
	for file in fileList2:     
		
		im_temp = pyvips.Image.new_from_file(file) #cannot be 'sequential': 'tiff2vips: out of order read'                 						
		im_temp2, c_count_original = read_img_convention(im_temp, file) #		
		
		r, g, b = im_temp2.bandsplit()  
		
		channel_list.append(r)
		channel_list.append(g) 
		channel_list.append(b)                 		
	
	#Save as pyramidal OME-TIFF  	
	file_output = os.path.basename(output_path)	 #requirement		
	montage_roll = ready_for_OME(channel_list, file_output, dimension_order, dimension_sizes, pixel_size_sel)
	
	
	montage_roll.tiffsave(output_path, compression="lzw", tile=True, 
				tile_width= tileSizeX, tile_height=tileSizeY,
				pyramid=True, subifd=True, bigtiff=True) #"lzw"

def generate_individualImages(fileList2, pixel_size_sel, tileSize, output_path):

	output_folder = os.path.dirname(output_path)
	file_output = os.path.basename(output_path)
	filename_without_extension = os.path.splitext(file_output)[0]

	output_folder1 = os.path.join(output_folder, f'{filename_without_extension}_individual')
	mkdir2(output_folder1)

	#info
	im_temp = pyvips.Image.new_from_file(fileList2[0]) #lazy loading			
	size_x = im_temp.width 
	size_y = im_temp.height		

	#Default dimensions   	
	z_count = 1
	t_count = 1
	dimension_order = "XYCZT" #equal to original VSI file
	tileSizeX = tileSize #512
	tileSizeY = tileSizeX	
	
	c_count = 3 #forced
	dimension_sizes = [size_x, size_y, c_count, z_count, t_count]
	
	
	for file in fileList2:  		
		
		im_temp = pyvips.Image.new_from_file(file)                  						
		im_temp2, c_count_original = read_img_convention(im_temp, file) #not allowed to have 1 channel		
		
		r, g, b = im_temp2.bandsplit()  
		
		channel_list = []  	
		channel_list.append(r)
		channel_list.append(g) 
		channel_list.append(b)     	   		 		
	
		#Save as pyramidal OME-TIFF  	
		file_output = os.path.basename(file)	 #requirement		
		file_path = os.path.join(output_folder1, file_output)
		montage_roll = ready_for_OME(channel_list, file_output, dimension_order, dimension_sizes, pixel_size_sel)		
		
		montage_roll.tiffsave(file_path, compression="lzw", tile=True, 
					tile_width= tileSizeX, tile_height=tileSizeY,
					pyramid=True, subifd=True, bigtiff=True) #"lzw"
		

def generate_dz(fileList2, pixel_size_sel, tileSize, output_path):

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
	 	
	metadata = learn_tileConfiguration(output_folder1)	

	return metadata
	
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