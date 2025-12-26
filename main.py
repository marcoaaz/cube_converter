
'''
main.py

Version 1 of software GUI processing VS200 slide scanner files.

Citation: https://doi.org/10.3390/min13020156

Documentation:
https://www.youtube.com/watch?v=2EjrLpC4cE4&t=163s
https://pyinstaller.org/en/stable/usage.html

Created: 15-Sep-25, Marco Acevedo
Updated: 9-Oct-25, 12-Dec-25

Written in python 3.9.13 (vsi_trial1)

'''
#Dependencies
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from cubeConverter_v4 import Ui_MainWindow #relative path

class Window(QMainWindow, Ui_MainWindow):

	#region GUI
	def __init__(self):
		super().__init__()
		self.setupUi(self)

		#Recovering images	
		# relative_path = sys._MEIPASS #PyInstaller executable
		bundle_dir = os.path.abspath(os.path.dirname(__file__)) #relative path
		icon_file_path = os.path.join(bundle_dir, "icons/cube_icon.ico")
		image_file_path0 = os.path.join(bundle_dir, "icons/QUT-Logo.png")
		image_file_path1 = os.path.join(bundle_dir, "icons/AuScope_logo.png")
		image_file_path2 = os.path.join(bundle_dir, "icons/3236907.png")

		#Window
		self.setWindowTitle("Cube Converter v1.0")
		self.setWindowIcon(QtGui.QIcon(icon_file_path))
		self.setMinimumSize(600, 600)
		self.setWindowFlags(self.windowFlags()) 

		#Image update
		self.label_22.setPixmap(QtGui.QPixmap(image_file_path2))
		self.label_23.setPixmap(QtGui.QPixmap(image_file_path1))
		self.label_24.setPixmap(QtGui.QPixmap(image_file_path0))

		#Get system info
		available_cores, total_RAM, _ = parse_system_info()        
		assigned_cores = available_cores//2 #half
		self.assigned_RAM = total_RAM[1] #75%    

		#Adjust GUIs
		self.spinBox_2.setMaximum(available_cores)
		self.spinBox_2.setValue(assigned_cores)

		#Default choices		
				
		#checkboxes
		self.items_output = ['reflected', 'ppl', 'xpl', 'rayTracing']  #update manually
		self.items_rt = ['ppl', 'xpl']
		self.items_calculation = ['max', 'min', 'maxIndex']
		self.items_format = ['ometiff']
		self.items_type = ['zstack']
		#widget list
		self.list_widget = [] #z-stack input
		self.list_widget_vsi = [] #vsi input
		self.option1 = 1 #delete intermediate files

		#Define functionality     
		
		#left GUI
		# self.pushButton_2.clicked.connect(self.open_file_dialog) #left  
		self.Add_2.clicked.connect(self.browse_files2)
		self.toolButton_3.clicked.connect(self.move_item_up2)
		self.toolButton_4.clicked.connect(self.move_item_down2)
		self.Remove_2.clicked.connect(self.remove_selected_item2)
		self.Clear_2.clicked.connect(self.remove_all_items2)			
		self.pushButton_7.clicked.connect(self.runningFunction) 		 

		#right GUI		
		self.Add.clicked.connect(self.browse_files)
		self.toolButton.clicked.connect(self.move_item_up)
		self.toolButton_2.clicked.connect(self.move_item_down)
		self.Remove.clicked.connect(self.remove_selected_item)
		self.Clear.clicked.connect(self.remove_all_items)				
		self.pushButton_5.clicked.connect(self.open_folder_dialog) 
		self.pushButton_8.clicked.connect(self.runningFunction2) 		
		
		#Build input lists
		#connect stateChanged signal to a common handler
		self.checkBox_3.stateChanged.connect(lambda state, item="originals": self.update_list(state, item))
		self.checkBox_4.stateChanged.connect(lambda state, item="reflected": self.update_list(state, item))		
		self.checkBox_13.stateChanged.connect(lambda state, item="ppl": self.update_list(state, item))
		self.checkBox_14.stateChanged.connect(lambda state, item="xpl": self.update_list(state, item))
		self.checkBox_12.stateChanged.connect(lambda state, item="rayTracing": self.update_list(state, item))

		self.checkBox.stateChanged.connect(lambda state, item="ppl": self.update_list2(state, item))
		self.checkBox_2.stateChanged.connect(lambda state, item="xpl": self.update_list2(state, item))

		self.checkBox_5.stateChanged.connect(lambda state, item="max": self.update_list3(state, item))
		self.checkBox_7.stateChanged.connect(lambda state, item="min": self.update_list3(state, item))
		self.checkBox_6.stateChanged.connect(lambda state, item="maxIndex": self.update_list3(state, item))
		self.checkBox_8.stateChanged.connect(lambda state, item="minIndex": self.update_list3(state, item))
		self.checkBox_10.stateChanged.connect(lambda state, item="mean": self.update_list3(state, item))
		self.checkBox_11.stateChanged.connect(lambda state, item="median": self.update_list3(state, item))
		self.checkBox_9.stateChanged.connect(lambda state, item="std": self.update_list3(state, item))      

		self.checkBox_17.stateChanged.connect(lambda state, item="ometiff": self.update_list4(state, item))
		self.checkBox_18.stateChanged.connect(lambda state, item="dz": self.update_list4(state, item))

		self.checkBox_15.stateChanged.connect(lambda state, item="zstack": self.update_list5(state, item))
		self.checkBox_16.stateChanged.connect(lambda state, item="individuals": self.update_list5(state, item))

		# High-level enabling  
		self.checkBox_3.toggled.connect(self.on_control_checkbox_toggled) #all
		self.checkBox_12.toggled.connect(self.on_control_checkbox_toggled2) #rt

		# Initialize the state of the target checkbox		
		self.checkBox_4.setEnabled(not self.checkBox_3.isChecked())		
		self.checkBox_13.setEnabled(not self.checkBox_3.isChecked())
		self.checkBox_14.setEnabled(not self.checkBox_3.isChecked())
		self.checkBox.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_2.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_5.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_7.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_6.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_8.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_10.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_11.setEnabled(self.checkBox_12.isChecked())
		self.checkBox_9.setEnabled(self.checkBox_12.isChecked())

	def on_control_checkbox_toggled(self, checked):
		# Set the enabled state of the target checkbox based on the controlling checkbox's state
		self.checkBox_4.setEnabled(not checked)
		self.checkBox_13.setEnabled(not checked)
		self.checkBox_14.setEnabled(not checked)
	
	def on_control_checkbox_toggled2(self, checked):
		# Set the enabled state of the target checkbox based on the controlling checkbox's state
		self.checkBox.setEnabled(checked)
		self.checkBox_2.setEnabled(checked)
		self.checkBox_5.setEnabled(checked)
		self.checkBox_7.setEnabled(checked)
		self.checkBox_6.setEnabled(checked)
		self.checkBox_8.setEnabled(checked)
		self.checkBox_10.setEnabled(checked)
		self.checkBox_11.setEnabled(checked)
		self.checkBox_9.setEnabled(checked)

	#endregion 

	#region Left GUI functions	

	def browse_files2(self):
		# Open a file dialog to select files
		file_dialog = QFileDialog()
		file_paths, _ = file_dialog.getOpenFileNames(
			self, 
			"Select Files", 
			"", 
			"All Files (*);;Evident format (*.vsi)"
			)

		# Add selected file paths to QListWidget
		temp_list = self.list_widget_vsi						
		temp_list_new = []
		if file_paths:			
			for path in file_paths:				
				if path in temp_list:											
					continue				
				else:
					temp_list_new.append(path)												
			
		temp_list.extend(temp_list_new)
		
		self.list_widget_vsi = temp_list
		self.listWidget_2.addItems(temp_list_new)

	def remove_selected_item2(self):
		selected_item = self.listWidget_2.currentItem()
		if selected_item:
			row = self.listWidget_2.row(selected_item)
			removed_item = self.listWidget_2.takeItem(row)
			del removed_item

	def remove_all_items2(self):
		self.listWidget_2.clear()
		self.list_widget_vsi = []

	def move_item_up2(self):
		current_row = self.listWidget_2.currentRow()
		if current_row > 0:
			current_item = self.listWidget_2.takeItem(current_row)
			self.listWidget_2.insertItem(current_row - 1, current_item)
			self.listWidget_2.setCurrentRow(current_row - 1)

	def move_item_down2(self):
		current_row = self.listWidget_2.currentRow()
		if current_row < self.listWidget_2.count() - 1:
			current_item = self.listWidget_2.takeItem(current_row)
			self.listWidget_2.insertItem(current_row + 1, current_item)
			self.listWidget_2.setCurrentRow(current_row + 1)
	
	#checkboxes
	def update_list(self, state, item_value):
		if state == Qt.Checked:
			if item_value not in self.items_output:
				self.items_output.append(item_value)
		else: # state == Qt.Unchecked
			if item_value in self.items_output:
				self.items_output.remove(item_value)        

	def update_list2(self, state, item_value):
		if state == Qt.Checked:
			if item_value not in self.items_rt:
				self.items_rt.append(item_value)
		else: # state == Qt.Unchecked
			if item_value in self.items_rt:
				self.items_rt.remove(item_value)
	
	def update_list3(self, state, item_value):
		if state == Qt.Checked:
			if item_value not in self.items_calculation:
				self.items_calculation.append(item_value)
		else: # state == Qt.Unchecked
			if item_value in self.items_calculation:
				self.items_calculation.remove(item_value)	   
	
	def get_selected_option(self): #save recoloured
		if self.radioButton_4.isChecked():			
			self.option1 = 1
		elif self.radioButton_3.isChecked():			
			self.option1 = 0		
		else:			
			self.option1 = None	

	#endregion

	#region Right GUI functions	

	def browse_files(self):
		# Open a file dialog to select files
		file_dialog = QFileDialog()
		file_paths, _ = file_dialog.getOpenFileNames(
			self, 
			"Select Files", 
			"", 
			"All Files (*);;Images (*.tif)"
			)

		# Add selected file paths to QListWidget
		temp_list = self.list_widget #previous		 				
		
		temp_list_new = []
		if file_paths:			
			for path in file_paths:				
				if path in temp_list:											
					continue				
				else:
					temp_list_new.append(path)												

			#Last accepted directory
			last_path1 = temp_list_new[-1]
			last_path2 = os.path.dirname(last_path1)

		temp_list.extend(temp_list_new)				

		#Store
		self.list_widget = temp_list
		self.listWidget.addItems(temp_list_new)
		self.output_folder = last_path2 #default of 'open_folder_dialog'
		

	def remove_selected_item(self):
		selected_item = self.listWidget.currentItem()
		if selected_item:
			row = self.listWidget.row(selected_item)
			removed_item = self.listWidget.takeItem(row)
			del removed_item

	def remove_all_items(self):
		self.listWidget.clear()
		self.list_widget = []

	def move_item_up(self):
		current_row = self.listWidget.currentRow()
		if current_row > 0:
			current_item = self.listWidget.takeItem(current_row)
			self.listWidget.insertItem(current_row - 1, current_item)
			self.listWidget.setCurrentRow(current_row - 1)

	def move_item_down(self):
		current_row = self.listWidget.currentRow()
		if current_row < self.listWidget.count() - 1:
			current_item = self.listWidget.takeItem(current_row)
			self.listWidget.insertItem(current_row + 1, current_item)
			self.listWidget.setCurrentRow(current_row + 1)

	#checkboxes
	def update_list4(self, state, item_value):
		if state == Qt.Checked:
			if item_value not in self.items_format:
				self.items_format.append(item_value)
		else: # state == Qt.Unchecked
			if item_value in self.items_format:
				self.items_format.remove(item_value)  

	def update_list5(self, state, item_value):
		if state == Qt.Checked:
			if item_value not in self.items_type:
				self.items_type.append(item_value)
		else: # state == Qt.Unchecked
			if item_value in self.items_type:
				self.items_type.remove(item_value)  

	#Final step
	def open_folder_dialog(self):
		# Open the folder selection dialog
		folder_path = QFileDialog.getExistingDirectory(
			self,   # Parent widget
			"Select Output Folder",  # Dialog title
			"" # app working dir= QDir.currentPath()
			)			      

		if folder_path: # If selection was made
			self.output_folder = folder_path
	
	#endregion

	#region Main script 
	
	def runningFunction(self):        	
		print('Processing pyramid(s) as OME-TIFF..')
		
		#User input
		fileList = qListWidget_list(self.listWidget_2)					
		sel_level = self.spinBox.value()
		items_output = self.items_output
		modality_list = self.items_rt
		statistic_list = self.items_calculation
		tileSize = int(self.comboBox.currentText())
		percentOut = self.doubleSpinBox.value()        
		n_cores = self.spinBox_2.value()
		delete_intermediate = self.option1

		#Script		
		
		#default
		assigned_RAM = self.assigned_RAM                 

		#Output convention
		condition1 = "originals" in items_output
		condition2 = "ppl" in items_output
		condition3 = "xpl" in items_output
		condition4 = "reflected" in items_output
		condition5 = "rayTracing" in items_output
		conditions = [condition1, condition2, condition3, condition4, condition5]

		modality_logical = [ any([item.find(str) != -1 for item in items_output]) for str in modality_list ] #ppl, xpl		

		#Main script
		
		for image_path in fileList:

			#Folder convention
			dirname1 = os.path.dirname(image_path)
			basename1 = os.path.basename(image_path).replace(".vsi", "")
			workingDir1 = os.path.join(dirname1, f"processed_level{sel_level:02d}_{basename1}")
			mkdir2(workingDir1) #remover= mkdir1, keeper= mkdir2          

			read_metadata_function(image_path, assigned_RAM)    
					
			save_tiles_function(image_path, sel_level, tileSize, n_cores, assigned_RAM, conditions)          
			
			if condition1 or condition2 or condition3 or condition4:                
				join_original_tiles_function(workingDir1, conditions)   

			if (condition1 or condition2 or condition3) and condition5 and all(modality_logical):
				ray_tracing_function(workingDir1, modality_list, statistic_list, n_cores)     
				join_rt_tiles_function(workingDir1, statistic_list, percentOut)  

			elif not all(modality_logical):
				modality_logical_not = [not elem for elem in modality_logical]
				print(f"Error: {list(compress(modality_list, modality_logical_not))} needs to be included in the initial export.")    

			if delete_intermediate == 1:
				delete_intermediate_files(workingDir1)

			print(f'Ready: {basename1}')
		
		print('Finished.')

	def runningFunction2(self):  
		print('Generating multi-modal image..')		
		
		#User input
		fileList2 = qListWidget_list(self.listWidget)		
		format_list = self.items_format
		type_list = self.items_type
		tileSize = int(self.comboBox_2.currentText())		
		pixel_size_sel = float(self.lineEdit_3.text())
		filename_output = self.lineEdit_2.text()
		output_folder = self.output_folder
		
		#Main script					
		file_output = filename_output + ".tif" 
		output_path = os.path.join(output_folder, file_output)  
		print(f'The output folder was \n {output_folder}')

		#Output convention
		output_ome = "ometiff" in format_list
		output_dz = "dz" in format_list
		output_zstack = "zstack" in type_list
		output_individuals = "individuals" in type_list
		condition1 = output_ome == 1 & output_zstack == 1
		condition2 = output_ome == 1 & output_individuals == 1
		condition3 = output_dz 		

		if condition1:
			print('Generating z-stack..')
			generate_zStack(fileList2, pixel_size_sel, tileSize, output_path)		

		if condition2:
			print('Generating individual image(s)..')
			generate_individualImages(fileList2, pixel_size_sel, tileSize, output_path)
		
		if condition3:
			print('Generating Deep Zoom image(s)..')
			generate_dz(fileList2, pixel_size_sel, tileSize, output_path)
		
		print('Finished.')

	#endregion	

	#region Application

def custom_exception_handler(exc_type, exc_value, exc_traceback):		

	print(f"Unhandled exception caught: {exc_type.__name__}: {exc_value}")
	
	traceback.print_exception(exc_type, exc_value, exc_traceback)
	formatted_traceback_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)	
	traceback_string = "".join(formatted_traceback_lines)

	# Display a message box to the user
	msg_box = QMessageBox()
	msg_box.setIcon(QMessageBox.Critical)
	msg_box.setWindowTitle("Error")
	msg_box.setText("An unexpected error occurred. Please, check inputs")
	msg_box.setInformativeText(traceback_string) #str(exc_value)
	
	msg_box.exec_()

if __name__ == "__main__":
	
	#Dependencies
	import multiprocessing
	multiprocessing.freeze_support() #mandatory
	#(anything before prints for each core)

	import os
	import sys
	import traceback	
	from itertools import compress	

	#relative to script path	
	from helperFunctions.mkdir_options import mkdir2
	from main_functions import delete_intermediate_files, parse_system_info, qListWidget_list
	from main_functions import read_metadata_function, save_tiles_function, ray_tracing_function, join_rt_tiles_function, join_original_tiles_function
	from main_functions import generate_zStack, generate_individualImages, generate_dz
	
	#GUI
	from PyQt5.QtWidgets import QApplication, QFileDialog, QDialog
	from PyQt5.QtCore import Qt
	from PyQt5 import QtGui

	sys.excepthook = custom_exception_handler

	#Run
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit(app.exec_())

	#endregion

