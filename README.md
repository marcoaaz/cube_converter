# Cube Converter

**Version**: 1.2  
**Binary download**: [Windows 11](https://zenodo.org/records/19689989)  
**Developer**: Dr Marco Acevedo Z. (maaz.geologia@gmail.com)  
**Affiliation**: School of Earth and Atmospheric Sciences, Queensland University of Technology   
**Date**: 28-April-2026  
**Citation**: [Acevedo Zamora & Kamber 2023](https://www.mdpi.com/2075-163X/13/2/156)  
**Original scripts**: [old repository](https://github.com/marcoaaz/Acevedo-Kamber)  

---

## 📖 Overview

The package to process petrographic microscopy multi-angle whole-slide images as ray traced images and 'virtual' z-stacks for next generation image analysis pipelines. It process full resolution polarised microscopy experiments configured in Evident [VS200 slide scanner](https://evidentscientific.com/en/products/slide-scanners/vs200) (acquisition routines after Acevedo Zamora & Kamber, 2023). The tool can represent a set of multi-angle polarised images (plane-polarised (PPL) pleochroism and cross-polarised (XPL) birefringence) as summary "ray tracing" (descriptive statistics: max, min, std, mean, index of max/min) images. 

The graphical user interface:

<p align="center">
  <img width=80% height=80% alt="Image" src="https://github.com/user-attachments/assets/5f8241f9-ee7d-41e4-9f5a-5cf71db7f3d0" />
</p>

---

## 🚀 Features

### Core Functionality
- **Graphical User Interface (GUI) following two steps** for processing raw images without having licensed software (costing around 10K AUD)
- **High reliability and performance** due to parallelised implementation
- Polarised microscopy processor
  - **Basic image processing** to allow changing an image pyramid level, tile size, and output brightness
  - **Menus for editing input and output images** according to the data acquisition nomenclature used in the VS200 petrographic slide scaner (configured by Marco Acevedo)
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

The current Cube converter version was demonstrated to work in Windows 11 OS.

- **Python** 3.9.13
- **PyQt5** 5.15.11 for running GUI (designed with PyQt5-tools)
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

- Suitable for reading and processing VSI files (CellSense format) saved from Evident VS200 slide scanner at QUT (acquisition protocols by Acevedo Zamora and Kamber (2023)).
- All experiment and image processing metadata are saved for reproducibility.
- The multi-modal Z-stack generator (right hand side of the interface) is able to save OME-TIFF files to be opened in almost any software (e.g., QuPath, Evident software suite)
  
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
- A Terminal opened next to the main window indicates the progress of processing your file
- An Error handling mechanism pops up if the user inputs a wrong value in the GUI options. For persistent errors, please, send me a screenshot

## Issues and future work

This is a beta version that will soon be improved with user feedback. If you are not familiar to coding but you have proposals/ideas, you are welcome to reach out because this project is still growing. 

- I had in mind:
  - Cloud implementation with more cores
  - Using Bio-Formats, the software can support many more light microscopy light microscopy [formats](https://docs.openmicroscopy.org/bio-formats/5.8.2/supported-formats.html), e.g., CZI from Zeiss [AxioScan Geo](https://www.zeiss.com/microscopy/en/products/imaging-systems/axioscan-7.html) (Zeiss Microscopy). A first step has been taken by Dr. Nicholas Condon with his [ReMInD](https://github.com/NickCondon/ReMInD/) software for metadata extraction.
  - Implementation of Cube Converter for compatibility with a routine using the 3D printed [PyAutoStage](https://sites.google.com/msu.edu/piautostage/home) ([Steiner and Rooney, 2021](https://doi.org/10.1029/2021GC009693)).
  - Continue the implementation of ray tracing using the Pipeline for optic-axis mapping (POAM) [(Acevedo Zamora et al., 2024)](https://onlinelibrary.wiley.com/doi/10.1111/jmi.13284)

If you are programmer, please support us translating the program for compilation in Mac OS and Linux.


Thanks.  
Marco Acevedo
