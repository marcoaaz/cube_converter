
import os
import sys
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

#region Segmentation

def segment_grains_scipy(final_composite, threshold=0.15, 
						 seed_min_dist=20, smooth_sigma=0):
	"""
	Segments grains using watershed.
	
	Args:
		final_composite: 2D array, edges are low, grains are high (0-1 range).
		threshold: Intensity value to separate grains from edges.
		seed_min_dist: Size of the filter to find seed centers. 
					   Increase to reduce oversegmentation.
		smooth_sigma: Gaussian blur radius for the topography.
					  Increase to reduce noise-induced splitting.
	"""
	# 1. Create a binary mask of the 'interior' of grains	
	grain_interior_mask = final_composite < threshold 
	
	# 2. Smooth the topography (optional but recommended to prevent splitting)
	if smooth_sigma > 0:
		# We smooth the edge map so boundaries are less affected by noise
		cost_map_data = ndimage.gaussian_filter(final_composite, sigma=smooth_sigma)
	else:
		cost_map_data = final_composite

	# 3. Distance Transform on the interior mask
	dist_map = ndimage.distance_transform_edt(grain_interior_mask)
	
	# 4. Find Seeds
	# Find local peaks in the distance map to mark the center of grains.
	local_max_bool = ndimage.maximum_filter(dist_map, size=seed_min_dist) == dist_map
	
	# Keep seeds only inside the grain interior
	seeds_int = local_max_bool.astype(np.int32) * grain_interior_mask.astype(np.int32)
	
	# Label the seeds with unique integers (1, 2, 3...)
	markers, _ = ndimage.label(seeds_int)
	
	# 5. Watershed (must be uint16)	
	cost_map = ((1.0 - cost_map_data) * 65535).astype(np.uint16)
	labels = ndimage.watershed_ift(cost_map, markers)
	
	# 6. Mask the result back to the grain interior
	labels1 = labels * grain_interior_mask.astype(labels.dtype)
	
	#colour map
	unique_labels = np.unique(labels1)
	num_labels = len(unique_labels)
	random_colors = np.random.rand(num_labels, 3)
	background_index = np.where(unique_labels == 0)[0]
	if len(background_index) > 0:
		random_colors[background_index[0]] = [0, 0, 0] 	

	return labels1, random_colors

def filter_small_features(labels, min_area=3500):
	"""
	Removes small labels (inclusions/noise) by area.
	"""
	# Find counts of each label
	label_ids, counts = np.unique(labels, return_counts=True)
	
	# Create a mask of 'valid' labels that are large enough
	# We ignore label 0 (which is usually background)
	valid_mask = counts >= min_area
	valid_labels = label_ids[valid_mask]
	
	# Zero out the labels that didn't make the cut
	mask = np.isin(labels, valid_labels)
	cleaned_labels = np.where(mask, labels, 0)
	
	return cleaned_labels


#endregion