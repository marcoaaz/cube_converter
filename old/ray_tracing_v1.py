# -*- coding: utf-8 -*-
"""
join_tiles_v2.py

Produces a montage from the Bio-Formats exported tiles in TIF

Documentation:
my previous scripts

#Created: 14-Aug-25, Marco Acevedo
#Updated: 

#Notes:

developed for 
workingDir1 = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\processed_CA24MR-1_second_top"

"""

import os
import glob
import re
import numpy as np
import pandas as pd

import json
from itertools import compress

import uuid
from ome_types.model import Channel
from ome_types.model import Image
from ome_types.model import OME
from ome_types.model import Pixels
from ome_types.model import TiffData

#relative paths
from helperFunctions.mkdir2 import mkdir1, mkdir2 
from ray_tracing_module import calculate_statistic

#VIPS
vipsbin = r'c:\vips-dev-8.16\bin'
add_dll_dir = getattr(os, 'add_dll_directory', None)
if callable(add_dll_dir):
    add_dll_dir(vipsbin)
else:
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))

import pyvips
print("vips version: " + str(pyvips.version(0))+"."+str(pyvips.version(1))+"."+str(pyvips.version(2)))

#region User input

workingDir1 = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\processed_Image_nan1-b_10x"
# workingDir1 = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\z-stack_zircon\processed_CA24MR-1_second_top"

modality_list = ['ppl', 'xpl'] #assuming ideal acquisition
sel_stats = 'max'

#endregion


#region PYVIPS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 	

	#Recovering metadata	
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')
	path2 = os.path.join(workingDir1, 'pyramid_sizes.csv')

	#Default
	pixel_type = u'uint8' #for optical microscopy 
	n_channels = 3 #for optical microscopy
	
	#JSON
	with open(path1, 'r') as f:
		data = json.load(f)

	dimension_order = data["dimension_order"]
	tileSizeX = data["tileSizeX"]
	tileSizeY = tileSizeX
	pixel_size_sel = data["pixel_size_sel"]
	series_span = data["series_span"] 
	layer_names = data["layer_names"] #follows series_span	

	#Learning tile arrangement
	fileList = glob.glob(f"{workingDir1}/**/*.tif", recursive = False) #only in current dir 	
	pattern = re.compile(r".+\\series(\d+)_z(\d+)\\tile_x(\d+)_y(\d+)\.tif")	
    
	items_str = ['series', 'z', 'x', 'y', 'width', 'height', 'image_path']
	items_str2 = ['z', 'x', 'y', 'width', 'height', 'image_path', 'statistic', 'modality']
	
	values = []
	for filename in fileList:		
		match = pattern.match(filename) # scan image set (perfect match needed)      
		
		if match is None:
			continue

		item_series = int(match.group(1))
		item_z = int(match.group(2))    
		item_x = int(match.group(3))    
		item_y = int(match.group(4))

		#image size
		im_temp = pyvips.Image.new_from_file(filename) #must be an image
		item_width = im_temp.width
		item_height = im_temp.height

		values.append([item_series, item_z, item_x, item_y, item_width, item_height, filename])

	df = pd.DataFrame(values, columns = items_str)	
	df1 = df.sort_values(items_str, ascending= [True, True, True, True, True, True, True])
	
	df1.to_csv(os.path.join(workingDir1, 'files1.csv'), index=False)

	#Processing metadata	
	z_list = df1['z'].unique() #assuming it applies to all the file		
	
	series_lists = [ [layer.find(modality_str) != -1 for layer in layer_names] for modality_str in modality_list ]
	
	values2 = [] #table

	for items, modality_str in zip(series_lists, modality_list):
		print(modality_str)

		#Output folder
		output_folder = os.path.join(workingDir1, f"rt_{modality_str}")
		mkdir2(output_folder)

		series_span2 = list(compress(series_span, items))		
		layer_names2 = list(compress(layer_names, items))
		n_layers = len(series_span2)
		
		#Getting x-y information		        
		series_1 = series_span2[0] #assuming selection covers only one level
		idx1 = df1['series'] == series_1        
		df_a = df.loc[idx1, :]
		y_list = df_a['y'].unique()
		x_list = df_a['x'].unique()
        
		#Loop (assuming no missing tiles)	

		for z in z_list:		
			for y in y_list:
				for x in x_list:
					
					idx2 = df1['z'] == z
					idx3 = df1['x'] == x
					idx4 = df1['y'] == y
					idx = idx2 & idx3 & idx4								

					df2 = df1.loc[idx, :] #shortened					 
					tile_width = df1.loc[idx, 'width'].array[0]
					tile_height = df1.loc[idx, 'height'].array[0]

					shape = (tile_height, tile_width, n_channels, n_layers) #pre-allocate
					tile_temp = np.zeros(shape, dtype= np.float32)
					
					for series, i in zip(series_span2, range(n_layers)):
						# print(f"{x}, {y}, {z}, {series}")						

						idx1 = df2['series'] == series							
						path_temp = df2.loc[idx1, 'image_path'].array[0]

						#Load image
						im_temp = pyvips.Image.new_from_file(path_temp)    							
						tile_temp[:, :, :, i] = im_temp.numpy()		
					

					tile_temp2 = np.max(tile_temp, axis= 3)
					
					#Write tiles
					name_str = f'tile_x{x:03.0f}_y{y:03.0f}_z{z:03.0f}_{sel_stats}.tif' #Stitching plugin
					file_temp = os.path.join(output_folder, name_str)
					
					image_output = pyvips.Image.new_from_array(tile_temp2)                            
					image_output.write_to_file(file_temp)  

					values2.append([z, x, y, tile_width, tile_height, file_temp, sel_stats, modality_str])
				
		
	#Write setup		
	df_rt = pd.DataFrame(values2, columns = items_str2)		
	df_rt.to_csv(os.path.join(workingDir1, 'files2.csv'), index=False)               
                

#endregion



