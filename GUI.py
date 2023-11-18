import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry
import os

# Import our custom class that handles and creates the graph from the data for us
from graph import HydroGraph

def create_gui():
    graph_backend = HydroGraph()

    # Create the main window
    root = tk.Tk()
    root.title("River Flow Predictions")
    root.iconbitmap("data/eef-g.ico")

    # Create a Figure and a Canvas to draw the graph
    fig = graph_backend.GetPlot()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    
    # Add a textbox
    def validate_input(input):
        return input.isdigit() and len(input) <= 8 or input == ""
    
    validate_command = root.register(validate_input)
    textbox = tk.Entry(root, validate="key", validatecommand=(validate_command, "%P"))
    textbox.pack()

    # Add a date selector
    date_selector = DateEntry(root)
    date_selector.pack()

    def collect_info():
        selcted_date = date_selector.get_date().strftime("%Y-%m-%d")
        # selected_date = selected_date.strftime("%Y-%m-%d")
        selected_sensor = textbox.get()
        graph_backend.SetFullInfo(selcted_date, selected_sensor)
        while not graph_backend.graph_finished:
            pass
        new_fig = graph_backend.GetPlot()

        global fig
        fig = new_fig

        canvas.figure = fig
        canvas.draw()

    def clear_cache():
        cache_folder = "data"
        parquet_subfolder = f"{cache_folder}/parquets"

        for file in os.listdir(parquet_subfolder):
            file_path = os.path.join(parquet_subfolder, file)
            os.remove(file_path)
           
    # Add a button
    button = ttk.Button(root, text="Get Data", command=collect_info)
    button.pack()

    # Add a second button that clears the cached data
    cache_button = ttk.Button(root, text="Clear Cache", command=clear_cache)
    cache_button.pack()

    # Start the main loop
    tk.mainloop()