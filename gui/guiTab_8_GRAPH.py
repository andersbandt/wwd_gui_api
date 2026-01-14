

# import needed packages
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os
from pathlib import Path
import re

# import needed GUI packages
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

# import user defined modules
from analysis.csv_helper import CSVHelper

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic


# TODO: have saveable setup configs

# TODO: add option to only select certain files from the Listbox in analysis


def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return("break")



class TabGraph(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath

        self.grid(row=0, column=0)

        # set up file information
        self.data_dir = basefilepath + "/data/"
        self.files = []

        self.fr_setup = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_analysis = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up prompt
        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                   "Data Logger Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_setup.grid(row=1, column=0, pady=15, padx=15)
        self.fr_analysis.grid(row=1, column=1, pady=15, padx=15)
        self.prompt.grid(row=2, column=0, columnspan=4, padx=30, pady=12)

    def initTabContent(self):
        print("Initializing tab 8 (Graph) content")

        # print welcome text_data
        l1 = ttk.Label(self, text="Grapher", style="BW.TLabel",
                       font=(self.theme_config["font"]["family"], 16))
        l1.grid(column=0, row=0, columnspan=4)

        self.init_fr_setup()
        self.init_fr_analysis()

    def init_fr_setup(self):
        # add directory search
        self.lbl_data_directory = tk.Label(self.fr_setup, text=self.data_dir, bg=self.theme_config["bg_light"])
        self.lbl_data_directory.grid(row=1, column=0)
        btn_set_directory = tk.Button(self.fr_setup, text="Set directory",
                                 command=lambda: self.set_directory(),
                                 bg=self.theme_config["light_1"], fg="black", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_set_directory.grid(row=1, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # graph labeling
        tk.Label(self.fr_setup, text="Title").grid(row=2, column=1, padx=5, pady=2)
        tk.Label(self.fr_setup, text="X-axis").grid(row=3, column=1, padx=5, pady=2)
        tk.Label(self.fr_setup, text="Y-axis").grid(row=4, column=1, padx=5, pady=2)
        tk.Label(self.fr_setup, text="X-scale").grid(row=5, column=1, padx=5, pady=2)
        tk.Label(self.fr_setup, text="Y-scale").grid(row=6, column=1, padx=5, pady=2)
        tk.Label(self.fr_setup, text="X-variable").grid(row=7, column=1, padx=5, pady=2)
        tk.Label(self.fr_setup, text="Y-variable").grid(row=8, column=1, padx=5, pady=2)

        self.title = tk.Text(self.fr_setup, height=1, width=20)
        self.x_label = tk.Text(self.fr_setup, height=1, width=20)
        self.y_label = tk.Text(self.fr_setup, height=1, width=20)
        self.x_scale = tk.Spinbox(self.fr_setup, from_=1, to=10e9)
        self.y_scale = tk.Spinbox(self.fr_setup, from_=1, to=10e9)
        self.x_var = tk.Text(self.fr_setup, height=1, width=20)
        self.y_var = tk.Text(self.fr_setup, height=1, width=20)

        self.title.bind("<Tab>", focus_next_widget)
        self.x_label.bind("<Tab>", focus_next_widget)
        self.y_label.bind("<Tab>", focus_next_widget)
        self.x_scale.bind("<Tab>", focus_next_widget)
        self.y_scale.bind("<Tab>", focus_next_widget)
        self.x_var.bind("<Tab>", focus_next_widget)
        self.y_var.bind("<Tab>", focus_next_widget)

        # Widgets
        self.title.grid(row=2, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.x_label.grid(row=3, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.y_label.grid(row=4, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.x_scale.grid(row=5, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.y_scale.grid(row=6, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.x_var.grid(row=7, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.y_var.grid(row=8, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # add check box and text field to filter files by string
        self.var_use_file_regex = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use Filename Filter",
                        variable=self.var_use_file_regex,
                        onvalue=1,
                        offvalue=0).grid(row=9, column=0, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.file_filter = tk.Text(self.fr_setup, height=1, width=20)
        self.file_filter.grid(row=9, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # add check box and text field to label graphs by string in filename
        self.var_use_file_labeler = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use Filename Labeler",
                        variable=self.var_use_file_labeler,
                        onvalue=1,
                        offvalue=0).grid(row=10, column=0, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.file_labeler = tk.Text(self.fr_setup, height=1, width=20)
        self.file_labeler.grid(row=10, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button SHOW_FILES
        btn_start_entry = tk.Button(self.fr_setup, text="Refresh Files",
                                 command=lambda: self.refresh_files(),
                                 bg=self.theme_config["success"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=11, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])


        # set up button START GRAPH
        btn_start_entry = tk.Button(self.fr_setup, text="Load fields (not working)",
                                 command=None,
                                 bg=self.theme_config["dark_3"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=11, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

    def init_fr_analysis(self):
        self.file_listbox = tk.Listbox(self.fr_analysis, width=50, height=15)
        self.file_listbox.grid(row=0, column=0, padx=self.theme_config["pad"]["xpad_m"], pady=self.theme_config["pad"]["ypad_m"])

        # analyze button
        open_button = tk.Button(self.fr_analysis,
                                text="Analyze file data",
                                command=self.analyze_files
                                )
        open_button.grid(row=3, column=1, padx=10, pady=10)

        # plot button
        graph_button = tk.Button(self.fr_analysis,
                                 text="Graph files",
                                 command=self.graph_files
                                 )
        graph_button.grid(row=4, column=1, padx=10, pady=10)

    def gui_refresh(self, event):
        pass

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def set_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    def refresh_files(self):
        files = [] # list of (filepath, vars_dict)

        def grab_files():
            for filename in os.listdir(self.data_dir):
                # check if CSV file
                if not filename.endswith(".csv"):
                    continue

                # filename filtering
                if self.var_use_file_regex.get():
                    sr_str = "_" + self.file_filter.get("1.0", "end").strip("\n") + "_"
                    if sr_str not in filename:
                        continue

                # extract vars_dict from filename (may contain things like board number, temperature, etc)
                stem = Path(filename).stem
                parts = stem.split('_')

                # extract Pandas df
                filepath = os.path.join(self.data_dir, filename)
                df = pd.read_csv(filepath)

                # append to running list of files
                files.append((
                    filename,
                    filepath,
                    parts,
                    df))
            return files

        # update file list
        self.files = grab_files()

        self.file_listbox.delete(0, tk.END)
        for file in self.files:
            self.file_listbox.insert(tk.END, file[0])

    def graph_files(self):
        # set up plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlabel(self.x_label.get("1.0", "end"))
        ax.set_ylabel(self.y_label.get("1.0", "end"))
        ax.set_title(self.title.get("1.0", "end"))
        ax.grid(True)
        plt.tight_layout()

        # iterate across all files
        for filename, filepath, file_parts, df in self.files:
            # setup X and Y data
            x_key = self.x_var.get("1.0", "end").strip("\n")
            y_key = self.y_var.get("1.0", "end").strip("\n")
            try:
                x_data = df[x_key]
                y_data = df[y_key]
            except KeyError as e:
                guih.alert_user("Key error in data file", f"Key {e} is not found", "error")
                return False
            try:
                x_scale = int(self.x_scale.get())
                y_scale = int(self.y_scale.get())
            except ValueError as e:
                guih.alert_user("Scale factor not integer", e, "error")
                return False

            # set up labeling
            if self.var_use_file_labeler.get():
                file_label_idx = int(self.file_labeler.get("1.0", "end"))
                label = file_parts[file_label_idx]
            else:
                label = filename

            # plot on axis
            ax.plot(
                 x_data * x_scale,
                 y_data * y_scale,
                label=label,
                # color=color
            )

        # show plot
        ax.legend()
        plt.show()
        return True

    def analyze_files(self):
        print("Analyzing file")
        file_path = self.basefilepath + self.data_dir + filename

        # imu_data = processor.load_csv(file_path)
        # if imu_data is None:
        #     gui_helper.alert_user("Something wrong with data!",
        #                           "Couldn't load data, something wrong",
        #                           kind="error")
        #     return False

        imu_stats = imu_analysis.analyze_imu(file_path)
        # output_frame = tk.Frame(self.master)
        # output_frame.grid(row=4, column=0)
        text_box = tk.Text(self.fr_analysis, height=17)
        text_box.grid(row=5, column=0, padx=15, pady=15)

        # Add the dictionary contents to the Text widget
        for key, value in imu_stats.items():
            text_box.insert(tk.END, f"{key}: {value}\n")
        return True





