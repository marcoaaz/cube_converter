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
from ray_tracing_module import img_rescaled

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
percentOut_dsaImage = 0.5

#endregion


#region PYVIPS

if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 	

	#Output folder
	path0 = os.path.join(workingDir1, 'montages_rt')
	mkdir2(path0)

	#Recovering metadata	
	path1 = os.path.join(workingDir1, 'experimental_metadata.json')
	path2 = os.path.join(workingDir1, 'files2.csv')

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

	#Processing metadata
	df_rt = pd.read_csv(path2)
	x_list = df_rt["x"].unique()
	y_list = df_rt["y"].unique()
	z_list = df_rt["z"].unique()
	statistic_list = df_rt["statistic"].unique()
	modality_list = df_rt["modality"].unique()

	tiles_accross = x_list.max() + 1 #assuming same pyramid level

	#Loop (assuming no missing tiles)	
	for modality_str in modality_list:
		for sel_stats in statistic_list:
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

						path_temp = df_rt.loc[idx_b, 'image_path'].array[0]

						#Load image
						im_temp = pyvips.Image.new_from_file(path_temp, access="sequential")    					

						image_tiles.append(im_temp)
			
				#Build montage				
				image_stitched = pyvips.Image.arrayjoin(image_tiles, across= tiles_accross)
				
				#Optional steps:
				montage = image_stitched
				
				# #(1) Crop background borders
				# left, top, width, height = image_stitched.find_trim(threshold=0.001, background=[0])
				# image_stitched2 = image_stitched.crop(left, top, width, height) #modify accordingly  
				
				# #(2) Rescale brightness
				# montage = img_rescaled(image_stitched2, percentOut_dsaImage)

				#region OME

				#Save as pyramidal OME-TIFF			
				file_output = f"{modality_str}_{sel_stats}_z{z}.tif"
				output_path = os.path.join(path0, file_output)

				image_width = montage[0].width #image are of = XY size
				image_height = montage[0].height													

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
				
				# file_output_info = f"montage_series{series}_z{z}.tif" #informative to QuPath
				file_output_info = file_output
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

				#endregion

				#stack vertically ready for OME 
				montage_roll = pyvips.Image.arrayjoin(montage.bandsplit(), across= 1) #for OME (only)
				montage_roll = montage_roll.copy()
				montage_roll.set_type(pyvips.GValue.gint_type, "page-height", image_height)			
				montage_roll.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)

				montage_roll.tiffsave(output_path, compression="lzw", tile=True, 
							tile_width= tileSizeX, tile_height=tileSizeY,
							pyramid=True, subifd=True)

#endregion



