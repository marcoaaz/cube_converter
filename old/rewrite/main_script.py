# -*- coding: utf-8 -*-

"""
main_script.py

Script to process whole-slide images of VS200 slide scanner into individual montages (including ray tracing).

Date created: 27-Aug-25, Marco Acevedo
Date updated: 29-Aug-25, 3-Sep-25

Notes:

For pyramid level 0 at 10X (with 4 CPU cores):
Saving tiles takes 11 min.
Ray tracing takes 
Join tiles takes 

series=pyramid (if z-stack), e.g., level 3 has >7K pixels 

"""

#Dependencies

import os
import time
import numpy as np


#relative to script path
from main_functions import read_metadata_function, save_tiles_function, ray_tracing_function, join_rt_tiles_function, join_original_tiles_function

#save tiles
image_path = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\Image_nan1-b_10x.vsi"
sel_level = 3 #pyramid level
modality_list = ['ppl', 'xpl'] #assuming ideal acquisition
statistic_list = ['max', 'maxIndex']
percentOut_dsaImage = 1

#Script
if __name__ == '__main__':    #lock to only 1 subprocess (Windows) 

    dirname1 = os.path.dirname(image_path)
    basename1 = os.path.basename(image_path).replace(".vsi", "")
    workingDir1 = os.path.join(dirname1, "processed_" + basename1)

    start_time = time.perf_counter()    

    read_metadata_function(image_path)     
    t1 = time.perf_counter()

    assigned_cores = 8
    assigned_RAM = '4G'
    save_tiles_function(image_path, sel_level, 512, assigned_cores, assigned_RAM)  
    t2 = time.perf_counter()
    
    # ray_tracing_function(workingDir1, modality_list, statistic_list)     
    # t3 = time.perf_counter()

    # join_rt_tiles_function(workingDir1, statistic_list, percentOut_dsaImage)    
    # t4 = time.perf_counter()

    # join_original_tiles_function(workingDir1)    
    # t5 = time.perf_counter()
    
    # #Benchmarking
    # t_process = np.array([start_time, t1, t2, t3, t4, t5])
    # t_process_abs = t_process[1:] - t_process[0:-1]
    # elapsed_time = (t_process_abs - start_time)/60
    # formatted_str = np.array_str(elapsed_time, precision=2, suppress_small=True)
    # print(formatted_str)
