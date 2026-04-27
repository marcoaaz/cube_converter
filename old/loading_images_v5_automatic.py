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

issue in ImageJ console:
Using TiffReader to determine the number of planes.

Writing TiffData (that is missing in the pyvips solution)
https://forum.image.sc/t/setting-up-ome-xml-for-a-new-microscope-from-scratch/62116/15
https://github.com/hzwirnmann/tcf_to_ometiff/blob/main/tcf_to_ometiff/tcf_to_ometiff.py
https://docs.openmicroscopy.org/ome-model/6.2.2/ome-tiff/specification.html#the-tiffdata-element


#Created: 8-Aug-25, Marco Acevedo
#Updated:

#Notes:
javabridge installation can fail: Microsoft Visual C++ 14.0 or greater is required. "Microsoft C++ Build Tools"

#Opening output in ImageJ 
Plugins > BioFormats Import
run("Make Composite");
run("Stack to RGB");



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

import javabridge
import bioformats
import matplotlib.pyplot as plt

import uuid
from ome_types.model import Channel
from ome_types.model import Image
from ome_types.model import OME
from ome_types.model import Pixels
from ome_types.model import TiffData

#relative paths
from helperFunctions.mkdir2 import mkdir1, mkdir2 

#endregion

#region User input

image_path = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\CA24MR-1_second_top.vsi"
sel_pyramid = 3 #sequential number of image #pyramid 3>7K pixels 
#sel_image = 2 #pythonic image count 
pixel_type = u'uint8'

#endregion




#region BIOFORMATS

javabridge.start_vm(class_path=bioformats.JARS,
                    run_headless=True)


dirname1 = os.path.dirname(image_path)
basename1 = os.path.basename(image_path)
folder1 = os.path.join(dirname1, "bf_" + basename1.replace(".vsi", ""))
mkdir2(folder1)

#Read metadata
xml1 = bioformats.get_omexml_metadata(image_path, url=None)      
xml2 = bioformats.OMEXML(xml1)

#General
acquisition_date = xml2.image(0).AcquisitionDate
layer_name = xml2.image(0).Name

#Specific
pixels = xml2.image(sel_pyramid).Pixels
x_count = pixels.SizeX
y_count = pixels.SizeY
c_count = pixels.SizeC
z_count = pixels.SizeZ
t_count = pixels.SizeT

path_list = []
for sel_image in range(0, 3):

    #output
    mode_str = f"{sel_image}"
    output_path = os.path.join(folder1, layer_name + "_" + mode_str + ".tif")

    # image, scale = bioformats.load_image(image_path, c= None, 
    #                                      z= sel_image, t=0, series= sel_pyramid, index= None,
    #                                      rescale=False, wants_max_intensity=True, channel_names=None)
   
    # bioformats.write_image(output_path, image, pixel_type, 
    #                     c=0, z=0, t=0, 
    #                     size_c=3, size_z=3, size_t=1, channel_names=None)

    path_list.append(output_path)

javabridge.kill_vm()

#endregion

#region PYVIPS

folder2 = os.path.join(folder1.replace("bf_", "vips_"))
mkdir2(folder2)

channel_list = []    
file_input = path_list[0]
# for file_input in path_list:  
    
basename_output = os.path.basename(file_input).replace(".tif", ".ome.tif")
file_output = os.path.join(folder2, basename_output)

im = pyvips.Image.new_from_file(file_input)    

# openslide will add an alpha ... drop it
if im.hasalpha():
    im = im[:-1]

image_width = im.width
image_height = im.height    

im = pyvips.Image.arrayjoin(im.bandsplit(), across=1)

#XML
tile_size = 512
ome = OME(uuid=f"urn:uuid:{uuid.uuid4()}")
pixels = Pixels(
    dimension_order='XYCZT',
    physical_size_x="0.2516",
    physical_size_y="0.2516",
    physical_size_z="0.75",
    size_x=image_width,
    size_y=image_height,
    size_z=1,
    size_c=3,
    size_t=1,
    type='uint8')
pixels.channels.extend([
    Channel(color="-16777216", name="Channel 1", samples_per_pixel=1),
    Channel(color="16711680", name="Channel 2", samples_per_pixel=1),
    Channel(color="65280", name="Channel 3", samples_per_pixel=1)])

ome.images.append(Image(name="example1", pixels=pixels))

# for c in range(3):
c = 0
filename = "input_C%04g.tif" % (c+1)
tiff_uuid = f"urn:uuid:{uuid.uuid4()}"
tiff = TiffData(
    first_c=c,
    first_t=0,
    first_z=0,
    plane_count=1,
    uuid=TiffData.UUID(value=tiff_uuid, file_name= basename_output)
)
pixels.tiff_data_blocks.append(tiff)

with open("cell0005_R0001.companion.ome", 'w') as f:
    temp_ome = ome.to_xml()    

    f.write(temp_ome)

print(f"""<?xml version="1.0" encoding="UTF-8"?>\n""" + temp_ome)

im = im.copy()
im.set_type(pyvips.GValue.gint_type, "page-height", image_height)
im.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)

im.tiffsave(file_output, compression="jpeg", tile=True,
            tile_width=512, tile_height=512,
            pyramid=True, subifd=True) #, bigtiff=True
#none, jpeg, lzw, zip, and deflate

#endregion




