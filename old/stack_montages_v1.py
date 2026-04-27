# -*- coding: utf-8 -*-
"""
stack_montages_v1.py

Script to generate a pyramidal OME-TIFF z-stack that can be read in OlyVIA, QuPath, and ImageJ software.

Documentation:
Talley Lambert: https://pypi.org/project/ome-types/


#Created: 14-Aug-25, Marco Acevedo
#Updated: 

#Notes:


"""
import os

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
workingDir = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\z-stack input_xenolith"
pixel_type = u'uint8'

#registered montages

file1 = r"Image_18RBE-006h_xenolith_phasemap_resaved.tif"
file1b = r"Image_18RBE-006h_xenolith_10x_RL BF_01.tif"
file2 = r"Image_18RBE-006h_xenolith_BSE_rgb_resaved.tif"
file3 = r"ray tracing\Image_01_Maximum_Z_xPL.tif" #xpl
file4 = r"ray tracing\Image_01_Maximum_Z.tif" #ppl

#endregion

#region PYVIPS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 

    #Output
    output_folder = os.path.join(workingDir, 'test_old')
    mkdir2(output_folder)

    fileList = [file1, file1b, file2, file3, file4]
    fileList2 = [os.path.join(workingDir, x) for x in fileList]

    #Default dimensions    
    layer_name = "stacked_montage"    
    tileSizeX = 512
    tileSizeY = 512
    z_count = len(fileList)        
    c_count = 3
    dimension_order = "XYCZT"

    channel_list = []   
    for file in fileList2:           
        
        im_temp = pyvips.Image.new_from_file(file)    
        image_width = im_temp.width #image are of = XY size
        image_height = im_temp.height

        # openslide will add an alpha ... drop it
        if im_temp.hasalpha():
            im_temp = im_temp[:-1]    
        
        r, g, b = im_temp.bandsplit()        

        channel_list.append(r)
        channel_list.append(g) 
        channel_list.append(b)                 
        
    
    #Save as pyramidal OME-TIFF
    file_output = f"z_stack.tif"
    output_path = os.path.join(output_folder, file_output)

    # pixel_calibration_sel = pyramid_sizes.loc[idx1, "pixel_calibration_sel"].array[0]            
    pixel_calibration_sel = 0.2

    #Write XML
    ome = OME(uuid=f"urn:uuid:{uuid.uuid4()}")

    pixels = Pixels(
        dimension_order=dimension_order,
        physical_size_x=pixel_calibration_sel,
        physical_size_y=pixel_calibration_sel,
        physical_size_z="1",
        size_x=image_width,
        size_y=image_height,
        size_z=z_count,
        size_c=c_count,
        size_t=1,
        type='uint8'
        )

    pixels.channels.extend([
        Channel(color="-16777216", name="R", samples_per_pixel=1),
        Channel(color="16711680", name="G", samples_per_pixel=1),
        Channel(color="65280", name="B", samples_per_pixel=1)])

    ome.images.append(Image(name= layer_name, pixels=pixels))

    tiff_uuid = f"urn:uuid:{uuid.uuid4()}"
    tiff = TiffData(
        first_c=0,
        first_t=0,
        first_z=0,
        plane_count=1,
        uuid=TiffData.UUID(value=tiff_uuid, file_name= file_output)
    )

    pixels.tiff_data_blocks.append(tiff)
    temp_ome = ome.to_xml() 			
    
    #stack vertically ready for OME 
    montage_roll = pyvips.Image.arrayjoin(channel_list, across=1)    
    montage_roll = montage_roll.copy()
    montage_roll.set_type(pyvips.GValue.gint_type, "page-height", image_height)			
    montage_roll.set_type(pyvips.GValue.gstr_type, "image-description", temp_ome)

    montage_roll.tiffsave(output_path, compression="jpeg", tile=True, 
                tile_width= tileSizeX, tile_height=tileSizeY,
                pyramid=True, subifd=True)
        
        

