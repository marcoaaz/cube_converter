# -*- coding: utf-8 -*-
"""
save_tiles_v1.py

Script to save a VSI z-stack as a series of tiles for a specific pyramid level. 
The script should be followed by 'join_tiles_v2.py'.

Designed to work with 
image_path = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\CA24MR-1_second_top.vsi"

This version works around an ImageReader issue:
javabridge.jutil.JavaException: Image plane too large. Only 2GB of data can be extracted at one time. You can work around the problem by opening the plane in tiles; for further details, see: https://docs.openmicroscopy.org/bio-formats/7.3.1/about/bug-reporting.html#common-issues-to-check   

Notes:
javabridge installation can fail: Microsoft Visual C++ 14.0 or greater is required. "Microsoft C++ Build Tools"

#Documentation:
#https://pypi.org/project/pyvips/
#https://pythonhosted.org/python-bioformats/
Previous work (Marco): https://github.com/libvips/libvips/discussions/2446

CZI with Bioformats
https://forum.image.sc/t/python-bioformats-not-able-to-correctly-open-an-image/96600/12

https://forum.image.sc/t/qupath-bioformats-high-compression-efficiency/58982/3

Tifffile (engine of python-bioformats) cannot write OME TIFF SubIDFs
https://forum.image.sc/t/python-bioformats-write-image-6d-images-series-handling/28633/7

Write pyramidal OME TIFF from pyvips: Here’s a slightly updated conversion script for libvips 8.14:
https://forum.image.sc/t/writing-qupath-bio-formats-compatible-pyramidal-image-with-libvips/51223/13

Alternatives to python-bioformats 
https://forum.image.sc/t/ongoing-support-for-python-bioformats/49683/14

Writing TiffData (that is missing in the pyvips solution)
https://forum.image.sc/t/setting-up-ome-xml-for-a-new-microscope-from-scratch/62116/15
https://github.com/hzwirnmann/tcf_to_ometiff/blob/main/tcf_to_ometiff/tcf_to_ometiff.py
https://docs.openmicroscopy.org/ome-model/6.2.2/ome-tiff/specification.html#the-tiffdata-element

#Created: 14-Aug-25, Marco Acevedo
#Updated: 

#Notes:

#Opening output in ImageJ 
Plugins > BioFormats Import*
run("Make Composite");
run("Stack to RGB");
*issue in ImageJ console (warning): Using TiffReader to determine the number of planes.

"""
#region Dependencies

import os
import sys

import json
import math
import numpy as np
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

import javabridge
import bioformats
import bioformats.formatreader as F
from bioformats import metadatatools

#relative paths
from helperFunctions.mkdir2 import mkdir1, mkdir2 

#endregion

#Input
# image_path = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\Image_nan1-b_10x.vsi"

image_path = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\z-stack_zircon\CA24MR-1_second_top.vsi"
sel_level = 3 #pyramid level

#series=pyramid (if z-stack), e.g., level 3 has >7K pixels 

#region BIOFORMATS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows)	      

	#Default
	sizeC = 3 #for optical microscopy
	tileSizeX = 512 
	tileSizeY = 512 

	#Output folder
	dirname1 = os.path.dirname(image_path)
	basename1 = os.path.basename(image_path).replace(".vsi", "")
	folder1 = os.path.join(dirname1, "processed_" + basename1)	

	#Read metadata (user readable)	

	file1 = os.path.join(folder1, 'pyramid_sizes.csv')
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

	unique_elements, indices = np.unique(acquisition_list, return_index=True) #sorted
	unique_elements2 = unique_elements[1:]				
	indices2 = indices[1:]	
	indices3 = indices2 + sel_level		
	layer_names = [df_sizes.loc[x, "Name"] for x in indices2]
	series_span = indices3.tolist() #images requested from data tree and pyramids
	
	#OLD (manual edition):
	# sel_series = 9 
	# series_span = range(sel_series, sel_series + 1)

	data = {
		"image_path": image_path,        
		"tileSizeX": tileSizeX,
		"tileSizeY": tileSizeY,
		"dimension_order": dimension_order,
		"sel_level": sel_level,
		"pixel_size_sel": pixel_size_sel,
		"series_span": series_span, 
		"layer_names": layer_names,
		}
	
	with open(file2, 'w') as f:
		json.dump(data, f, indent=4) # indent for pretty printing	

	#region Read the tiles	

	#Generate Reader

	javabridge.start_vm(class_path=bioformats.JARS, max_heap_size='24G', run_headless=True)

	omeMeta = metadatatools.createOMEXMLMetadata() #for output
	ImageReader = F.make_image_reader_class()
	reader = ImageReader()
	reader.setMetadataStore(omeMeta)
	reader.setId(image_path)            		
	
	image_count = reader.getImageCount() #Data tree = 1; z-stack = # of planes		  	
	image_span = range(image_count)
	
	
	for series in series_span:	

		reader.setSeries(series)
		sizeX = reader.getSizeX()
		sizeY = reader.getSizeY()
		
		for image in image_span: #XPL		
			
			#output folder
			basename2 = f"series{series}_z{image}"
			output_1 = os.path.join(folder1, basename2)	    
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
					name_str = f'tile_x{x:03.0f}_y{y:03.0f}.tif' #Stitching plugin
					file_temp = os.path.join(output_1, name_str)
					image_output = pyvips.Image.new_from_array(buf)                            
					image_output.write_to_file(file_temp) 

	reader.close()
	javabridge.kill_vm()

	# endregion

	


