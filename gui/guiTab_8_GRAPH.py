

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
        # Create Listbox with multi-select support and scrollbar
        listbox_frame = tk.Frame(self.fr_analysis)
        listbox_frame.grid(row=0, column=0, padx=self.theme_config["pad"]["xpad_m"], pady=self.theme_config["pad"]["ypad_m"])

        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        self.file_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.EXTENDED,  # Enable multi-select
            width=50,
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind selection event
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        # Selection info label
        self.file_selection_label = tk.Label(self.fr_analysis, text="0 files selected", relief='sunken')
        self.file_selection_label.grid(row=1, column=0, padx=10, pady=5, sticky='ew')

        # analyze button
        open_button = tk.Button(self.fr_analysis,
                                text="Analyze Selected Files",
                                command=self.analyze_files,
                                bg=self.theme_config["dark_2"], fg="white",
                                height=self.theme_config["size"]["h_button"],
                                width=self.theme_config["size"]["w_button"])
        open_button.grid(row=3, column=1, padx=10, pady=10)

        # plot button
        graph_button = tk.Button(self.fr_analysis,
                                 text="Graph Selected Files",
                                 command=self.graph_files,
                                 bg=self.theme_config["dark_3"], fg="white",
                                 height=self.theme_config["size"]["h_button"],
                                 width=self.theme_config["size"]["w_button"])
        graph_button.grid(row=4, column=1, padx=10, pady=10)

    def gui_refresh(self, event):
        pass

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def set_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    def on_file_select(self, event):
        """Update the selection label when files are selected"""
        selected_indices = self.file_listbox.curselection()
        num_selected = len(selected_indices)

        if num_selected == 0:
            self.file_selection_label.config(text="0 files selected")
        elif num_selected == 1:
            self.file_selection_label.config(text="1 file selected")
        else:
            self.file_selection_label.config(text=f"{num_selected} files selected")

    def get_selected_files(self):
        """Get list of selected file data tuples"""
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return []

        selected_files = []
        for idx in selected_indices:
            if idx < len(self.files):
                selected_files.append(self.files[idx])

        return selected_files

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

        self.prompt.print(f"Loaded {len(self.files)} files")

    def graph_files(self):
        # Get selected files
        selected_files = self.get_selected_files()

        if not selected_files:
            guih.alert_user("No Files Selected", "Please select one or more files to graph", "warning")
            return False

        self.prompt.print(f"Graphing {len(selected_files)} selected file(s)...")

        # set up plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlabel(self.x_label.get("1.0", "end").strip("\n"))
        ax.set_ylabel(self.y_label.get("1.0", "end").strip("\n"))
        ax.set_title(self.title.get("1.0", "end").strip("\n"))
        ax.grid(True)
        plt.tight_layout()

        # iterate across selected files only
        for filename, filepath, file_parts, df in selected_files:
            # setup X and Y data
            x_key = self.x_var.get("1.0", "end").strip("\n")
            y_key = self.y_var.get("1.0", "end").strip("\n")
            try:
                x_data = df[x_key]
                y_data = df[y_key]
            except KeyError as e:
                guih.alert_user("Key error in data file", f"Key {e} is not found in {filename}", "error")
                self.prompt.print(f"Error: Column '{e}' not found in {filename}", "error")
                continue
            try:
                x_scale = int(self.x_scale.get())
                y_scale = int(self.y_scale.get())
            except ValueError as e:
                guih.alert_user("Scale factor not integer", str(e), "error")
                return False

            # set up labeling
            if self.var_use_file_labeler.get():
                try:
                    file_label_idx = int(self.file_labeler.get("1.0", "end").strip("\n"))
                    label = file_parts[file_label_idx]
                except (ValueError, IndexError):
                    label = filename
            else:
                label = filename

            # plot on axis
            ax.plot(
                 x_data * x_scale,
                 y_data * y_scale,
                label=label,
                marker='o',
                markersize=3
            )

            self.prompt.print(f"Plotted {filename}")

        # show plot
        ax.legend()
        plt.show()
        self.prompt.print("Graph complete!")
        return True

    def analyze_files(self):
        # Get selected files
        selected_files = self.get_selected_files()

        if not selected_files:
            guih.alert_user("No Files Selected", "Please select one or more files to analyze", "warning")
            return False

        self.prompt.print(f"Analyzing {len(selected_files)} selected file(s)...")

        # Analyze each selected file
        for filename, filepath, file_parts, df in selected_files:
            self.prompt.print(f"\n=== Analysis of {filename} ===")

            # Basic statistics
            self.prompt.print(f"Rows: {len(df)}")
            self.prompt.print(f"Columns: {', '.join(df.columns.tolist())}")

            # Show statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_cols) > 0:
                self.prompt.print("\nStatistics:")
                for col in numeric_cols:
                    mean_val = df[col].mean()
                    std_val = df[col].std()
                    min_val = df[col].min()
                    max_val = df[col].max()
                    self.prompt.print(f"  {col}: mean={mean_val:.4f}, std={std_val:.4f}, min={min_val:.4f}, max={max_val:.4f}")

        self.prompt.print("\nAnalysis complete!")
        return True





