# Cube Converter
# The package to process petrographic microscopy multi-pol whole-slide images as ray traced scans and 'virtual' z-stacks for next generation image analysis pipelines.

**Version**: 1 (beta)  
**Author**: Dr Marco Acevedo Z. (maaz.geologia@gmail.com)  
**Affiliation**: School of Earth and Atmospheric Sciences, Queensland University of Technology  
**Date**: November 2025  
**Citation**: [Acevedo Zamora & Kamber 2023](https://www.mdpi.com/2075-163X/13/2/156)  
**Previous versions**: [Original repository](https://github.com/marcoaaz/Acevedo-Kamber)  

---

## 📖 Overview

Cube converter allows microscopists and researchers to process full resolution polarised microscopy experiments configured in Evident VS200 slide scanners (acquisition routines after Acevedo Zamora & Kamber, 2023). The tool represents a set of multi-angle polarised images (plane-polarised (PPL) pleochroism and cross-polarised (XPL) birefringence) as summary "ray tracing" (descriptive statistics: max, min, std, mean, index of max/min) images. 

These images are friendlier for pixel/object classification/segmentation tasks due to the homogenisation of colours regarless of "virtual" stage rotation. Segmentation has been demonstrated to work with [QuPath](https://qupath.github.io/) ([Bankhead et al., 2017](https://www.nature.com/articles/s41598-017-17204-5)) using the [pixel classifier](https://qupath.readthedocs.io/en/stable/docs/tutorials/pixel_classification.html) tool. Segmenting multi-channel images with reflected light (RL), PPL-max, and XPL-max only has achieved results comparable to SEM-based Automated mineralogy systems. This, of course, if having a "friendly" mineralogy and colour contrast (robust to crystal orientation dependance).

Locally, the output intermediate/final (original scans and ray tracing images) images are saved in a structured folder sequence for each input VSI file input (see interface). The exporation process records the data acquisition and processing metadata for potential future documentation in [OMERO Server](https://www.openmicroscopy.org/omero/). 

<img width=100% height=100% alt="Image" src="https://github.com/user-attachments/assets/2c76b648-eaba-449d-af6f-57b0643c1d71" />

---

## 🚀 Features

### Core Functionality
- **Graphical User Interface (GUI) following two steps** for processing raw optical microscopy images without having to pay for a license (proprietary instrument software is 10K AUD)
- **High reliability and performance** due to parallelised implementation
- Polarised microscopy processor
  - **Basic image processing** to allow changing an image pyramid level, tile size, and output brightness
  - **Menus for editing input and output images** according to the data acquisition nomenclature used in the VS200 petrographic slide scaner laboratory at Queensland University of Technology (configured by Marco Acevedo)  
- Multi-modal z-stack generator
  - **The input list** allows stacking single optical and/or align images (from any instrument) as long as they have the same X-Y dimensions into multi-modal z-stacks (e.g. ray tracing, chemical images, phase map).
  - **Interactive output images** thanks to pyramidal OME-TIFF format allowing to read ~250 GB files in a few seconds and without latency. 
  
### Image Metadata Extraction
- **Automatic metadata extraction** from microscopy files:
  - **VSI files** (Evident) - acquisition settings, microscope info, channels
  - **Steps metadata** - CSV files are saved tracking the semantic and numerical outputs from each processing step within the GUI and allow reproducibility.
    
### Adaptive Interface
- **Grid design** - adapts to the window size

---

## 🖥️ Requirements*

The current Cube converter version was demonstrated to work on Windows 11 OS.

- **Python** 3.9.13
- **PyQt5** 5.15.11 for GUI design
- **pyinstaller** 6.15.0 for compiling with modified generated main.spec file*
- **multiprocessing** (included with most Python installations) for parallel processing
- **Additional libraries**:
  - `pyvips 3.0.0`** - for enabling extreme processing speed with image pyramid outputs [link](https://github.com/libvips/pyvips)
  - `javabridge 1.0.19`*** - CellProfiller tool for opening Java virtual machines within processing cores [link](https://pypi.org/project/javabridge/)
  - `python-bioformats 4.1.0` - for warping Bio-Formats (Java library) within Python [link](https://pypi.org/project/python-bioformats/)
  - `ome-types 0.6.1` - for read/write OME-TIFF metadata [link](https://pypi.org/project/ome-types/)

*Ensure the main.spec file contains:

    datas=[
        ("icons", "icons"),
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/javabridge/jars/*", "javabridge/jars"), 
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/javabridge/*", "javabridge"),
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/bioformats/jars/*", "bioformats/jars"),                
        ("E:/Alienware_March 22/current work/00-new code May_22/vsiFormatter/vsi_trial1/Lib/site-packages/bioformats/*", "bioformats"),
        ("c:/vips-dev-8.16/bin", "vips"),
        ("C:/Program Files/Amazon Corretto/jdk1.8.0_462", "jdk_folder_in_bundle")
        ],
    hiddenimports=[
        'xsdata_pydantic_basemodel.hooks', 
        'xsdata_pydantic_basemodel.hooks.class_type',
        'bioformats', 'javabridge'
        ],
        
- **pyvips requires internally defining the path to libvips binaries (Windows DLL) in your PC. I downloaded the folder from [link](https://github.com/libvips/build-win64-mxe/releases/tag/v8.16.0) and unzipped to 'c:/vips-dev-8.16/bin'
- ***javabridge will require a hacky manual modification to work properly:  
  Within ..\<your-environment-name>\Lib\site-packages\javabridge\locate.py > find_javahome()  
  Change line 76 original line: 

      java_path = os.path.join(app_path, 'java')
  
  to

      java_path = os.path.join(app_path, '_internal/jdk_folder_in_bundle')
  
  This is required for adopting what was written in the "main.spec" description and is provided to pyinstaller during compilation.  

---

## 📁 Versions Available

### Cube converter v1 (main.py)
- File to call the functionality and app interface (cubeConverter_v3.py)
- Suitable for reading and processing VSI files (CellSense format) saved from Evident VS200 slide scanner (at QUT)
- All metadata extraction features included
  
---

## ⌨️ Creating the Executable

1.  In VSCode or Anaconda, activate <your-environment-name>
2.  **pip install -r requirements.txt**
2.  In the terminal, run:
   ```bash
   pyinstaller main.py
   ```
5.  Edit the main.spec file (see edits in Requirements section above)
   ```bash
   pyinstaller main.spec
   ```
6.  The executable will be next to a bundled app folder at:  
   "..\<your-environment-name>\dist\Cube Converter v1\Cube Converter v1.exe"


## 📦 Packaged Executable
- Cube Converter v1.exe works for Windows 11 and it is not fully self contained (for efficiency while opening the app)
- A Terminal will be open to indicate the progress of processing your file
- An Error handling mechanism pops up if the user inputs a wrong value in the GUI options. For persistent errors, please, send me a screenshot

## Issues and future work
- This is a beta version that will soon be improved with user feedback
- I had in mind:
  - Allowing compatibility with more light microscopy light microscopy formats, e.g., CZI from Zeiss AxioScan Geo (Zeiss Microscopy)
  - Implementing ray tracing using the Pipeline for optic-axis mapping (POAM) [(Acevedo Zamora et al., 2024)](https://onlinelibrary.wiley.com/doi/10.1111/jmi.13284)
- If you are not familiar to coding but you have proposals/ideas, you are welcome to contact me as well. This is open-source :smile:

## Citing Phase interpreter
- The software depends on open-source as well (see above) and scientific citations/feedback. The following research papers have contributed to its evolution:
  - Acevedo Zamora, M. A., & Kamber, B. S. (2023). Petrographic Microscopy with Ray Tracing and Segmentation from Multi-Angle Polarisation Whole-Slide Images. Minerals, 13(2), 156. https://doi.org/10.3390/min13020156   
  - Acevedo Zamora, M. (2024). Petrographic microscopy of geologic textural patterns and element-mineral associations with novel image analysis methods [Thesis by publication, Queensland University of Technology]. Brisbane. https://eprints.qut.edu.au/248815/
  - Burke, T. M., Kamber, B. S., & Rowlings, D. (2025). Microscopic investigation of incipient basalt breakdown in soils: implications for selecting products for enhanced rock weathering [Original Research]. Frontiers in Climate, Volume 7 - 2025. https://doi.org/10.3389/fclim.2025.1572341 

