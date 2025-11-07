
'''
ray_tracing_module.py

File contains the helper functions to enable ray tracing.

Documentation:

https://www.libvips.org/API/current/method.Image.stats.html
https://www.libvips.org/API/current/method.Image.resize.html
https://stackoverflow.com/questions/32789991/python-dimension-subset-of-ndimage-using-indices-stored-in-another-image

Citation: https://doi.org/10.3390/min13020156

Date updated: 3-Sep-25, 13-Sep-25

'''

import os
import sys
import numpy as np
import pandas as pd

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


def channel_uint8(image_rs3):
	image_rs4 = image_rs3.cast("uchar") #uint8    

	return image_rs4

def find_P_thresholds(input_channel, percentOut_dsaImage, bit_precision):
	#bit_precision: 8-bit=255; 16-bit=65535
	
	calc_depth = (2**bit_precision)-1     
	min_val = input_channel.min()
	max_val = input_channel.max()
	ratio = ((max_val - min_val)/calc_depth)

	#Finding percentiles	
	image_rs1 = (input_channel - min_val) / ratio         
	image_rs2 = (image_rs1).cast("uint") #'uchar' is for 8-bit        
	
	th_low = image_rs2.percent(percentOut_dsaImage)
	th_high = image_rs2.percent(100 - percentOut_dsaImage)        
	
	#values	
	th_low_input = th_low*ratio + min_val 
	th_high_input = th_high*ratio + min_val                    

	return th_low_input, th_high_input


def channel_rescaled(input_channel, th_low_input, th_high_input):

	#Rescaling and capping
	image_rs3 = (input_channel - th_low_input) * (255 / (th_high_input - th_low_input)) 

	image_rs3 = (image_rs3 > 255).ifthenelse(255, image_rs3) #true, false
	image_rs3 = (image_rs3 < 0).ifthenelse(0, image_rs3)

	output_channel = image_rs3.cast("uchar") #uint8    

	return output_channel

def img_rescaled(image_cropped, percentOut_dsaImage):
	#Descr. statistics (follows 'tilingAndStacking_v3.py')
	
	# minimum, maximum, sum, sum of squares, mean, standard deviation, 
	# x coordinate of minimum, y coordinate of minimum, x coordinate of maximum, y coordinate of maximum  
	target_W = 5000
	source_W = image_cropped.width
	ratio = target_W/source_W
	image_thumbnail = image_cropped.resize(ratio, kernel=pyvips.Kernel.NEAREST)
	
	out = pyvips.Image.stats(image_thumbnail)
	out1 = out.numpy()   	
	# > 6GB (74Kx45K montage) warning: vips_tracked: out of memory -- size == 3MB	
	
	n_bands = image_cropped.bands			
	channel_list_out = []
	for i in range(n_bands):		
		
		#Direct indexing
		channel_temp = image_cropped[i]
		thumbnail_temp = image_thumbnail[i] #faster computation

		statistic_vals = out1[i+1, :] #channel stats
		#Note: row 0 has statistics for all bands together

		#Positive, rescaled, capped and uint8 (useful for std, maxIndex, minIndex, PCA)
		channel_positive = channel_temp - statistic_vals[0]		
		thumbnail_positive = thumbnail_temp - statistic_vals[0]

		th_low_input, th_high_input = find_P_thresholds(thumbnail_positive, percentOut_dsaImage, 16)		
		channel_positive2 = channel_rescaled(channel_positive, th_low_input, th_high_input)		
		
		channel_list_out.append(channel_positive2)
	
	#RGB
	image_rescaled = channel_list_out[0].bandjoin(channel_list_out[1:])

	return image_rescaled

def understand_tiling(fileList, pattern, workingDir1):
	
	items_str = ['series', 'z', 'x', 'y', 'width', 'height', 'image_path']
	
	values = []
	for filename in fileList:		
		match = pattern.match(filename) # scan image set (perfect match needed)      
		
		if match is None:
			continue

		item_series = int(match.group(1))
		item_z = int(match.group(2))    
		item_x = int(match.group(3))    
		item_y = int(match.group(4))

		#image size
		im_temp = pyvips.Image.new_from_file(filename) #must be an image
		item_width = im_temp.width
		item_height = im_temp.height

		values.append([item_series, item_z, item_x, item_y, item_width, item_height, filename])

	df = pd.DataFrame(values, columns = items_str)	
	df1 = df.sort_values(items_str, ascending= [True, True, True, True, True, True, True])
	
	df1.to_csv(os.path.join(workingDir1, 'files1.csv'), index=False)
	
	return df1

def calculate_statistic(tile_temp, sel_stats):

	condition_1 = sel_stats == "max"
	condition_2 = sel_stats == "maxIndex"
	condition_3 = sel_stats == "min"
	condition_4 = sel_stats == "minIndex"	
	condition_a = (condition_1 or condition_2 or condition_3 or condition_4)	

	#Using colour (float32)
	if sel_stats == "mean":            
		tile_temp2 = np.mean(tile_temp, axis= 3)
		
	elif sel_stats == "median":        
		tile_temp2 = np.median(tile_temp, axis= 3)    

	elif sel_stats == "std":        
		tile_temp2 = np.std(tile_temp, axis= 3)    
	
	#Using greyscale indexes (int64)  
	elif condition_a:
		dim = tile_temp.shape
		n_channels = dim[2]		

		tile_greyscale = np.mean(tile_temp, axis= 2, keepdims=True)
		
		if condition_1 or condition_2:
			tile_idx = np.argmax(tile_greyscale, axis= 3)
		elif condition_3 or condition_4:
			tile_idx = np.argmin(tile_greyscale, axis= 3)		
		
		tile_idx2 = np.repeat(tile_idx, n_channels, 2) 			
		
		#for index image
		if condition_2 or condition_4:					
		
			tile_temp2 = tile_idx2.astype(np.float32)   			
		
		#for min/max
		elif condition_1 or condition_3:							
			
			array_idx = np.indices(tile_idx2.shape)
			last_dim = tile_idx2[array_idx[0], array_idx[1], array_idx[2]]
			tile_temp2 = tile_temp[array_idx[0], array_idx[1], array_idx[2], last_dim]				

	else:
		print('The statistic selected is not available')
	
	return tile_temp2