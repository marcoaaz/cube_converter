import os
import sys
import numpy as np
import pandas as pd
from scipy import ndimage

#VIPS
add_dll_dir = getattr(os, 'add_dll_directory', None) #Windows=True
vipsbin = r'c:/vips-dev-8.16/bin'

if getattr(sys, 'frozen', False):	# Running in a PyInstaller bundle			
	bundle_dir = os.path.abspath(os.path.dirname(__file__)) #relative path	
	vip_dlls = os.path.join(bundle_dir, 'vips')

else: # for regular Python environment	
	vip_dlls = vipsbin

#Adding pyvips
if callable(add_dll_dir): 
	add_dll_dir(vip_dlls)
else:
	os.environ['PATH'] = os.pathsep.join((vip_dlls, os.environ['PATH']))

import pyvips

from ray_tracing_module import multi_channel_structure_tensor_edge
from ray_tracing_module import build_direction_array, build_direction_array_weighted

#2, 98
def to_uint8(data, low_per=2, high_per=98):
	"""
	Converts float32 to uint8 by stretching the middle 96% of values.
	"""
	# 1. Determine the robust range
	v_min, v_max = np.percentile(data, [low_per, high_per])
	
	# 2. Clip the data so outliers don't wrap around
	data_clipped = np.clip(data, v_min, v_max)
	
	# 3. Linearly rescale to 0-255
	# Formula: (val - min) / (max - min) * 255
	rescaled = (data_clipped - v_min) / (v_max - v_min + 1e-8) * 255
	
	return rescaled.astype(np.uint8)

#User input
filename = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\slides_processing\curiosity\tl-xpl.tif" 
radius_med = 8 #8, critical parameter
manual_request = [0, 1, 3, 4, 6, 8] #list(range(10))

#Notes
#0, 15, 30, 45, 60, 75
#[0, 1, 3, 4, 6, 8]
# "C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\slides_processing\curiosity\rl-ppl.tif"
#tl-xpl-lambda.tif, rl-ppl.tif

#Script

#default
n_layers_requested = len(manual_request) #10, not so important (36 better than 6 steps)
output_basename = f'edges_tl-xpl_n{n_layers_requested}_medF{radius_med}.tif'
parentDir = os.path.dirname(filename)
file_output = os.path.join(parentDir, output_basename)

#metadata
im_temp = pyvips.Image.new_from_file(filename)
n_layers = im_temp.get("n-pages")
tile_height = im_temp.height
tile_width = im_temp.width
n_channels = im_temp.bands
shape = (tile_height, tile_width, n_channels, len(manual_request)) 

#process_tile_rt
tile_temp = np.zeros(shape, dtype= np.float32) #pre-allocate						

for k, index in enumerate(manual_request):
	im_temp = pyvips.Image.new_from_file(filename, page= index) 
	
	im_temp2 = im_temp.median(radius_med) #denoising	
	tile_temp[:, :, :, k] = im_temp2.numpy() #caching	

#calculate_statistic
colour_mode = 1
if colour_mode == 0:
	tile_temp = np.mean(tile_temp, axis= 2, keepdims=True)

# direction_array, coherence_map = build_direction_array(tile_temp)
direction_array, coherence_map = build_direction_array_weighted(tile_temp)
array2 = multi_channel_structure_tensor_edge(coherence_map, tile_temp, sigma_grad=1.0, sigma_tensor=3.0)

array3 = to_uint8(array2)
test = pyvips.Image.new_from_array(array3)
test.tiffsave(file_output)


