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
import pandas as pd
import json

import uuid
from ome_types.model import Channel
from ome_types.model import Image
from ome_types.model import OME
from ome_types.model import Pixels
from ome_types.model import TiffData

#relative paths
from helperFunctions.mkdir2 import mkdir1, mkdir2 

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

# workingDir1 = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\processed_Image_nan1-b_10x"
workingDir1 = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\z-stack_zircon\processed_CA24MR-1_second_top"

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
	tileSizeY = data["tileSizeY"]
	layer_names = data["layer_names"]
	series_span = data["series_span"]
	pixel_size_sel = data["pixel_size_sel"]

	#Processing metadata
	# pyramid_sizes = pd.read_csv(path2)

	#Learning tile arrangement
	fileList = glob.glob(f"{workingDir1}/**/*.tif", recursive = False) #only in current dir 	
	pattern = re.compile(r".+\\series(\d+)_z(\d+)\\tile_x(\d+)_y(\d+)\.tif")	
    
	items_str = ['series', 'z', 'x', 'y']
	values = []
	for filename in fileList:		
		match = pattern.match(filename) # scan image set (perfect match needed)      

		item_series = int(match.group(1))
		item_z = int(match.group(2))    
		item_x = int(match.group(3))    
		item_y = int(match.group(4))

		values.append([item_series, item_z, item_x, item_y])

	df = pd.DataFrame(values, columns = items_str)
	df.insert(0, "image_path", fileList, True)
	df1 = df.sort_values(items_str, ascending= [True, True, True, True])
	
	
	# series_list = df1['series'].unique() #all available
	series_list = series_span
	z_list = df1['z'].unique()	

	#Loop (assuming no missing tiles)
	for series, layer_name in zip(series_list, layer_names):
		for z in z_list:
			
			#info
			idx1 = df1['series'] == series
			idx2 = df1['z'] == z
			idx = idx1 & idx2
			df2 = df.loc[idx, :]
            
			y_list = df2['y'].unique()
			x_list = df2['x'].unique()

			image_tiles = []
			for y in y_list:
				for x in x_list:
					idx3 = df1['x'] == x
					idx4 = df1['y'] == y
					idx = idx3 & idx4
					path_temp = df2.loc[idx, 'image_path'].array[0]

					#Load image
					im_temp = pyvips.Image.new_from_file(path_temp)    

					# openslide will add an alpha ... drop it
					if im_temp.hasalpha():
						im_temp = im_temp[:-1]   			

					image_tiles.append(im_temp)
			
			
			tiles_accross = x_list.max() + 1
			montage = pyvips.Image.arrayjoin(image_tiles, across= tiles_accross)
			
			image_width = montage[0].width #image are of = XY size
			image_height = montage[0].height						
			
            #Save as pyramidal OME-TIFF			
			file_output = layer_name + f"_z{z}.tif"
			output_path = os.path.join(workingDir1, file_output)
			
            #Write XML
			ome = OME(uuid=f"urn:uuid:{uuid.uuid4()}")
	
			pixels = Pixels(
                dimension_order=dimension_order,
                physical_size_x=pixel_size_sel,
                physical_size_y=pixel_size_sel,
                physical_size_z="1",
                size_x=image_width,
                size_y=image_height,
                size_z=1,
                size_c=3,
                size_t=1,
                type='uint8'
				)

			pixels.channels.extend([
                Channel(color="-16777216", name="R", samples_per_pixel=1),
                Channel(color="16711680", name="G", samples_per_pixel=1),
                Channel(color="65280", name="B", samples_per_pixel=1)])
			
			file_output_info = f"montage_series{series}_z{z}.tif" #informative to QuPath
			ome.images.append(Image(name= file_output_info, pixels=pixels))

			tiff_uuid = f"urn:uuid:{uuid.uuid4()}"
			tiff = TiffData(
                first_c=0,
                first_t=0,
                first_z=0,
                plane_count=1,
                uuid=TiffData.UUID(value=tiff_uuid, file_name= file_output) 
            ) #file_name cannot change

			pixels.tiff_data_blocks.append(tiff)
			temp_ome = ome.to_xml() 			

            #stack vertically ready for OME 
			montage_roll = pyvips.Image.arrayjoin(montage.bandsplit(), across= 1) #for OME (only)
			montage_roll = montage_roll.copy()
			montage_roll.set_type(pyvips.GValue.gint_type, "page-height", image_height)			
			montage_roll.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)

			montage_roll.tiffsave(output_path, compression="jpeg", tile=True, 
                        tile_width= tileSizeX, tile_height=tileSizeY,
                        pyramid=True, subifd=True)

#endregion



