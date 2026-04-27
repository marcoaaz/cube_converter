# -*- coding: utf-8 -*-
"""
read_metadata_v1.py

Script to save a VSI z-stack as a series of tiles for a specific pyramid level. 
The script should be followed by 'join_tiles_v2.py'.

Designed to work with 
image_path = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\CA24MR-1_second_top.vsi"

#Created: 14-Aug-25, Marco Acevedo
#Updated: 19-Aug-25

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

Notes:

This version works around an ImageReader issue:
javabridge.jutil.JavaException: Image plane too large. Only 2GB of data can be extracted at one time. You can work around the problem by opening the plane in tiles; for further details, see: https://docs.openmicroscopy.org/bio-formats/7.3.1/about/bug-reporting.html#common-issues-to-check   

javabridge installation can fail: Microsoft Visual C++ 14.0 or greater is required. "Microsoft C++ Build Tools"


#Opening output in ImageJ 
Plugins > BioFormats Import*
run("Make Composite");
run("Stack to RGB");
*issue in ImageJ console (warning): Using TiffReader to determine the number of planes.

"""
#region Dependencies

import os
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

image_path = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\Image_nan1-b_10x.vsi"
# image_path = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\z-stack_zircon\CA24MR-1_second_top.vsi"

#region BIOFORMATS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 	

	dirname1 = os.path.dirname(image_path)
	basename1 = os.path.basename(image_path).replace(".vsi", "")
	folder1 = os.path.join(dirname1, "processed_" + basename1)
	mkdir2(folder1)

	#Read metadata
	
	javabridge.start_vm(class_path=bioformats.JARS, max_heap_size='24G', run_headless=True)

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
	image_count = reader.getImageCount()	
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

		#Finding scans
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

	reader.close()
	javabridge.kill_vm()
	
	
	#Saving in readable format
	file1 = os.path.join(folder1, 'pyramid_sizes.csv')
	df_sizes.to_csv(file1, sep=',', index=False)

	
	# endregion
