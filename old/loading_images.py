# -*- coding: utf-8 -*-
"""

#Documentation:
#https://pypi.org/project/pyvips/
#https://pythonhosted.org/python-bioformats/

#Notes:
javabridge installation can fail: Microsoft Visual C++ 14.0 or greater is required. "Microsoft C++ Build Tools"

#Created: 8-Aug-25, Marco Acevedo
#Updated:

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

#endregion

javabridge.start_vm(class_path=bioformats.JARS,
                    run_headless=True)

#region User input

image_path = r"E:\Feb-March_2024_zircon imaging\zircon_proj_VS200\Export\CA24MR-1_second_top.vsi"
sel_pyramid = 3 #sequential number of image
sel_image = 2 #pythonic image count 

#pyramid 3>7K pixels 

#endregion

#region Script

image_path2 = image_path.replace(".vsi", ".ome.tif") #output

#Learn about the input
xml1 = bioformats.get_omexml_metadata(image_path, url=None)      
xml2 = bioformats.OMEXML(xml1)
acquisitionDate = xml2.image().AcquisitionDate

pixels = xml2.image(sel_pyramid).Pixels
x_count = pixels.SizeX
y_count = pixels.SizeY
c_count = pixels.SizeC
z_count = pixels.SizeZ
t_count = pixels.SizeT
print([x_count, y_count, c_count, z_count, t_count])


image, scale = bioformats.load_image(image_path, c= None, z= sel_image, t=0, series= sel_pyramid, index= None, 
                                     rescale=False, wants_max_intensity=True, channel_names=None)


imgplot = plt.imshow(image)
plt.show()

pixel_type = u'uint8'
bioformats.write_image(image_path2, image, pixel_type, 
                       c=0, z=0, t=0, 
                       size_c=3, size_z=3, size_t=1, channel_names=None)


#endregion




javabridge.kill_vm()