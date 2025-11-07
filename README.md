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
  - **The input list** allows stacking optical (and truly any image from any instrument) as long as they are pre-registered (aligned), e.g., ray tracing, chemical images, phase map (e.g., multi-modal z-stacks).
  - **Output pyramidal OME-TIFF files** of ~250 GB can be opened in a few seconds without latency. 
  
### Image Metadata Extraction
- **Automatic metadata extraction** from microscopy files:
  - **VSI files** (Evident) - acquisition settings, microscope info, channels
  - **Steps metadata** - CSV files are saved tracking the semantic and numerical outputs from each processing step within the GUI and allow reproducibility.
    
### Adaptive Interface
- **Grid design** - adapts to the window size

---

## 🖥️ Requirements*

- **Python** 3.9.13
- **PyQt5** 5.15.11 for GUI design
- **pyinstaller** 6.15.0 for compiling
- **multiprocessing** (included with most Python installations) for parallel processing
- **Additional libraries**:
  - `pyvips 3.0.0`* - for enabling extreme processing speed with image pyramid outputs [link](https://pypi.org/project/python-bioformats/)
  - `javabridge 1.0.19` - CellProfiller tool for opening Java virtual machines within processing cores [link](https://pypi.org/project/javabridge/)
  - `python-bioformats 4.1.0` - for warping Bio-Formats (Java library) within Python [link](https://github.com/Arcadia-Science/readlif)
  - `ome-types 0.6.1` - for read/write OME-TIFF metadata [link](https://pypi.org/project/ome-types/)

*pyvips requires internally defining the path to libvips binaries (Windows DLL) in your PC. I downloaded the folder from [link](https://github.com/libvips/build-win64-mxe/releases/tag/v8.16.0) and unzipped to 'c:/vips-dev-8.16/bin'

The current version was demonstrated to work on Windows 11 OS.

---

## 📁 Versions Available

### ReMInD Full (Remind_v2.27.py)
- Complete feature set including RDM connectivity
- UQ InstGateway integration for institutional users
- Recommended for University of Queensland researchers

---

## ⌨️ Creating the Executable

1. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```
2.  Place the python file into its own directory with no spaces
3.  In Command Prompt navigate to this directory with the script
4.  Run the following command replacing <scriptname> with your own (or e.g. Remind_v2.27.py)
   ```bash
   pyinstaller --onefile --windowed --name "executablename" --add-data "CZI_MetadataGUI.py;." --add-data "LIF_MetadataGUI.py;." --add-data "ND2_v2a.py;." <scriptname>.py
   ```
5.  Your single executable will be within the dist directory that was created.


## 📦 Packaged Executable
- The Remind.exe file can be downloaded and is fully self contained for Windows 11
- If using the custom icon file (provided) you will need to create a shortcut to the Remind.exe to use custom icons in Windows 11
