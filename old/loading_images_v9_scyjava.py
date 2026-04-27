# -*- coding: utf-8 -*-
"""

#Documentation:
#https://pypi.org/project/pyvips/
#https://pythonhosted.org/python-bioformats/

CZI with Bioformats
https://forum.image.sc/t/python-bioformats-not-able-to-correctly-open-an-image/96600/12

My issue with pyvips and QuPath
https://github.com/libvips/libvips/discussions/2446

https://forum.image.sc/t/qupath-bioformats-high-compression-efficiency/58982/3

Tifffile (engine of python-bioformats) cannot write OME TIFF SubIDFs
https://forum.image.sc/t/python-bioformats-write-image-6d-images-series-handling/28633/7

Write pyramidal OME TIFF from pyvips: Here’s a slightly updated conversion script for libvips 8.14:
https://forum.image.sc/t/writing-qupath-bio-formats-compatible-pyramidal-image-with-libvips/51223/13

Alternatives to python-bioformats 
https://forum.image.sc/t/ongoing-support-for-python-bioformats/49683/14

issue in ImageJ console (warning): Using TiffReader to determine the number of planes.

Writing TiffData (that is missing in the pyvips solution)
https://forum.image.sc/t/setting-up-ome-xml-for-a-new-microscope-from-scratch/62116/15
https://github.com/hzwirnmann/tcf_to_ometiff/blob/main/tcf_to_ometiff/tcf_to_ometiff.py
https://docs.openmicroscopy.org/ome-model/6.2.2/ome-tiff/specification.html#the-tiffdata-element


#Created: 8-Aug-25, Marco Acevedo
#Updated: 12-Aug-25

#Notes:
javabridge installation can fail: Microsoft Visual C++ 14.0 or greater is required. "Microsoft C++ Build Tools"

#Opening output in ImageJ 
Plugins > BioFormats Import
run("Make Composite");
run("Stack to RGB");

ImageReader issue:
javabridge.jutil.JavaException: Image plane too large. Only 2GB of data can be extracted at one time. You can work around the problem by opening the plane in tiles; for further details, see: https://docs.openmicroscopy.org/bio-formats/7.3.1/about/bug-reporting.html#common-issues-to-check   


"""
#region Dependencies

import os
vipsbin = r'c:\vips-dev-8.16\bin'
add_dll_dir = getattr(os, 'add_dll_directory', None)
if callable(add_dll_dir):
    add_dll_dir(vipsbin)
else:
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))

import sys
import pyvips
import glob
print("vips version: " + str(pyvips.version(0))+"."+str(pyvips.version(1))+"."+str(pyvips.version(2)))
import matplotlib.pyplot as plt
import math

import javabridge
import bioformats
import bioformats.formatreader as F
from bioformats import metadatatools
import bioformats.formatwriter as W

import uuid
from ome_types.model import Channel
from ome_types.model import Image
from ome_types.model import OME
from ome_types.model import Pixels
from ome_types.model import TiffData

#relative paths
from helperFunctions.mkdir2 import mkdir1, mkdir2 

# imports > pip install pyimagej
import scyjava
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import ImageReader
from loci.formats import MetadataTools
from loci.formats import FormatTools
from loci.formats.out import PyramidOMETiffWriter
from loci.common.image import IImageScaler
from loci.common.image import SimpleImageScaler
from ome.xml.model.primitives import PositiveInteger

# import sys
# import scyjava

# scyjava.config.endpoints.append('ome:formats-bsd:6.7.0')

# Integer = scyjava.jimport('java.lang.Integer')
# Arrays = scyjava.jimport('java.util.Arrays')

# SimpleImageScaler = scyjava.jimport('loci.common.image.SimpleImageScaler')
# ServiceFactory = scyjava.jimport('loci.common.services.ServiceFactory')
# FormatTools = scyjava.jimport('loci.formats.FormatTools')
# ImageReader = scyjava.jimport('loci.formats.ImageReader')
# ImageWriter = scyjava.jimport('loci.formats.ImageWriter')
# OMEXMLService = scyjava.jimport('loci.formats.services.OMEXMLService')

# DimensionOrder = scyjava.jimport('ome.xml.model.enums.DimensionOrder')
# PositiveInteger = scyjava.jimport('ome.xml.model.primitives.PositiveInteger')

#endregion

# #region User input

# image_path = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\CA24MR-1_second_top.vsi"
# sel_pyramid = 2 #sequential number of image #pyramid 3>7K pixels 
# #sel_image = 2 #pythonic image count 
# pixel_type = u'uint8'

# #endregion

# #region BIOFORMATS

# javabridge.start_vm(class_path=bioformats.JARS, max_heap_size='24G', run_headless=True)


# dirname1 = os.path.dirname(image_path)
# basename1 = os.path.basename(image_path).replace(".vsi", "")
# folder1 = os.path.join(dirname1, "bf_" + basename1)
# mkdir2(folder1)

# #Read metadata
# xml1 = bioformats.get_omexml_metadata(image_path, url=None)      
# xml2 = bioformats.OMEXML(xml1)

# #General
# levelZero = xml2.image(0)
# acquisition_date = levelZero.AcquisitionDate
# layer_name = levelZero.Name
# pixel_calibration = levelZero.Pixels.PhysicalSizeX #equal to Y
# dimension_order = levelZero.Pixels.DimensionOrder
# # byte_order = levelZero.Pixels.BigEndian #reading byte order
# # pixel_type = levelZero.Pixels.Type

# #Specific level
# pixels = xml2.image(sel_pyramid).Pixels
# x_count = pixels.SizeX
# y_count = pixels.SizeY
# c_count = pixels.SizeC
# z_count = pixels.SizeZ
# t_count = pixels.SizeT
# pixel_calibration_sel = pixel_calibration*(2 ** sel_pyramid)


# path_list = []
# sel_image = 2
# # for sel_image in range(0, 3):

# #output
# mode_str = f"{sel_image}"
# output_path = os.path.join(folder1, layer_name + "_" + mode_str + ".tif")

# #caution: write_image locally overwrites the same file (indexing issues if different shape)
# if os.path.exists(output_path):
#   os.remove(output_path)
# else:
#   print("Overwritting") 


# #Setting up image reader and retrieving area
# seriesIndex = 1 #pyramid level   
# z_index = 2 #z-series
# n_channels = 3 

# omeMeta = metadatatools.createOMEXMLMetadata() #for output

# #Reader
# ImageReader = F.make_image_reader_class()
# reader = ImageReader()
# reader.setMetadataStore(omeMeta)
# reader.setId(image_path)            
# reader.setSeries(seriesIndex) #pyramid

# sizeX = reader.getSizeX()
# sizeY = reader.getSizeY()        
# sizeZ = reader.getSizeZ()  
# sizeC = reader.getSizeC()  
# sizeT = reader.getSizeT()  
# tileSizeX = 512 #reader.getOptimalTileWidth()
# tileSizeY = 512 #reader.getOptimalTileHeight()
# type = reader.getPixelType()

# #Writer
# writer = W.make_ome_tiff_writer_class()
# # writer.setMetadataRetrieve(omeMeta)
# # writer.setInterleaved("true") #writer.isInterleaved()

# writer.setTileSizeX(tileSizeX)
# writer.setTileSizeY(tileSizeY)
# writer.setId(output_path)

# # read the tiles
# for series in range(reader.getSeriesCount()):
# 	reader.setSeries(series)

# 	for image in range(reader.getImageCount()):
# 		width = reader.getSizeX()
# 		height = reader.getSizeY()

# 		# Determined the number of tiles to read and write
# 		nXTiles = int(math.floor(width / tileSizeX))
# 		nYTiles = int(math.floor(height / tileSizeY))
# 		if nXTiles * tileSizeX != width:
# 			nXTiles = nXTiles + 1
# 		if nYTiles * tileSizeY != height:
# 			nYTiles = nYTiles + 1

# 		for y in range(nYTiles):
# 			for x in range(nXTiles):
# 				# The x and y coordinates for the current tile
# 				tileX = x * tileSizeX
# 				tileY = y * tileSizeY
# 				effTileSizeX = tileSizeX
# 				if (tileX + tileSizeX) >= width:
# 					effTileSizeX = width - tileX
					
# 				effTileSizeY = tileSizeY
# 				if (tileY + tileSizeY) >= height:
# 					effTileSizeY = height - tileY
					
# 				# Read tiles from the input file and write them to the output OME-Tiff
# 				buf = reader.openBytes(image, tileX, tileY, effTileSizeX, effTileSizeY)
#                 # writer.saveBytes(image, buf, tileX, tileY, tileSizeX, tileSizeY)



# image = reader.openBytesXYWH(z_index, 0, 0, sizeX, sizeY)
# image.shape = (sizeY, sizeX, n_channels) #interleaved (see VSI metadata)

# bioformats.write_image(output_path, image, pixel_type, 
#                         c=0, z=0, t=0,
#                         size_c=3, size_z=1, size_t=1, 
#                         channel_names=None)

# path_list.append(output_path)

# javabridge.kill_vm()

#endregion

# #region PYVIPS

# folder2 = os.path.join(folder1.replace("bf_", "vips_"))
# mkdir2(folder2)

# #file_input = path_list[0]
# for file_input in path_list:  
    
#     basename_output = os.path.basename(file_input).replace(".tif", ".ome.tif")
#     file_output = os.path.join(folder2, basename_output)

#     im = pyvips.Image.new_from_file(file_input)    

#     # openslide will add an alpha ... drop it
#     if im.hasalpha():
#         im = im[:-1]

#     image_width = im.width
#     image_height = im.height    

#     im = pyvips.Image.arrayjoin(im.bandsplit(), across=1)

#     #XML
#     tile_size = 512
#     ome = OME(uuid=f"urn:uuid:{uuid.uuid4()}")
#     pixels = Pixels(
#         dimension_order=dimension_order,
#         physical_size_x=pixel_calibration_sel,
#         physical_size_y=pixel_calibration_sel,
#         physical_size_z="1",
#         size_x=image_width,
#         size_y=image_height,
#         size_z=1,
#         size_c=3,
#         size_t=1,
#         type='uint8')

#     pixels.channels.extend([
#         Channel(color="-16777216", name="R", samples_per_pixel=1),
#         Channel(color="16711680", name="G", samples_per_pixel=1),
#         Channel(color="65280", name="B", samples_per_pixel=1)])

#     ome.images.append(Image(name=layer_name, pixels=pixels))

#     tiff_uuid = f"urn:uuid:{uuid.uuid4()}"
#     tiff = TiffData(
#         first_c=0,
#         first_t=0,
#         first_z=0,
#         plane_count=1,
#         uuid=TiffData.UUID(value=tiff_uuid, file_name= basename_output)
#     )

#     pixels.tiff_data_blocks.append(tiff)
#     temp_ome = ome.to_xml() 
#     print(f"""<?xml version="1.0" encoding="UTF-8"?>\n""" + temp_ome)

#     im = im.copy()
#     im.set_type(pyvips.GValue.gint_type, "page-height", image_height)
#     im.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)

#     im.tiffsave(file_output, compression="jpeg", tile=True,
#                 tile_width= tile_size, tile_height= tile_size,
#                 pyramid=True, subifd=True) #, bigtiff=True
#     #none, jpeg, lzw, zip, and deflate

#     #endregion




