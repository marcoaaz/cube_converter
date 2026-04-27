import tkinter as tk

def button_click():
    label.config(text="Button clicked!")

# Create the main window
root = tk.Tk()
root.title("My First GUI")

# Create a label
label = tk.Label(root, text="Hello, GUI!")
label.pack(pady=10)

# Create a button
button = tk.Button(root, text="Click Me", command=button_click)
button.pack(pady=5)

# Start the GUI event loop
root.mainloop()