
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
import gc

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.ndimage import grey_dilation

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

#region Image processing

def channel_uint8(image_rs3):
	image_rs4 = image_rs3.cast("uchar") #uint8    

	return image_rs4

def find_P_thresholds(input_channel, percentOut, bit_precision = 16):
	#bit_precision: 8-bit=255; 16-bit=65535		

	calc_depth = (2**bit_precision) -1  
	stats = input_channel.stats() #eager pass (load data once)
	min_val = stats(0, 0)[0] 
	max_val = stats(1, 0)[0]    
	 
	#medicine 1: zero division if weight-decay is too low and no. epochs too high
	range_val = max((max_val - min_val), 0.1) 
	ratio = (range_val/calc_depth)

	#medicine 2: 'gint' is invalid or out of range
	p_low = percentOut + 0.005 
	p_high = 100 - p_low

	#Finding percentiles (16-bit), 'uchar'=8-bit, 'uint' or 'ushort'=16-bit  	
	image_rs2 = ((input_channel - min_val) / ratio).cast("ushort") #uint	

	th_low = image_rs2.percent(p_low) #'int'	
	th_high = image_rs2.percent(p_high)        	
	
	th_low_input = th_low*ratio + min_val 
	th_high_input = th_high*ratio + min_val                    

	#medicine 3: zero division when processing an artefact image (e.g., Synchrotron XFM Flux0)
	if th_low_input == th_high_input:
		th_high_input = th_high_input + 1

	#Warning note: the file handles on Windows often "choke" or the pipeline breaks when using 
	#random access if the full image has to pass 3 or more times, which causes blacked-out strips.

	return th_low_input, th_high_input

def channel_rescaled(input_channel, min_val, max_val, th_low_input, th_high_input):  
	#Min-Max Scaling (normalization)
	#Note: Use when the distribution is not normal and you need to preserve data relationships.
	#Following: https://au.mathworks.com/help/matlab/ref/rescale.html

	#Capping
	input_channel = (input_channel > th_high_input).ifthenelse(th_high_input, input_channel) #true, false
	input_channel = (input_channel < th_low_input).ifthenelse(th_low_input, input_channel)

	#Rescaling
	output_channel = min_val + (input_channel - th_low_input) * ( (max_val - min_val) / (th_high_input - th_low_input) ) 			
	
	return output_channel  

def img_rescaled(image_cropped, percentOut):
	#Note: Descriptive statistics part follows 'tilingAndStacking_v3.py'	
	
	target_W = 5000
	source_W = image_cropped.width
	ratio = target_W/source_W

	image_thumbnail = image_cropped.resize(ratio, kernel=pyvips.Kernel.NEAREST)
	
	#Materialize the thumbnail to break the pipeline connection to the large image
	image_thumbnail = image_thumbnail.copy_memory()
	stats_image = image_thumbnail.stats()
	# Row 0 = all bands, Row 1 = Band 1, etc.	
	# Col 0 = minimum, Col 1= maximum, sum, sum of squares, mean, standard deviation, 
	# x coordinate of minimum, y coordinate of minimum, x coordinate of maximum, y coordinate of maximum  

	n_bands = image_cropped.bands			
	channel_list_out = []

	for i in range(n_bands):		
		
		#Direct indexing
		channel_temp = image_cropped[i]
		thumbnail_temp = image_thumbnail[i] #faster computation

		min_val = stats_image.getpoint(0, i + 1)[0] #direct fetching		

		#Positive, rescaled, capped and uint8 (useful for std, maxIndex, minIndex, PCA)
		channel_positive = channel_temp - min_val	
		thumbnail_positive = thumbnail_temp - min_val

		th_low_input, th_high_input = find_P_thresholds(thumbnail_positive, percentOut, 16)					
		channel_out = channel_rescaled(channel_positive, 0, 255, th_low_input, th_high_input) #float		

		channel_list_out.append(channel_out.cast("uchar")) #uint8 

		del channel_temp, thumbnail_temp, channel_positive, thumbnail_positive, channel_out  	
	
	#RGB
	image_rescaled = channel_list_out[0].bandjoin(channel_list_out[1:])

	#RAM cleanup
	del image_thumbnail, stats_image, channel_list_out
	gc.collect()

	return image_rescaled



#endregion

#region Ray tracing

def calculate_statistic(tile_temp, sel_stats):
	
	dim = tile_temp.shape
	n_channels = dim[2]	

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
			
	
	#Modulation based on greyscale PPL/XPL (float32)
	elif sel_stats == "modulation": 
	#Following: Acevedo Zamora et al. (2024) 'stack_spectra_leica_v18_loop.m'
	#After: 2011_Axer et al._High-resolution fiber tract reconstruction in the 
	#human brain by means of three-dimensional polarized light imaging	

		epsilon= 10**(-8)
		colour_mode = 0
		if colour_mode == 0:
			tile_greyscale = np.mean(tile_temp, axis= 2, keepdims=True)		
		
		#transmittance (mean)
		tile_mean = np.mean(tile_greyscale, axis=3, keepdims=False)
		
		#phase (stage rotation when max)
		tile_minIdx = np.argmin(tile_greyscale, axis= 3)		
		tile_maxIdx = np.argmax(tile_greyscale, axis= 3)
		tile_phase = tile_maxIdx.astype(np.float32)
		
		#retardation (normalised range)
		array_idx = np.indices(tile_minIdx.shape)		
		min_last_dim = tile_minIdx[array_idx[0], array_idx[1], array_idx[2]]
		max_last_dim = tile_maxIdx[array_idx[0], array_idx[1], array_idx[2]]		
		tile_min = tile_greyscale[array_idx[0], array_idx[1], array_idx[2], min_last_dim]#tile_temp						 
		tile_max = tile_greyscale[array_idx[0], array_idx[1], array_idx[2], max_last_dim]		

		tile_retardation = (tile_max - tile_min) / (tile_mean + epsilon)
		tile_retardation2 = np.clip(tile_retardation, 0, None)
		
		#modulation image
		tile_temp2 = np.concatenate((tile_mean, tile_phase, tile_retardation2), axis=2)		

	#Detecting edges (float32)
	elif sel_stats == "edges": #this takes x4 longer than modulation
		colour_mode = 1
		if colour_mode == 0:
			tile_edges = np.mean(tile_temp, axis= 2, keepdims=True)
		else:
			tile_edges = tile_temp

		# direction_array, coherence_map = build_direction_array(tile_temp)
		direction_array, coherence_map = build_direction_array_weighted(tile_edges)
		edge_map = multi_channel_structure_tensor_edge(coherence_map, tile_edges, 
												 sigma_grad=1.0, sigma_tensor=3.0)

		edge_map2 = np.expand_dims(edge_map, axis=2)
		tile_temp2 = np.repeat(edge_map2, n_channels, 2) 	
			
	else:
		print('The calculation selected is not available')
		tile_temp2 = None
	
	return tile_temp2

#endregion

#region Edge detection
def normalize(arr):	
	if arr.dtype != np.float32:
		arr = arr.astype(np.float32)
	
	output = (arr - arr.min()) / (arr.max() - arr.min() + 1e-8) #(0 - 1)

	return output

def build_direction_array(tile_data):
	#Based on 'direction adaptative Pearson correlation coefficient'
	#2020_Zhang et al._Orthogonal microscopy image acquisition analysis technique for rock sections

	step = 1

	#'edge' mode repeats the last pixel (homogeneous continuation of grain beyond tile)
	padded_data = np.pad(tile_data, ((step, step), (step, step), (0, 0), (0, 0)), mode='edge')

	#'center' is the original image, but extracted from the padded version
	H, W, depth, n_layers = tile_data.shape
	center = padded_data[step : step + H, step : step + W, :, :]

	#shifts
	directions = {
		"0_deg":   [(step, 0), (-step, 0)], 
		"45_deg":  [(step, step), (-step, -step)],
		"90_deg":  [(0, step), (0, -step)], 
		"135_deg": [(-step, step), (step, -step)],
	}	

	#constants
	epsilon= 10**(-8)	
	sum_c  = np.sum(center, axis=3)
	sum_c2 = np.sum(center**2, axis=3)
	var_c = np.clip(n_layers * sum_c2 - sum_c**2, 0, None) #precision jitter
	sqrt_var_c = np.sqrt(var_c)
	
	direction_array = np.zeros((H, W, depth, len(directions)), dtype= np.float32) #pre-allocate

	for k, (angle, shift_list) in enumerate(directions.items()):

		n_shifts = len(shift_list)
		shift_array = np.zeros((H, W, depth, n_shifts), dtype= np.float32) #pre-allocate

		for item, (dx, dy) in enumerate(shift_list):		

			# Slice the neighbor shifted by (dx, dy)
			x_shifted = step + dx
			y_shifted = step + dy
			neighbor = padded_data[y_shifted : y_shifted + H, x_shifted : x_shifted + W, :, :]
			
			#Equation		
			sum_n  = np.sum(neighbor, axis=3)		
			sum_n2 = np.sum(neighbor**2, axis=3)
			sum_cn = np.sum(center * neighbor, axis=3) #cross-correlation

			#Covariance numerator		
			term1 = n_layers * sum_cn - sum_c * sum_n

			#Variance denominators			
			var_n = np.clip(n_layers * sum_n2 - sum_n**2, 0, None)
			term2 = (sqrt_var_c*np.sqrt(var_n) + epsilon)

			output = term1 / term2

			shift_array[:, :, :, item] = output

		array1 = np.min(shift_array, axis= 3)
		direction_array[:, :, :, k] = array1	
	
	# --- 2. COHERENCE (boundaries are where directions disagree)---
	# Inside grain/bg: Max and Min are both high (Max - Min is LOW)
	# On Edge: Max is high (parallel), Min is low (across). (Max - Min is HIGH)	
	max_d = np.max(direction_array, axis=3)
	min_d = np.min(direction_array, axis=3)	
	coherence_map = np.clip(max_d - min_d, 0, 1)

	return direction_array, coherence_map

def build_direction_array_weighted(tile_data):

	H, W, depth, n_layers = tile_data.shape 
	epsilon = 10**(-8)  
	step = 1    
	directions = {
		"0_deg":   [(step, 0), (-step, 0)], 
		"45_deg":  [(step, step), (-step, -step)],
		"90_deg":  [(0, step), (0, -step)], 
		"135_deg": [(-step, step), (step, -step)],
		} 
	sharpness_level = 15 #"pinches" the edge.

	# 1. Attributes of every pixel
	mean_t = np.mean(tile_data, axis=3)     
	range_r = np.ptp(tile_data, axis=3)	
	modulation = range_r / (mean_t + epsilon) #signal quality

	padded_data = np.pad(tile_data, ((step, step), (step, step), (0, 0), (0, 0)), mode='edge')	
	padded_mean = np.pad(mean_t, ((step, step), (step, step), (0, 0)), mode='edge')
	padded_mod = np.pad(modulation, ((step, step), (step, step), (0, 0)), mode='edge')

	#pre-calculate
	center = padded_data[step : step + H, step : step + W, :, :]         
	sum_c   = np.sum(center, axis=3)
	sum_c2  = np.sum(center**2, axis=3)
	var_c   = np.clip(n_layers * sum_c2 - sum_c**2, 0, None)
	sqrt_var_c = np.sqrt(var_c)
	
	#pre-allocate
	direction_array = np.zeros((H, W, depth, len(directions)), dtype=np.float32)

	for k, (angle, shift_list) in enumerate(directions.items()):
		n_shifts = len(shift_list)
		shift_array = np.zeros((H, W, depth, n_shifts), dtype=np.float32)

		for item, (dx, dy) in enumerate(shift_list):        
			x_s, y_s = step + dx, step + dy
			neighbor = padded_data[y_s : y_s + H, x_s : x_s + W, :, :]
			
			# --- Pearson Correlation ---
			sum_n, sum_n2 = np.sum(neighbor, axis=3), np.sum(neighbor**2, axis=3)
			sum_cn = np.sum(center * neighbor, axis=3)
			term1 = n_layers * sum_cn - sum_c * sum_n
			var_n = np.clip(n_layers * sum_n2 - sum_n**2, 0, None)
			output = term1 / (sqrt_var_c * np.sqrt(var_n) + epsilon)		
			
			# --- Local Attributes ---
			n_mean = padded_mean[y_s : y_s + H, x_s : x_s + W, :]
			n_mod  = padded_mod[y_s : y_s + H, x_s : x_s + W, :]
			
			#penalize if the neighbor has LOWER range (moving towards edge)			
			local_mod_weight = np.clip(n_mod / (modulation + epsilon), 0, 1)

			#Directional Edge Penalty
			mean_diff = np.abs(mean_t - n_mean) / (mean_t + n_mean + epsilon)
			edge_penalty = np.exp(-sharpness_level * mean_diff)

			# Raw weighted correlation for this specific neighbor
			shift_array[:, :, :, item] = output * local_mod_weight * edge_penalty			
		
		direction_array[:, :, :, k] = np.min(shift_array, axis=3) #min is the best
	
	# --- 2. COHERENCE (boundaries are where directions disagree)---
	# Inside grain/bg: Max and Min are both high (Max - Min is LOW)
	# On Edge: Max is high (parallel), Min is low (across). (Max - Min is HIGH)	
	max_d = np.max(direction_array, axis=3)
	min_d = np.min(direction_array, axis=3)	
	coherence_map = np.clip(max_d - min_d, 0, 1)

	return direction_array, coherence_map

def multi_channel_structure_tensor_edge(coherence_map, raw_xpl_stack, sigma_grad=1.0, sigma_tensor=3.0):
	"""
	Fuses Pearson correlation 'coherence' with Morphological Structure Tensor edges. 
	Pearson it's better for XPL signatures than Structure but they complement well.
	Structure edges amplify edges where Transmittance and Range are low 
	(typical of grain boundaries).
	The fusion uses "Boundary Affinity Weight" that calculates a weighted 
	principal eigenvalue of a multi-channel structure tensor.		
	"""
	
	epsilon = 1e-8   
	k = 0.01  #lower k = brighter weak edges.
	
	# 1. OPTICAL EDGE 	  
	coherence_map = grey_dilation(coherence_map, size=(3, 3, 1)) 
	
	if coherence_map.ndim == 3:
		opt_edge_mean = np.mean(coherence_map, axis=2)
	else:
		opt_edge_mean = coherence_map
		
	opt_edge_norm = normalize(opt_edge_mean)
	
	# 2. BOUNDARY AFFINITY MASK
	# Weight is HIGH when mean transmittance and range are LOW.
	mean_t = np.mean(raw_xpl_stack, axis=(2, 3)) 
	range_r = np.ptp(raw_xpl_stack, axis=3).mean(axis=2) 
			   
	t_weight = 1.0 / (mean_t / (mean_t.max() + epsilon) + 0.1)
	r_weight = 1.0 / (range_r / (range_r.max() + epsilon) + 0.1)   	
	boundary_mask = normalize(t_weight * r_weight)

	# 3. STRUCTURE TENSOR (Morphological Edge)
	# Average across the rotation (axis 3) to get a stable base image
	avg_rgb = np.mean(raw_xpl_stack, axis=3)    
	h, w, c = avg_rgb.shape

	Jxx = np.zeros((h, w), dtype=np.float32)
	Jyy = np.zeros((h, w), dtype=np.float32)
	Jxy = np.zeros((h, w), dtype=np.float32)

	for i in range(c):
		channel = avg_rgb[:, :, i]
		dx = ndimage.gaussian_filter(channel, sigma=sigma_grad, order=[1, 0])
		dy = ndimage.gaussian_filter(channel, sigma=sigma_grad, order=[0, 1])
		
		Jxx += ndimage.gaussian_filter(dx**2, sigma=sigma_tensor)
		Jyy += ndimage.gaussian_filter(dy**2, sigma=sigma_tensor)
		Jxy += ndimage.gaussian_filter(dx*dy, sigma=sigma_tensor)
	
	avg_diag = (Jxx + Jyy) / 2
	dist_diag = np.sqrt(((Jxx - Jyy) / 2)**2 + Jxy**2)
	lambda_1 = avg_diag + dist_diag 	
	morph_edge = normalize(lambda_1 * boundary_mask) #suppress noise	

	#Combination	
	combined = opt_edge_norm * morph_edge #clean image		
	equalized = combined / (combined + k) #saturate
	final_composite = normalize(equalized)

	return final_composite

#endregion

