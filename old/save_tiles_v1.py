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
import json
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

import javabridge
import bioformats
import bioformats.formatreader as F
from bioformats import metadatatools

#relative paths
from helperFunctions.mkdir2 import mkdir1, mkdir2 

#endregion

#region User input

image_path = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\Image_nan1-b_10x.vsi"
sel_pyramid = 2 #sequential number of image #pyramid 3>7K pixels 

tileSizeX = 512 #reader.getOptimalTileWidth()
tileSizeY = 512 

#endregion

#region BIOFORMATS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 
     
	javabridge.start_vm(class_path=bioformats.JARS, max_heap_size='24G', run_headless=True)

	dirname1 = os.path.dirname(image_path)
	basename1 = os.path.basename(image_path).replace(".vsi", "")
	folder1 = os.path.join(dirname1, "processed_" + basename1)
	mkdir2(folder1)

	#Read metadata
	xml1 = bioformats.get_omexml_metadata(image_path, url=None)      
	xml2 = bioformats.OMEXML(xml1)
	
	#Convention (only first layer explains image)
	levelZero = xml2.image(0)
	acquisition_date = levelZero.AcquisitionDate
	layer_name = levelZero.Name
	dimension_order = levelZero.Pixels.DimensionOrder
	pixel_calibration = levelZero.Pixels.PhysicalSizeX #equal to Y
	#pixels = xml2.image(series).Pixels

	#Reader
	
	omeMeta = metadatatools.createOMEXMLMetadata() #for output
	ImageReader = F.make_image_reader_class()
	reader = ImageReader()
	reader.setMetadataStore(omeMeta)
	reader.setId(image_path)            
	series_count = reader.getSeriesCount()
	image_count = reader.getImageCount()

	#Learning about levels
	values = []
	for series in range(series_count): #pyramid levels
		
		reader.setSeries(series)
		sizeX = reader.getSizeX()
		sizeY = reader.getSizeY()
		sizeC = reader.getSizeC()
		sizeZ = reader.getSizeZ()		  
		sizeT = reader.getSizeT()  
		type = reader.getPixelType()
		pixel_calibration_sel = pixel_calibration*(2 ** series)

		values.append([series, sizeX, sizeY, sizeC, sizeZ, sizeT, type, pixel_calibration_sel])	

	df_sizes = pd.DataFrame(values, columns =['series', 'sizeX', 'sizeY', 'sizeC', 'sizeZ', 'sizeT', 
									 'type', 'pixel_calibration_sel'])

	#Saving in readable format
	file1 = os.path.join(folder1, 'pyramid_sizes.csv')
	file2 = os.path.join(folder1, 'experimental_metadata.json')

	df_sizes.to_csv(file1, sep=',', index=False)

	data = {
		"image_path": image_path,
        "acquisition_date": acquisition_date,
        "layer_name": layer_name,
        "dimension_order": dimension_order,   
        "tileSizeX": tileSizeX,
        "tileSizeY": tileSizeY,
		}
	
	with open(file2, 'w') as f:
		json.dump(data, f, indent=4) # indent for pretty printing	

    #endregion
	
	#region Read the tiles
	series_span = range(sel_pyramid, sel_pyramid+1)
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

	


