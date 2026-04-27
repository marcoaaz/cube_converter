
'''
main.py

Version 1 of software GUI processing VS200 slide scanner files.

Citation: https://doi.org/10.3390/min13020156

Documentation:
https://www.youtube.com/watch?v=2EjrLpC4cE4&t=163s
https://pyinstaller.org/en/stable/usage.html

Created: 15-Sep-25, Marco Acevedo
Updated: 9-Oct-25, 12-Dec-25, 28-Apr-26

Written in python 3.9.13 (vsi_trial1)

'''
#Dependencies
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from cubeConverter_v6 import Ui_MainWindow #relative path

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
		self.setWindowTitle("Cube Converter v1.2")
		self.setWindowIcon(QIcon(icon_file_path))
		self.setMinimumSize(600, 600)
		self.setWindowFlags(self.windowFlags()) 

		#Image update
		self.label_22.setPixmap(QPixmap(image_file_path2))
		self.label_23.setPixmap(QPixmap(image_file_path1))
		self.label_24.setPixmap(QPixmap(image_file_path0))

		#Get system info
		available_cores, process_RAM, available_RAM = parse_system_info()        
		assigned_cores = math.ceil(available_cores/2) #half
		self.assigned_RAM = process_RAM[1] #string

		#Adjust GUI
		self.spinBox_2.setMaximum(available_cores)
		self.spinBox_2.setValue(assigned_cores)

		#Default choices		
		
		#browse buttons
		self.output_folder = ""
		self.output_folder2 = ""

		#checkboxes
		self.init_checkbox_states()		

		#widget list
		self.list_widget = [] #z-stack input
		self.list_widget_vsi = [] #vsi input
		#radio buttons
		self.option1 = 1 #delete intermediate files

		#Define functionality     
		#Build input lists, connect stateChanged signal to a common handler

		#left GUI
		
		self.pushButton_6.clicked.connect(self.open_folder_dialog2) 
		self.listWidget_2.setSelectionMode(QAbstractItemView.ExtendedSelection) #Ctrl/Shift selection
		self.Add_2.clicked.connect(self.browse_files2)
		self.toolButton_3.clicked.connect(self.move_item_up2)
		self.toolButton_4.clicked.connect(self.move_item_down2)
		self.Remove_2.clicked.connect(self.remove_selected_item2)
		self.Clear_2.clicked.connect(self.remove_all_items2)			
		self.pushButton_7.clicked.connect(self.runningFunction) 
	
		self.checkBox_3.stateChanged.connect(lambda state, item="originals": self.update_list(state, item))
		self.checkBox_4.stateChanged.connect(lambda state, item="reflected": self.update_list(state, item))		
		self.checkBox_13.stateChanged.connect(lambda state, item="ppl": self.update_list(state, item))
		self.checkBox_14.stateChanged.connect(lambda state, item="xpl": self.update_list(state, item))

		self.checkBox_12.stateChanged.connect(lambda state, item="rayTracing": self.update_list(state, item))
		self.checkBox.stateChanged.connect(lambda state, item="ppl": self.update_list2(state, item))
		self.checkBox_2.stateChanged.connect(lambda state, item="xpl": self.update_list2(state, item))

		self.checkBox_5.stateChanged.connect(lambda state, item="max": self.update_list3(state, item))
		self.checkBox_7.stateChanged.connect(lambda state, item="min": self.update_list3(state, item))		
		self.checkBox_10.stateChanged.connect(lambda state, item="mean": self.update_list3(state, item))
		self.checkBox_11.stateChanged.connect(lambda state, item="median": self.update_list3(state, item))
		self.checkBox_9.stateChanged.connect(lambda state, item="std": self.update_list3(state, item))      

		self.checkBox_6.stateChanged.connect(lambda state, item="maxIndex": self.update_list3(state, item))
		self.checkBox_8.stateChanged.connect(lambda state, item="minIndex": self.update_list3(state, item))
		self.checkBox_20.stateChanged.connect(lambda state, item="modulation": self.update_list3(state, item))
		self.checkBox_21.stateChanged.connect(lambda state, item="edges": self.update_list3(state, item))

		self.radioButton_4.toggled.connect(self.get_selected_option) #delete intermediate files
		
		# High-level enabling  
		self.checkBox_3.toggled.connect(self.on_control_checkbox_toggled) #all outputs
		self.checkBox_12.toggled.connect(self.on_control_checkbox_toggled2) #ray tracing

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
		self.checkBox_20.setEnabled(self.checkBox_12.isChecked()) 
		self.checkBox_21.setEnabled(self.checkBox_12.isChecked())

		#right GUI		
		
		self.pushButton_5.clicked.connect(self.open_folder_dialog) 
		self.listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection) #Ctrl/Shift selection
		self.Add.clicked.connect(self.browse_files)
		self.toolButton.clicked.connect(self.move_item_up)
		self.toolButton_2.clicked.connect(self.move_item_down)
		self.Remove.clicked.connect(self.remove_selected_item)
		self.Clear.clicked.connect(self.remove_all_items)					
		self.pushButton_8.clicked.connect(self.runningFunction2) 	

		self.checkBox_17.stateChanged.connect(lambda state, item="ometiff": self.update_list4(state, item))
		self.checkBox_18.stateChanged.connect(lambda state, item="dz": self.update_list4(state, item))
		self.checkBox_19.stateChanged.connect(lambda state, item="flat": self.update_list4(state, item))

		self.checkBox_15.stateChanged.connect(lambda state, item="zstack": self.update_list5(state, item))
		self.checkBox_16.stateChanged.connect(lambda state, item="individuals": self.update_list5(state, item))

		#High-level enabling 				
		self.pushButton_7.setEnabled(False) #execution button	
		self.pushButton_8.setEnabled(False)

	def init_checkbox_states(self):
		# Mapping of checkbox objects to their string values
		output_map = {
			self.checkBox_3: 'originals',			
			self.checkBox_13: 'ppl', 
			self.checkBox_14: 'xpl', 
			self.checkBox_4: 'reflected', 
			self.checkBox_12: 'rayTracing'
			}
		rt_map = {
			self.checkBox: 'ppl', 
			self.checkBox_2: 'xpl'
			}
		calc_map = {
			self.checkBox_5: 'max', 
			self.checkBox_7: 'min', 			
			self.checkBox_10: 'mean', 
			self.checkBox_11: 'median', 
			self.checkBox_9: 'std', 
			self.checkBox_6: 'maxIndex', 
			self.checkBox_8: 'minIndex',
			self.checkBox_20: 'modulation', 
			self.checkBox_21: 'edges'
			}
		format_map = {
			self.checkBox_17: 'ometiff',
			self.checkBox_18: 'dz', 
			self.checkBox_19: 'flat', 			
			}
		type_map = {
			self.checkBox_15: 'zstack',
			self.checkBox_16: 'individuals', 			
			}

		# Initialize lists based on what is checked in the GUI
		self.items_output = [val for cb, val in output_map.items() if cb.isChecked()]
		self.items_rt = [val for cb, val in rt_map.items() if cb.isChecked()]
		self.items_calculation = [val for cb, val in calc_map.items() if cb.isChecked()]
		self.items_format = [val for cb, val in format_map.items() if cb.isChecked()]
		self.items_type = [val for cb, val in type_map.items() if cb.isChecked()]

	def keyPressEvent(self, event):
		# Check if Esc was pressed
		if event.key() == Qt.Key_Escape:			
			self.close() 
		else:			
			super().keyPressEvent(event)	
			
#endregion 

#region Extra windows functions		
	
	def closeEvent(self, event):
		#GUI window disappears immediately
		event.accept()

		#Kill the JVM (for Bio-Formats)		
		try:
			javabridge.kill_vm()
		except:
			pass		
		
		os._exit(0) 
		#Note: do not call QApplication.quit() or sys.exit() to 
		# bypass the 'Timer' error and kill the CMD

#endregion

#region Left GUI functions		

	#Disabling Run button
	def update_button_state2(self):		
		if self.listWidget_2.count() == 0:
			self.pushButton_7.setEnabled(False)
		else:
			self.pushButton_7.setEnabled(True)	

	def open_folder_dialog2(self):
		
		path1 = self.lineEdit_3.text() 
		path2 = self.output_folder2 #last_path2
		if path1 != "":
			default_folder = path1
		else:
			if path2 != "":
				default_folder = path2
			else:
				default_folder = ""

		# Open the folder selection dialog
		folder_path = QFileDialog.getExistingDirectory(
			self,   # Parent widget
			"Select Output Folder",  # Dialog title
			default_folder, # app working dir= QDir.currentPath()
			)			      

		if folder_path: # If selection was made
			self.lineEdit_3.setText(folder_path)

	
	def browse_files2(self):
		# 1. Use existing output_folder2 if available, otherwise start empty
		start_dir = getattr(self, 'output_folder2', "")

		# Open a file dialog to select files
		file_dialog = QFileDialog()
		file_paths, _ = file_dialog.getOpenFileNames(
			self, 
			"Select Files", 
			start_dir, # 2. Start at the last used folder
			"All Files (*);;Evident format (*.vsi)"
			)

		# Add selected file paths to QListWidget		

		if file_paths: 
			temp_list = self.list_widget_vsi                        
			temp_list_new = []

			for path in file_paths:             
				if path not in temp_list:
					temp_list_new.append(path)                                                              

			#Only calculate path and update if new files were actually added
			if temp_list_new:				
				self.output_folder2 = os.path.dirname(temp_list_new[-1])			

				# Update the lists and UI
				temp_list.extend(temp_list_new)
				self.list_widget_vsi = temp_list
				self.listWidget_2.addItems(temp_list_new)

		self.update_button_state2()

	#listWidget_2
	def move_item_up2(self):
		# Get selected rows and sort them (0, 1, 2...)
		selected_rows = sorted([self.listWidget_2.row(item) for item in self.listWidget_2.selectedItems()])
		
		# If the first selected row is already at 0, we can't move up
		if not selected_rows or selected_rows[0] == 0:
			return

		for row in selected_rows:
			item = self.listWidget_2.takeItem(row)
			self.listWidget_2.insertItem(row - 1, item)
			item.setSelected(True) # Keep the item selected after move

	def move_item_down2(self):
		# Get selected rows and sort them in REVERSE (...2, 1, 0)
		selected_rows = sorted([self.listWidget_2.row(item) for item in self.listWidget_2.selectedItems()], reverse=True)
		
		# If the last selected row is at the bottom, we can't move down
		if not selected_rows or selected_rows[0] == self.listWidget_2.count() - 1:
			return

		for row in selected_rows:
			item = self.listWidget_2.takeItem(row)
			self.listWidget_2.insertItem(row + 1, item)
			item.setSelected(True)		
	
	def remove_selected_item2(self):
		selected_items = self.listWidget_2.selectedItems()
		if not selected_items:
			return

		for item in selected_items:
			text = item.text()
			if text in self.list_widget_vsi:
				self.list_widget_vsi.remove(text) # Remove from the tracking list

			# We take the item by row index
			row = self.listWidget_2.row(item)
			self.listWidget_2.takeItem(row)

			del item # Explicitly free memory
		
		self.update_button_state2() #update
	
	def remove_all_items2(self):
		self.listWidget_2.clear()
		self.list_widget_vsi = []	

		self.update_button_state2() #update

	#checkboxes

	#Enabling follows the controlling checkbox's state
	def on_control_checkbox_toggled(self, checked):		
		self.checkBox_4.setEnabled(not checked) #rl
		self.checkBox_13.setEnabled(not checked) #ppl
		self.checkBox_14.setEnabled(not checked) #xpl
	
	def on_control_checkbox_toggled2(self, checked):		
		self.checkBox.setEnabled(checked)
		self.checkBox_2.setEnabled(checked)
		self.checkBox_5.setEnabled(checked)
		self.checkBox_7.setEnabled(checked)
		self.checkBox_6.setEnabled(checked)
		self.checkBox_8.setEnabled(checked)
		self.checkBox_10.setEnabled(checked)
		self.checkBox_11.setEnabled(checked)
		self.checkBox_9.setEnabled(checked)
		self.checkBox_20.setEnabled(checked)
		self.checkBox_21.setEnabled(checked)
	
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
	
	#radio buttons
	def get_selected_option(self): #delete intermediate files
		if self.radioButton_4.isChecked():			
			self.option1 = 1
		elif self.radioButton_3.isChecked():			
			self.option1 = 0		
		else:			
			self.option1 = None	

	#endregion

	#region Right GUI functions	

	#Disabling Run button
	def update_button_state(self):		
		if self.listWidget.count() == 0:
			self.pushButton_8.setEnabled(False)
		else:
			self.pushButton_8.setEnabled(True)	

	def open_folder_dialog(self):

		default_folder = self.output_folder #last_path2

		# Open the folder selection dialog
		folder_path = QFileDialog.getExistingDirectory(
			self,   # Parent widget
			"Select Output Folder",  # Dialog title
			default_folder, # app working dir= QDir.currentPath()
			)			      

		if folder_path: # If selection was made
			self.output_folder = folder_path

	def browse_files(self):
		# 1. Determine starting directory: use self.output_folder if it exists, else empty string
		start_dir = getattr(self, 'output_folder', "")

		file_dialog = QFileDialog()
		file_paths, _ = file_dialog.getOpenFileNames(
			self, 
			"Select Files", 
			start_dir,  # 2. Pass the last path here
			"All Files (*);;Images (*.tif)"
		)

		if file_paths:
			temp_list = self.list_widget
			temp_list_new = []
			
			for path in file_paths:             
				if path not in temp_list:                                            
					temp_list_new.append(path)

			if temp_list_new:
				self.output_folder = os.path.dirname(temp_list_new[-1])
				
				temp_list.extend(temp_list_new)
				self.list_widget = temp_list
				self.listWidget.addItems(temp_list_new)

		self.update_button_state()

	#listWidget
	def move_item_up(self):
		# Get selected rows and sort them (0, 1, 2...)
		selected_rows = sorted([self.listWidget.row(item) for item in self.listWidget.selectedItems()])
		
		# If the first selected row is already at 0, we can't move up
		if not selected_rows or selected_rows[0] == 0:
			return

		for row in selected_rows:
			item = self.listWidget.takeItem(row)
			self.listWidget.insertItem(row - 1, item)
			item.setSelected(True) # Keep the item selected after move

	def move_item_down(self):
		# Get selected rows and sort them in REVERSE (...2, 1, 0)
		selected_rows = sorted([self.listWidget.row(item) for item in self.listWidget.selectedItems()], reverse=True)
		
		# If the last selected row is at the bottom, we can't move down
		if not selected_rows or selected_rows[0] == self.listWidget.count() - 1:
			return

		for row in selected_rows:
			item = self.listWidget.takeItem(row)
			self.listWidget.insertItem(row + 1, item)
			item.setSelected(True)		
	
	def remove_selected_item(self):
		selected_items = self.listWidget.selectedItems()
		if not selected_items:
			return

		for item in selected_items:
			text = item.text()
			if text in self.list_widget:
				self.list_widget.remove(text) # Remove from the tracking list

			# We take the item by row index
			row = self.listWidget.row(item)
			self.listWidget.takeItem(row)
			del item # Explicitly free memory
		
		self.update_button_state() 
	
	def remove_all_items(self):
		self.listWidget.clear()
		self.list_widget = []	

		self.update_button_state() 

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

	#endregion

	#region Main script 
	
	def runningFunction(self):        	
		print('Processing scans as image pyramid(s)..')
		
		#User input
		chosen_directory = self.lineEdit_3.text()		
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

		assigned_RAM = self.assigned_RAM   
		
		#splitting assigned cores
		n_cores_save = math.ceil(n_cores/2) #influenced by assigned_RAM
		n_cores_omeTiff = math.ceil(n_cores/2)
		n_cores_rt = n_cores 

		if sel_level == 0: #medicine
			n_cores_rt = math.ceil(n_cores/2)

		#Output convention
		condition1 = "originals" in items_output #all
		condition2 = "ppl" in items_output
		condition3 = "xpl" in items_output
		condition4 = "reflected" in items_output
		condition5 = "rayTracing" in items_output
		conditions = [condition1, condition2, condition3, condition4]

		if not any(conditions):
			print(r'Please, tick on at least one microscopy observation mode.')
			return
		
		modality_logical = [ any([item.find(str) != -1 for item in items_output]) for str in modality_list ] #ppl, xpl		

		#Force everything to False
		if not condition5:
			modality_logical = [False] * len(modality_logical)

		#feedback to users
		modality_not_logical = [not elem for elem in modality_logical]
		modality_subset = list(compress(modality_list, modality_logical))				
		unused_modalities = list(compress(modality_list, modality_not_logical))
		if unused_modalities:
			print(f"Ray tracing will not be done for: {unused_modalities} because it was not initially exported.")

		#Main script
		
		all_benchmarks = []

		for image_path in fileList:			

			loop_start = time.perf_counter()

			#Folder convention
			if chosen_directory == "":
				dirname1 = os.path.dirname(image_path) #last visited parent directory
			else:
				dirname1 = chosen_directory

			basename1 = os.path.basename(image_path).replace(".vsi", "")
			workingDir1 = os.path.join(dirname1, f"processed_level{sel_level:02d}_{basename1}")
			mkdir2(workingDir1) #remover= mkdir1, keeper= mkdir2          

			s1 = time.perf_counter()

			print(f'Extracting medatada..')
			read_metadata_function(image_path, dirname1, assigned_RAM)    
			t_metadata = time.perf_counter() - s1

			s2 = time.perf_counter()

			print(f'Re-formatting BioFormats pyramids as BigTIFF..')
			tile_table = save_tiles_function(image_path, conditions, sel_level, tileSize, 
									n_cores_save, assigned_RAM, dirname1)          
			t_tiles = time.perf_counter() - s2

			t_stitch = 0
			if any(conditions):  	
				s3 = time.perf_counter()

				print(f'Saving original montages as OME-TIFF..')     
				join_original_tiles_function(tile_table, n_cores_omeTiff) #n_cores  
				t_stitch = time.perf_counter() - s3 

			t_raytrace = 0			
			t_raytrace_stitch = 0
			
			
			if any(modality_logical): 
				#already validated with available scans and ray tracing check box

				s4 = time.perf_counter()

				print(f'Calculating ray tracing..')	
				rt_montage_paths = ray_tracing_function(tile_table, modality_subset, statistic_list, percentOut, 
											n_cores_rt, workingDir1)    								
				t_raytrace = time.perf_counter() - s4				
				
				s5 = time.perf_counter()	

				print(f'Saving ray tracing montages as OME-TIFF..')     
				join_rt_tiles_function(rt_montage_paths, n_cores_omeTiff)
				t_raytrace_stitch = time.perf_counter() - s5					

			
			t_cleanup = 0
			if delete_intermediate == 1:	
				s6 = time.perf_counter()	

				print(f'Deleting intermediate files..')
				delete_intermediate_files(workingDir1)
				t_cleanup = time.perf_counter() - s6

			total_img_time = time.perf_counter() - loop_start
			
			file_stats = {
				'filename': basename1,
				'metadata_sec': t_metadata,
				'tile_export_sec': t_tiles,
				'stitching_sec': t_stitch,
				'raytrace_sec': t_raytrace,				
				'raytrace_stitch_sec': t_raytrace_stitch,				
				'cleanup_sec': t_cleanup,
				'total_sec': total_img_time,
				}	
			
			all_benchmarks.append(file_stats)
			print(f'Ready: {basename1} ({total_img_time:.2f}s)')
		
		if all_benchmarks:
			master_df = pd.DataFrame(all_benchmarks)
			master_df.to_csv(os.path.join(workingDir1, 'time_benchmark.csv'), index=False)

		print('Finished.')

	def runningFunction2(self):  		
		
		#User input
		output_folder = self.output_folder
		filename_output0 = self.lineEdit_2.text()
		fileList2 = qListWidget_list(self.listWidget)		
		format_list = self.items_format
		type_list = self.items_type
		tileSize = int(self.comboBox_2.currentText())		
		pixel_size_sel = self.doubleSpinBox_2.value() #float				
		
		#Main script	
		print('Generating multi-modal image..')		

		#Defaults
		if filename_output0 == '':
			filename_output = 'default_name' #default
		else:
			filename_output = filename_output0 
						
		file_output = filename_output + ".tif" 
		output_path = os.path.join(output_folder, file_output)  
		print(f'The output folder was \n {output_folder}')		

		#Output convention
		output_ome = "ometiff" in format_list
		output_dz = "dz" in format_list
		output_flat = "flat" in format_list
		output_zstack = "zstack" in type_list
		output_individuals = "individuals" in type_list
		condition1 = output_ome == 1 & output_zstack == 1
		condition2 = output_ome == 1 & output_individuals == 1
		condition3 = output_dz 		
		condition4 = output_flat

		if condition1:
			print('Generating z-stack..')
			generate_zStack(fileList2, pixel_size_sel, tileSize, output_path)		

		if condition2:
			print('Generating individual pyramid(s)..')
			generate_individualImages(fileList2, pixel_size_sel, tileSize, output_path)
		
		if condition3:
			print('Generating Deep Zoom pyramid(s)..')
			generate_dz(fileList2, tileSize, output_path)
		
		if condition4:
			print('Generating flat images(s)..')
			generate_flatImages(fileList2, output_path)

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
	import time
	import traceback
	import pandas as pd	
	from itertools import compress	
	import math
	import javabridge 

	#relative to script path	
	from helperFunctions.mkdir_options import mkdir2
	from main_functions import delete_intermediate_files, parse_system_info, qListWidget_list
	from main_functions import read_metadata_function, save_tiles_function, ray_tracing_function, join_original_tiles_function, join_rt_tiles_function
	from main_functions import generate_zStack, generate_individualImages, generate_dz, generate_flatImages
	
	#GUI
	from PyQt5.QtWidgets import QApplication, QFileDialog, QAbstractItemView
	from PyQt5.QtCore import Qt, QSize
	from PyQt5.QtGui import QPixmap, QIcon

	sys.excepthook = custom_exception_handler

	#App resolution
	QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) 
	QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True) #icons
	
	if os.name == 'nt': #blurry on HDMI screens (Windows-only)
		import ctypes
		ctypes.windll.shcore.SetProcessDpiAwareness(1)

	#Run
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit(app.exec_())

	#endregion

