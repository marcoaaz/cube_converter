import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy import ndimage
from matplotlib.colors import ListedColormap

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

from ray_tracing_module import normalize
from prototype_module import segment_grains_scipy, filter_small_features

#User input
filename = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\slides_processing\curiosity\edges_tl-xpl_sat0.01_n36_medF8.tif"

output_basename = f'grains.tif'
parentDir = os.path.dirname(filename)
file_output = os.path.join(parentDir, output_basename)

final_composite0 = pyvips.Image.new_from_file(filename)
final_composite = normalize(final_composite0.numpy())

labels, random_colors = segment_grains_scipy(final_composite, threshold= 0.25, 
							  seed_min_dist= 120, smooth_sigma= 1)
labels_cleaned = filter_small_features(labels, min_area=3500)

random_cmap = ListedColormap(random_colors)

print("Visualizing results...")

fig, axes = plt.subplots(1, 2, figsize=(20, 12))
# 3. Raw Labels
axes[0].imshow(labels, cmap=random_cmap)
axes[0].set_title('Raw Segmentation')
axes[0].axis('off')

# 4. Filtered Labels
axes[1].imshow(labels_cleaned, cmap=random_cmap)
axes[1].set_title('Filtered Segmentation')
axes[1].axis('off')

plt.tight_layout()
plt.show()

