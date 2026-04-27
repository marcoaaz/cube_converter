

#JAVA_HOME is set to: C:\Program Files\Amazon Corretto\jdk1.8.0_422
#Zulu JDK+FX 8 recommendation C:\Users\acevedoz\zulu8.88.0.19-ca-jdk8.0.462-win_x64\bin
# java_home_path = os.environ.get('JAVA_HOME')
  
import os
java_home_path = r"C:\Users\acevedoz\zulu8.88.0.19-ca-jdk8.0.462-win_x64"
os.environ['JAVA_HOME'] = java_home_path

import imagej

# C:\Users\acevedoz\Fiji
# C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\fiji_28sep24\Fiji.app
ij = imagej.init(r"C:\Users\acevedoz\Fiji", mode='headless')

import scyjava

from loci.plugins import BF
# from loci.plugins.in import ImporterOptions
from ij import IJ

# Create ImporterOptions object
options = ImporterOptions()




