

'''
main.py

Version 1 of software GUI processing VS200 slide scanner files.

Citation: https://doi.org/10.3390/min13020156

Documentation:
https://www.youtube.com/watch?v=2EjrLpC4cE4&t=163s
https://pyinstaller.org/en/stable/usage.html

Created: 15-Sep-25, Marco Acevedo
Updated: 9-Oct-25

Written in python 3.9.13 (vsi_trial1)

'''
#Dependencies
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from cubeConverter_v3 import Ui_MainWindow #relative path

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
		
		#VSI
		path1 = r"C:\Users\acevedoz\OneDrive - Queensland University of Technology\Desktop\data tree\data tree_granite_xenolith\Image_nan1-b_10x.vsi"
		self.lineEdit.setText(path1)		
		#checkboxes
		self.items_output = ['reflected', 'ppl', 'xpl', 'rayTracing']  #update manually
		self.items_rt = ['ppl', 'xpl']
		self.items_calculation = ['max','maxIndex']
		#widget list
		self.list_widget = []

		#Define functionality     
		self.pushButton_2.clicked.connect(self.open_file_dialog) #left  
		self.pushButton_7.clicked.connect(self.runningFunction) 		 

		self.pushButton_5.clicked.connect(self.open_folder_dialog) #right 
		self.pushButton_8.clicked.connect(self.runningFunction2) 		
		self.toolButton.clicked.connect(self.move_item_up)
		self.toolButton_2.clicked.connect(self.move_item_down)
		self.Add.clicked.connect(self.browse_files)
		self.Remove.clicked.connect(self.remove_selected_item)
		self.Clear.clicked.connect(self.remove_all_items)				

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

		#High-level enabling  
		self.checkBox_3.toggled.connect(self.on_control_checkbox_toggled)
		self.checkBox_12.toggled.connect(self.on_control_checkbox_toggled2)

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
	def open_file_dialog(self):
		file_path, _ = QFileDialog.getOpenFileName(
			self,
			"Select File",
			"",  # Initial directory (empty string for default)
			"All Files (*);;Optical scans (*.vsi)" # File filters
		)
		if file_path:
			self.lineEdit.setText(file_path)	

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
	
	#endregion

	#region Right GUI functions	

	def browse_files(self):
		# Open a file dialog to select files
		file_dialog = QFileDialog()
		file_paths, _ = file_dialog.getOpenFileNames(self, "Select Files", "", "All Files (*);;Text Files (*.tif)")

		# Add selected file paths to QListWidget
		temp_list = self.list_widget						
		temp_list_new = []
		if file_paths:			
			for path in file_paths:				
				if path in temp_list:											
					continue				
				else:
					temp_list_new.append(path)												
			
		temp_list.extend(temp_list_new)
		
		self.list_widget = temp_list
		self.listWidget.addItems(temp_list_new)

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
	
	def open_folder_dialog(self):
		# Open the folder selection dialog
		folder_path = QFileDialog.getExistingDirectory(
			self,                                      # Parent widget
			"Select Output Folder",                     # Dialog title
			""                          # Initial directory QDir.currentPath()
		)

		if folder_path: # If a folder was selected (user didn't cancel)
			# Display the selected folder path (e.g., in a QLineEdit)
			self.output_folder = folder_path
	
	#endregion

	#region Main script 

	def runningFunction(self):        	

		#User input
		image_path = self.lineEdit.text()
		sel_level = self.spinBox.value()
		items_output = self.items_output
		modality_list = self.items_rt
		statistic_list = self.items_calculation
		tileSize = int(self.comboBox.currentText())
		percentOut_dsaImage = self.doubleSpinBox.value()        
		n_cores = self.spinBox_2.value()
		
		#Script
		#Folder convention
		dirname1 = os.path.dirname(image_path)
		basename1 = os.path.basename(image_path).replace(".vsi", "")
		workingDir1 = os.path.join(dirname1, "processed_" + basename1)
		mkdir1(workingDir1) #remover= mkdir1, keeper= mkdir2          
		
		#Output convention
		condition1 = "originals" in items_output
		condition2 = "ppl" in items_output
		condition3 = "xpl" in items_output
		condition4 = "reflected" in items_output
		condition5 = "rayTracing" in items_output
		conditions = [condition1, condition2, condition3, condition4, condition5]

		modality_logical = [ any([item.find(str) != -1 for item in items_output]) for str in modality_list ] #ppl, xpl

		#Main_script   
		assigned_RAM = self.assigned_RAM                 
		read_metadata_function(image_path, assigned_RAM)    
				
		save_tiles_function(image_path, sel_level, tileSize, n_cores, assigned_RAM, conditions)          
		
		if condition1 or condition2 or condition3 or condition4:                
			join_original_tiles_function(workingDir1, conditions)   

		if (condition1 or condition2 or condition3) and condition5 and all(modality_logical):
			ray_tracing_function(workingDir1, modality_list, statistic_list, n_cores)     
			join_rt_tiles_function(workingDir1, statistic_list, percentOut_dsaImage)  
		elif not all(modality_logical):
			modality_logical_not = [not elem for elem in modality_logical]
			print(f"Error: {list(compress(modality_list, modality_logical_not))} needs to be included in the initial export.")    

	def runningFunction2(self):  
		
		def qListWidget_list(list_widget):
		
			item_texts = []
			for i in range(list_widget.count()):
				item_texts.append(list_widget.item(i).text())
			return item_texts
		
		#User input
		fileList2 = qListWidget_list(self.listWidget)
		#print(fileList2)
		
		pixel_size_sel = float(self.lineEdit_3.text())
		tileSize = int(self.comboBox_2.currentText())
		filename_output = self.lineEdit_2.text()
		output_folder = self.output_folder
		
		#Script
		mkdir2(output_folder)  
		file_output = filename_output + ".tif" 
		output_path = os.path.join(output_folder, file_output)  

		zStack_montages(fileList2, pixel_size_sel, tileSize, output_path)		

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
	from helperFunctions.mkdir_options import mkdir1, mkdir2 
	from main_functions import read_metadata_function, save_tiles_function, ray_tracing_function, join_rt_tiles_function, join_original_tiles_function, parse_system_info, zStack_montages
	
	#GUI
	from PyQt5.QtWidgets import QApplication, QFileDialog
	from PyQt5.QtCore import Qt
	from PyQt5 import QtGui

	sys.excepthook = custom_exception_handler

	#Run
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit(app.exec_())

	#endregion

