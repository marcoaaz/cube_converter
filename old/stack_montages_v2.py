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
from main_functions import ready_for_OME

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

#registered montages
workingDir = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\z-stack input_xenolith"
file1 = r"Image_18RBE-006h_xenolith_phasemap_resaved.tif"
file1b = r"Image_18RBE-006h_xenolith_10x_RL BF_01.tif"
file2 = r"Image_18RBE-006h_xenolith_BSE_rgb_resaved.tif"
file3 = r"ray tracing\Image_01_Maximum_Z_xPL.tif" #xpl
file4 = r"ray tracing\Image_01_Maximum_Z.tif" #ppl

pixel_size_sel = 0.2 
tileSize = 512 
filename_output = f"z_stack"
output_folder = os.path.join(workingDir, 'z-stack')

fileList = [file1, file1b, file2, file3, file4]
fileList2 = [os.path.join(workingDir, x) for x in fileList]

#endregion

#region PYVIPS
if __name__ == '__main__':    #lock to only 1 subprocess (Windows)     

    mkdir2(output_folder)    

    #Default dimensions   
    z_count = len(fileList2)        
    c_count = 3
    dimension_order = "XYCZT" #equal to original VSI file
    tileSizeX = tileSize #512
    tileSizeY = tileSizeX

    channel_list = []   
    for file in fileList2:           
        
        im_temp = pyvips.Image.new_from_file(file)            

        # openslide will add an alpha ... drop it
        if im_temp.hasalpha():
            im_temp = im_temp[:-1]    
        
        r, g, b = im_temp.bandsplit()        

        channel_list.append(r)
        channel_list.append(g) 
        channel_list.append(b)                 
        
    #image are of = XY size
    size_x = channel_list[0].width 
    size_y = channel_list[0].height
    
    #Save as pyramidal OME-TIFF   
    file_output = filename_output + ".tif" 
    output_path = os.path.join(output_folder, file_output)

    dimension_sizes = [size_x, size_y, c_count, z_count, 1] #[size_c, size_z, size_t]
    montage_roll = ready_for_OME(channel_list, file_output, dimension_order, dimension_sizes, pixel_size_sel)

    montage_roll.tiffsave(output_path, compression="lzw", tile=True, 
                tile_width= tileSizeX, tile_height=tileSizeY,
                pyramid=True, subifd=True, bigtiff=True)
        
        

