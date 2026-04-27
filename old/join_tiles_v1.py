
import os
import sys
import json
import glob
import re

import matplotlib.pyplot as plt
import math
import pandas as pd

#VIPS
vipsbin = r'c:\vips-dev-8.16\bin'
add_dll_dir = getattr(os, 'add_dll_directory', None)
if callable(add_dll_dir):
    add_dll_dir(vipsbin)
else:
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))

import pyvips
print("vips version: " + str(pyvips.version(0))+"."+str(pyvips.version(1))+"."+str(pyvips.version(2)))



workingDir1 = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\processed_CA24MR-1_second_top"

#region PYVIPS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 

	fileList = glob.glob(f"{workingDir1}/**/*.tif", recursive = False) #only in current dir 	
	pattern = re.compile(r".+\\series(\d+)_z(\d+)\\tile_x(\d+)_y(\d+)\.tif")

	#Learning arrangement
    
	items_str = ['series', 'z', 'x', 'y']
	values = []
	for filename in fileList:
		print(filename)
		match = pattern.match(filename) # scan image set (perfect match needed)      

		item_series = int(match.group(1))
		item_z = int(match.group(2))    
		item_x = int(match.group(3))    
		item_y = int(match.group(4))

		values.append([item_series, item_z, item_x, item_y])

	df = pd.DataFrame(values, columns = items_str)
	df.insert(0, "image_path", fileList, True)
	df1 = df.sort_values(items_str, ascending= [True, True, True, True])

	series_list = df1['series'].unique()
	z_list = df1['z'].unique()	
	
	#Loop (assuming no missing tiles)
	for series in series_list:
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
			
			#stack vertically ready for OME 
			tiles_accross = x_list.max() + 1
			montage = pyvips.Image.arrayjoin(image_tiles, across= tiles_accross)

			image_width = montage[0].width #image are of = XY size
			image_height = montage[0].height			
			print('Final Image dimentions(WxHxC):', image_width, image_height, 3)

			file_output = os.path.join(workingDir1, f"montage_series{series}_z{z}.tif")

			montage.write_to_file(file_output, compression="lzw", tile=True, 
                 tile_width=512, tile_height=512,  
                 pyramid=True, subifd=True)

      

# #endregion

