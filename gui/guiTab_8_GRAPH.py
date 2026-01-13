
# import needed packages
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os

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

# TODO: is there an option to tab to the next Entry box ... probably not ....



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

        # Widgets
        self.title.grid(row=2, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.x_label.grid(row=3, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.y_label.grid(row=4, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.x_scale.grid(row=5, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.y_scale.grid(row=6, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.x_var.grid(row=7, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.y_var.grid(row=8, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # add check boxes for the various options
        self.var_use_file_regex = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use Filename Filter",
                        variable=self.var_use_file_regex,
                        onvalue=1,
                        offvalue=0).grid(row=9, column=0, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])
        self.file_filter = tk.Text(self.fr_setup, height=1, width=20)
        self.file_filter.grid(row=9, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button SHOW_FILES
        btn_start_entry = tk.Button(self.fr_setup, text="Refresh Files",
                                 command=lambda: self.refresh_files(),
                                 bg=self.theme_config["success"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=10, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])


        # set up button START GRAPH
        btn_start_entry = tk.Button(self.fr_setup, text="Load fields (not working)",
                                 command=None,
                                 bg=self.theme_config["dark_3"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=10, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

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
                                 command=lambda: self.graph_files(self.file_filter.get("1.0", "end"))
                                 )
        graph_button.grid(row=4, column=1, padx=10, pady=10)

    def gui_refresh(self, event):
        if event == "auto":
            if self.cc.get_ser_status():
                self.ser_status.set_color(self.theme_config["success"])
            else:
                self.ser_status.set_color(self.theme_config["error"])
            if self.cc.get_dmm_status():
                self.dmm_status.set_color(self.theme_config["success"])
            else:
                self.dmm_status.set_color(self.theme_config["error"])
            if self.cc.get_ps_status():
                self.ps_status.set_color(self.theme_config["success"])
            else:
                self.ps_status.set_color(self.theme_config["error"])


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def set_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    def refresh_files(self):
        files = [] # list of (filepath, vars_dict)
        vars_dict = {}

        # TODO: make this group_schema an option in the GUI interface
        group_schema = {
            1: ("var1", str),  # e.g., board number as string
            2: ("var2", float),  # e.g., temperature as float
        }

        def grab_files():
            for filename in os.listdir(self.data_dir):
                if not filename.endswith(".csv"):
                    continue
                if self.var_use_file_regex.get():
                    pass
                    # TODO: add some pattern matching here
                    # m = pattern.match(filename)
                    # if not m:
                    #     continue

                # Build a vars dict from the regex match dynamically
                # for idx, (name, caster) in group_schema.items():
                #     if self.var_use_file_regex.get():
                #         try:
                #             vars_dict[name] = caster(m.group(idx))
                #         except (IndexError, ValueError) as ex:
                #             # If a group is missing or cast fails, skip this file
                #             # (You can log/print ex if desired)
                #             vars_dict = None
                #             break
                #     else:
                #         vars_dict = None

                filepath = os.path.join(self.data_dir, filename)
                df = pd.read_csv(filepath)
                files.append((filename, filepath, vars_dict, df))
            return files

        # update file list
        self.files = grab_files()

        self.file_listbox.delete(0, tk.END)
        for file in self.files:
            self.file_listbox.insert(tk.END, file[0])

    def graph_files(self, filter_value):
        # TODO: make this a user input
        filter_by = "var1"
        label_var = "PWM"
        legend_added = set()
        label_values = []

        for _, _, _, df in self.files:
            if label_var not in df.columns:
                raise KeyError(f"Column '{label_var}' not found in one of the CSV files.")
                # TODO: user error handling here
            label_values.extend(df[label_var].dropna().unique())

        # Unique + sorted (for consistent coloring)
        unique_labels = sorted(set(label_values))

        # TODO: evaluate this color normalization more
        try:
            # Attempt numeric normalization (e.g., PWM values like 0, 25, 50, 75, 100)
            lbl_arr = np.array(unique_labels, dtype=float)
            vmin, vmax = lbl_arr.min(), lbl_arr.max()
            norm_lbl = mcolors.Normalize(vmin=vmin, vmax=vmax)
            cmap_lbl = plt.get_cmap('tab10')  # or 'viridis', 'plasma' etc.
            color_for_label = {val: cmap_lbl(norm_lbl(float(val))) for val in unique_labels}
        except Exception:
            # Fallback: categorical colors (e.g., strings)
            cmap_lbl = plt.get_cmap('tab10')
            color_for_label = {val: cmap_lbl(i % 10) for i, val in enumerate(unique_labels)}

        # set up plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlabel(self.x_label.get("1.0", "end"))
        ax.set_ylabel(self.y_label.get("1.0", "end"))
        ax.set_title(self.title.get("1.0", "end"))
        ax.grid(True)
        plt.tight_layout()

        for _, filepath, vars_dict, df in self.files:
            if self.var_use_file_regex.get():
                if filter_value is not None:
                    if vars_dict[filter_by] != filter_value:
                        continue

            for label_val in sorted(df[label_var].dropna().unique()):
                df_pwm = df[df[label_var] == label_val]

                color = color_for_label[label_val]

                # Only add one legend entry per PWM value
                label = f"{label_var}={label_val}" if label_val not in legend_added else None
                if label is not None:
                    legend_added.add(label_val)

                try:
                    x_data = df_pwm[self.x_var.get("1.0", "end").strip("\n")]
                    y_data = df_pwm[self.y_var.get("1.0", "end").strip("\n")]
                except KeyError as e:
                    guih.alert_user("Key error in data file", e, "error")
                    return False
                try:
                    x_scale = int(self.x_scale.get())
                    y_scale = int(self.y_scale.get())
                except ValueError as e:
                    guih.alert_user("Scale factor not integer", e, "error")
                    return False

                ax.plot(
                     x_data * x_scale,
                     y_data * y_scale,
                    label=label,
                    color=color
                )

        # show plot
        ax.legend()
        plt.show()
        return True

    def analyze_files(self):
        print("Analyzing file")
        file_path = self.basefilepath + self.data_folder + filename

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





