"""Graphing tab for plotting saved CSV data."""

# import needed packages
import pandas as pd
import os
import json
from pathlib import Path
from collections import namedtuple
import numpy as np

# import needed GUI packages
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

# import user defined modules
from common import path_helper
from common import plotter
from analysis import data_helper
from analysis import stats_analysis

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic



# Define named tuple for file data
FileData = namedtuple('FileData', ['filename', 'filepath', 'parts', 'df'])


def focus_next_widget(event):
    event.widget.tk_focusNext().focus()
    return "break"



class GraphOptionsDialog(tk.Toplevel):
    """Modal popup for configuring matplotlib graph appearance options."""

    LEGEND_LOCS = [
        "best", "upper right", "upper left", "lower right", "lower left",
        "center left", "center right", "lower center", "upper center", "center",
    ]

    def __init__(self, parent, current_config, on_apply):
        super().__init__(parent)
        self.title("Graph Appearance Options")
        self.resizable(False, False)
        self.on_apply = on_apply

        cfg = current_config
        self.var_figsize_w    = tk.DoubleVar(value=cfg.get("figsize_w", 10))
        self.var_figsize_h    = tk.DoubleVar(value=cfg.get("figsize_h", 6))
        self.var_show_grid    = tk.BooleanVar(value=cfg.get("show_grid", True))
        self.var_grid_alpha   = tk.DoubleVar(value=cfg.get("grid_alpha", 0.3))
        self.var_xtick_rot    = tk.IntVar(value=cfg.get("xtick_rotation", 0))
        self.var_ytick_rot    = tk.IntVar(value=cfg.get("ytick_rotation", 0))
        self.var_xtick_max    = tk.IntVar(value=cfg.get("xtick_max", 0))
        self.var_show_legend  = tk.BooleanVar(value=cfg.get("show_legend", True))
        self.var_legend_loc   = tk.StringVar(value=cfg.get("legend_loc", "best"))
        self.var_linewidth    = tk.DoubleVar(value=cfg.get("linewidth", 1.5))
        self.var_alpha        = tk.DoubleVar(value=cfg.get("alpha", 1.0))
        self.var_markersize   = tk.IntVar(value=cfg.get("markersize", 3))

        self._build_ui()
        self.grab_set()
        self.transient(parent)

    def _build_ui(self):
        p = {"padx": 8, "pady": 3}
        row = 0

        def section(label):
            nonlocal row
            tk.Label(self, text=label, font=("TkDefaultFont", 9, "bold")).grid(
                row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(10, 2))
            row += 1

        def field(label, widget_fn):
            nonlocal row
            tk.Label(self, text=label).grid(row=row, column=0, sticky="e", **p)
            widget_fn(row)
            row += 1

        def sep():
            nonlocal row
            ttk.Separator(self, orient="horizontal").grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=4)
            row += 1

        # ── Figure Size ──────────────────────────────────────────────
        section("Figure Size")
        field("Width (in)",  lambda r: tk.Spinbox(self, from_=4,  to=30,  increment=1,   textvariable=self.var_figsize_w,  width=7).grid(row=r, column=1, sticky="w", **p))
        field("Height (in)", lambda r: tk.Spinbox(self, from_=2,  to=20,  increment=1,   textvariable=self.var_figsize_h,  width=7).grid(row=r, column=1, sticky="w", **p))
        sep()

        # ── Grid ─────────────────────────────────────────────────────
        section("Grid")
        ttk.Checkbutton(self, text="Show grid", variable=self.var_show_grid).grid(
            row=row, column=0, columnspan=2, sticky="w", **p); row += 1
        field("Grid alpha",  lambda r: tk.Spinbox(self, from_=0.0, to=1.0, increment=0.1, format="%.1f", textvariable=self.var_grid_alpha, width=7).grid(row=r, column=1, sticky="w", **p))
        sep()

        # ── Tick Rotation ────────────────────────────────────────────
        section("Tick Rotation")
        field("X-tick (°)", lambda r: tk.Spinbox(self, from_=0, to=90, increment=15, textvariable=self.var_xtick_rot, width=7).grid(row=r, column=1, sticky="w", **p))
        field("Y-tick (°)", lambda r: tk.Spinbox(self, from_=0, to=90, increment=15, textvariable=self.var_ytick_rot, width=7).grid(row=r, column=1, sticky="w", **p))
        field("Max X-ticks (0=auto)", lambda r: tk.Spinbox(self, from_=0, to=50, increment=5, textvariable=self.var_xtick_max, width=7).grid(row=r, column=1, sticky="w", **p))
        sep()

        # ── Legend ───────────────────────────────────────────────────
        section("Legend")
        ttk.Checkbutton(self, text="Show legend", variable=self.var_show_legend).grid(
            row=row, column=0, columnspan=2, sticky="w", **p); row += 1
        field("Location", lambda r: ttk.Combobox(self, textvariable=self.var_legend_loc,
            values=self.LEGEND_LOCS, state="readonly", width=14).grid(row=r, column=1, sticky="w", **p))
        sep()

        # ── Line Appearance ──────────────────────────────────────────
        section("Line Appearance")
        field("Line width",  lambda r: tk.Spinbox(self, from_=0.5, to=8.0, increment=0.5, format="%.1f", textvariable=self.var_linewidth,  width=7).grid(row=r, column=1, sticky="w", **p))
        field("Alpha",       lambda r: tk.Spinbox(self, from_=0.1, to=1.0, increment=0.1, format="%.1f", textvariable=self.var_alpha,       width=7).grid(row=r, column=1, sticky="w", **p))
        field("Marker size", lambda r: tk.Spinbox(self, from_=1,   to=20,  increment=1,                  textvariable=self.var_markersize,  width=7).grid(row=r, column=1, sticky="w", **p))
        sep()

        # ── Buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=8)
        tk.Button(btn_frame, text="OK",     width=10, command=self._ok).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=4)

    def _ok(self):
        self.on_apply({
            "figsize_w":     self.var_figsize_w.get(),
            "figsize_h":     self.var_figsize_h.get(),
            "show_grid":     self.var_show_grid.get(),
            "grid_alpha":    self.var_grid_alpha.get(),
            "xtick_rotation": self.var_xtick_rot.get(),
            "ytick_rotation": self.var_ytick_rot.get(),
            "xtick_max":      self.var_xtick_max.get(),
            "show_legend":   self.var_show_legend.get(),
            "legend_loc":    self.var_legend_loc.get(),
            "linewidth":     self.var_linewidth.get(),
            "alpha":         self.var_alpha.get(),
            "markersize":    self.var_markersize.get(),
        })
        self.destroy()


class TabGraph(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath

        self.grid(row=0, column=0)

        # set up file information
        self.data_dir = path_helper.get_full_data_path()
        self.files = []

        # default appearance options (user can change via the options dialog)
        self.appearance_config = {
            "figsize_w":      10,
            "figsize_h":      6,
            "show_grid":      True,
            "grid_alpha":     0.3,
            "xtick_rotation": 0,
            "ytick_rotation": 0,
            "show_legend":    True,
            "legend_loc":     "best",
            "linewidth":      1.5,
            "alpha":          1.0,
            "markersize":     3,
            "xtick_max":      0,
        }

        # set up preset configuration
        self.preset_dir = os.path.join(self.basefilepath, "config", "graph_presets")
        os.makedirs(self.preset_dir, exist_ok=True)

        self.fr_setup = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_files = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "Data Logger Output")

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_setup.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_files.grid(row=1, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])

        compact = self.theme_config.get("compact", False)
        if compact:
            # compact: prompt beside fr_files in the same row
            self.prompt.grid(row=1, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")
            self.columnconfigure(2, weight=1)
            self.rowconfigure(1, weight=1)
        else:
            # normal: prompt gets its own full-width row at the bottom
            self.prompt.grid(row=2, column=0, columnspan=4, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")
            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=1)
            self.rowconfigure(2, weight=1)

        # refresh initial file last
        self.refresh_files()

        # refresh presets dropdown
        self.refresh_presets()

    def initTabContent(self):
        print("Initializing tab 9 (Graph) content")

        # print welcome text_data
        l1 = ttk.Label(self, text="Grapher", style="BW.TLabel",
                       font=(self.theme_config["font"]["family"], 16))
        l1.grid(column=0, row=0, columnspan=4)

        self.init_fr_setup()
        self.init_fr_files()

    def init_fr_setup(self):
        xpad = self.theme_config["pad"]["xpad_s"]
        ypad = self.theme_config["pad"]["ypad_s"]

        # allow column 1 to stretch so title/text fields expand
        self.fr_setup.columnconfigure(1, weight=1)

        row = 0

        # ── Preset controls ──────────────────────────────
        tk.Label(self.fr_setup, text="Preset:").grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.preset_combo = ttk.Combobox(self.fr_setup, width=18, state='readonly')
        self.preset_combo.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_select)
        row += 1

        btn_save_preset = tk.Button(self.fr_setup, text="Save",
                                    command=self.save_preset,
                                    bg=self.theme_config["success"],
                                    fg=self.theme_config["fg_dark"],
                                    height=1, width=8)
        btn_save_preset.grid(row=row, column=0, padx=xpad, pady=ypad)

        btn_load_preset = tk.Button(self.fr_setup, text="Load",
                                    command=self.load_preset,
                                    bg=self.theme_config["light_2"],
                                    fg=self.theme_config["fg_dark"],
                                    height=1, width=8)
        btn_load_preset.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='w')

        btn_clear_all = tk.Button(self.fr_setup, text="Clear All",
                                  command=self.clear_all_fields,
                                  bg=self.theme_config["warning"],
                                  fg=self.theme_config["fg_dark"],
                                  height=1, width=8)
        btn_clear_all.grid(row=row, column=2, padx=xpad, pady=ypad, sticky='w')
        row += 1

        # ── Graph Appearance ──────────────────────────────
        sep1 = ttk.Separator(self.fr_setup, orient='horizontal')
        sep1.grid(row=row, column=0, columnspan=3, sticky='ew', pady=(8, 2))
        row += 1

        lbl_section1 = tk.Label(self.fr_setup, text="Graph Appearance",
                                font=(self.theme_config["font"]["family"], 9, "bold"),
                                bg=self.theme_config["light_4"])
        lbl_section1.grid(row=row, column=0, columnspan=2, sticky='w', padx=5)
        row += 1

        lbl_title = tk.Label(self.fr_setup, text="Title")
        lbl_title.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        lbl_x_axis = tk.Label(self.fr_setup, text="X-axis")
        lbl_y_axis = tk.Label(self.fr_setup, text="Y-axis")
        lbl_plot_style = tk.Label(self.fr_setup, text="Plot style")

        self.title = tk.Text(self.fr_setup, height=1, width=20)
        self.x_label = tk.Text(self.fr_setup, height=1, width=20)
        self.y_label = tk.Text(self.fr_setup, height=1, width=20)
        self.plot_style_drop = guih.generate_drop_down(self.fr_setup, ["Line", "Scatter", "Line + Scatter"])

        self.title.bind("<Tab>", focus_next_widget)
        self.x_label.bind("<Tab>", focus_next_widget)
        self.y_label.bind("<Tab>", focus_next_widget)

        # title gets sticky='ew' so it expands with the frame
        self.title.grid(row=row, column=1, columnspan=2, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        lbl_x_axis.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.x_label.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        lbl_y_axis.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.y_label.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        lbl_plot_style.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.plot_style_drop[0].grid(row=row, column=1, padx=xpad, pady=ypad)
        self.plot_style_drop[1].set("Line + Scatter")
        row += 1

        # labeling options
        self.var_use_file_labeler = tk.IntVar()
        cb_file_label = ttk.Checkbutton(self.fr_setup,
                                        text="Use Filename Labeler",
                                        variable=self.var_use_file_labeler,
                                        onvalue=1, offvalue=0)
        cb_file_label.grid(row=row, column=0, padx=xpad, pady=ypad)
        # NOTE: Currently uses full filename stem when checkbox is enabled.
        #       This text field is reserved for future enhancement to specify which parts
        #       of the filename to use (e.g., index, range, or slice notation).
        self.file_labeler = tk.Text(self.fr_setup, height=1, width=20)
        self.file_labeler.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        self.var_use_data_labeler = tk.IntVar()
        cb_data_label = ttk.Checkbutton(self.fr_setup,
                                        text="Use Data (header) Labeler",
                                        variable=self.var_use_data_labeler,
                                        onvalue=1, offvalue=0)
        cb_data_label.grid(row=row, column=0, padx=xpad, pady=ypad)
        self.data_labeler = tk.Text(self.fr_setup, height=1, width=20)
        self.data_labeler.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        self.var_normalize_colors = tk.IntVar()
        cb_norm = ttk.Checkbutton(self.fr_setup,
                                  text="Normalize colors by data value",
                                  variable=self.var_normalize_colors,
                                  onvalue=1, offvalue=0)
        cb_norm.grid(row=row, column=0, columnspan=2, padx=xpad, pady=ypad, sticky='w')
        row += 1

        btn_appearance = tk.Button(self.fr_setup, text="Appearance Options...",
                                   command=self.open_appearance_dialog,
                                   bg=self.theme_config["light_3"],
                                   fg=self.theme_config["fg_dark"],
                                   height=1)
        btn_appearance.grid(row=row, column=0, columnspan=2, padx=xpad, pady=(6, 2), sticky='w')
        row += 1

        # ── Data Configuration ────────────────────────────
        sep2 = ttk.Separator(self.fr_setup, orient='horizontal')
        sep2.grid(row=row, column=0, columnspan=3, sticky='ew', pady=(8, 2))
        row += 1

        lbl_section2 = tk.Label(self.fr_setup, text="Data Configuration",
                                font=(self.theme_config["font"]["family"], 9, "bold"),
                                bg=self.theme_config["light_4"])
        lbl_section2.grid(row=row, column=0, columnspan=2, sticky='w', padx=5)
        row += 1

        lbl_x_var = tk.Label(self.fr_setup, text="X-variable")
        lbl_y_var = tk.Label(self.fr_setup, text="Y-variable")
        lbl_x_scale = tk.Label(self.fr_setup, text="X-scale")
        lbl_y_scale = tk.Label(self.fr_setup, text="Y-scale")

        self.x_var = tk.Text(self.fr_setup, height=1, width=20)
        self.y_var = tk.Text(self.fr_setup, height=1, width=20)
        self.x_scale = tk.Spinbox(self.fr_setup, from_=1, to=10e9)
        self.y_scale = tk.Spinbox(self.fr_setup, from_=1, to=10e9)

        self.x_var.bind("<Tab>", focus_next_widget)
        self.y_var.bind("<Tab>", focus_next_widget)
        self.x_scale.bind("<Tab>", focus_next_widget)
        self.y_scale.bind("<Tab>", focus_next_widget)

        lbl_x_var.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.x_var.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        lbl_y_var.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.y_var.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='ew')
        row += 1

        lbl_x_scale.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.x_scale.grid(row=row, column=1, padx=xpad, pady=ypad)
        row += 1

        lbl_y_scale.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.y_scale.grid(row=row, column=1, padx=xpad, pady=ypad)
        row += 1

        lbl_start_row = tk.Label(self.fr_setup, text="Start row")
        lbl_end_row = tk.Label(self.fr_setup, text="End row")
        self.entry_start_row = tk.Entry(self.fr_setup, width=10)
        self.entry_end_row = tk.Entry(self.fr_setup, width=10)

        lbl_start_row.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.entry_start_row.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='w')
        row += 1

        lbl_end_row.grid(row=row, column=0, padx=5, pady=2, sticky='e')
        self.entry_end_row.grid(row=row, column=1, padx=xpad, pady=ypad, sticky='w')
        row += 1

        # ── Tooltips ─────────────────────────────────────
        guic.Tooltip(lbl_title, "Graph title displayed above the plot")
        guic.Tooltip(lbl_x_axis, "Label shown on the X-axis")
        guic.Tooltip(lbl_y_axis, "Label shown on the Y-axis")
        guic.Tooltip(lbl_plot_style, "Line, scatter, or both")
        guic.Tooltip(cb_file_label, "Label each line by a part of its filename.\nLeave the text box empty to use the full filename stem.\nEnter an index (e.g. 3) to use the Nth underscore-delimited part\n(e.g. index 2 on 'AREC_20260204_25C_sweep.csv' gives '25C')")
        guic.Tooltip(cb_data_label, "Color/label each line by a CSV column value")
        guic.Tooltip(cb_norm, "Map label values to a color gradient instead of discrete colors")
        guic.Tooltip(lbl_x_var, "CSV column name to use for X-axis data")
        guic.Tooltip(lbl_y_var, "CSV column name to use for Y-axis data")
        guic.Tooltip(lbl_x_scale, "Multiply all X values by this factor (e.g. 0.001 to convert ms to s)")
        guic.Tooltip(lbl_y_scale, "Multiply all Y values by this factor")
        guic.Tooltip(lbl_start_row, "First row to include (0-based, leave blank for beginning)")
        guic.Tooltip(lbl_end_row, "Last row to include (exclusive, leave blank for end)")

    def init_fr_files(self):
        fr_m = self.fr_files

        # add directory search
        self.lbl_data_directory = tk.Label(fr_m, text=self.data_dir, fg=self.theme_config["fg_light"],
                                           bg=self.theme_config["bg_light"])
        self.lbl_data_directory.grid(row=0, column=0)
        btn_set_directory = tk.Button(fr_m, text="Set directory",
                                      command=lambda: self.set_directory(),
                                      bg=self.theme_config["light_1"], fg=self.theme_config["fg_dark"],
                                      height=self.theme_config["size"]["h_button"],
                                      width=self.theme_config["size"]["w_button"])
        btn_set_directory.grid(row=0, column=1, padx=self.theme_config["pad"]["xpad_s"],
                               pady=self.theme_config["pad"]["ypad_s"])

        # Create Listbox with multi-select support and scrollbar
        listbox_frame = tk.Frame(self.fr_files)
        listbox_frame.grid(row=1, column=0, rowspan=4, padx=self.theme_config["pad"]["xpad_m"],
                           pady=self.theme_config["pad"]["ypad_m"])

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        self.file_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.EXTENDED,  # Enable multi-select
            width=50,
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.pack(side="left", fill="both", expand=True)

        # Bind selection event
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        # Selection info label
        self.file_selection_label = tk.Label(fr_m, text="0 files selected", relief='sunken')
        self.file_selection_label.grid(row=6, column=0, padx=10, pady=5, sticky='ew')

        # add check box and text field to filter files by string
        self.var_use_file_regex = tk.IntVar()
        ttk.Checkbutton(fr_m,
                        text="Use Filename Filter",
                        variable=self.var_use_file_regex,
                        onvalue=1,
                        offvalue=0).grid(row=9, column=0, padx=self.theme_config["pad"]["xpad_s"],
                                         pady=self.theme_config["pad"]["ypad_s"])
        self.file_filter = tk.Text(fr_m, height=1, width=20)
        self.file_filter.grid(row=9, column=1, padx=self.theme_config["pad"]["xpad_s"],
                              pady=self.theme_config["pad"]["ypad_s"])

        # set up button to REFRESH FILES
        btn_refresh_files = tk.Button(fr_m, text="Refresh Files",
                                      command=lambda: self.refresh_files(),
                                      bg=self.theme_config["light_2"], fg=self.theme_config["fg_dark"],
                                      height=self.theme_config["size"]["h_button"],
                                      width=self.theme_config["size"]["w_button"])
        btn_refresh_files.grid(row=1, column=1, padx=self.theme_config["pad"]["xpad_s"],
                               pady=self.theme_config["pad"]["ypad_s"])

        # set up button PRINT FIELDS
        btn_disp_fields = tk.Button(fr_m, text="Print fields",
                                    command=self.disp_fields,
                                    bg=self.theme_config["light_3"], fg=self.theme_config["fg_dark"],
                                    height=self.theme_config["size"]["h_button"],
                                    width=self.theme_config["size"]["w_button"])
        btn_disp_fields.grid(row=2, column=1, padx=self.theme_config["pad"]["xpad_s"],
                             pady=self.theme_config["pad"]["ypad_s"])

        # analyze button + FFT checkbox
        open_button = tk.Button(fr_m,
                                text="Analyze Selected Files",
                                command=self.analyze_files,
                                bg=self.theme_config["dark_3"], fg=self.theme_config["fg_light"],
                                height=self.theme_config["size"]["h_button"],
                                width=self.theme_config["size"]["w_button"])
        open_button.grid(row=3, column=1, padx=10, pady=10)

        self.var_analyze_fft = tk.IntVar()
        ttk.Checkbutton(fr_m,
                        text="Analyze FFT",
                        variable=self.var_analyze_fft,
                        onvalue=1,
                        offvalue=0).grid(row=3, column=2, padx=self.theme_config["pad"]["xpad_s"],
                                         pady=self.theme_config["pad"]["ypad_s"], sticky='w')

        # plot button
        graph_button = tk.Button(fr_m,
                                 text="Graph Selected Files",
                                 command=self.graph_files,
                                 bg=self.theme_config["success"], fg=self.theme_config["fg_dark"],
                                 height=self.theme_config["size"]["h_button"],
                                 width=self.theme_config["size"]["w_button"])
        graph_button.grid(row=4, column=1, padx=10, pady=10)

    def gui_refresh(self, event):
        pass

    def open_appearance_dialog(self):
        GraphOptionsDialog(self, self.appearance_config, self._apply_appearance)

    def _apply_appearance(self, config):
        self.appearance_config = config
        self.prompt.print("Appearance options updated")

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def set_directory(self):
        self.data_dir = filedialog.askdirectory()
        if self.data_dir is None or self.data_dir == "":
            return
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
        """Get list of selected file data (FileData named tuples)"""
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return []

        selected_files = []
        for idx in selected_indices:
            if idx < len(self.files):
                selected_files.append(self.files[idx])

        return selected_files

    def refresh_files(self):
        files = []  # list of FileData named tuples

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
                files.append(FileData(
                    filename=filename,
                    filepath=filepath,
                    parts=parts,
                    df=df))
            return files

        # update file list
        self.files = grab_files()

        self.file_listbox.delete(0, tk.END)
        for file in self.files:
            self.file_listbox.insert(tk.END, file[0])

        self.prompt.print(f"Loaded {len(self.files)} files")

    def disp_fields(self):
        selected_files = self.get_selected_files()
        for filename, _, _, df in selected_files:
            self.prompt.print(f"Filename: {filename} --> {list(df.columns)}")

    def graph_files(self):
        # Get selected files
        selected_files = self.get_selected_files()

        if not selected_files:
            guih.alert_user("No Files Selected", "Please select one or more files to graph", "warning")
            return False

        # Apply row range if specified
        start_str = self.entry_start_row.get().strip()
        end_str = self.entry_end_row.get().strip()
        try:
            start_row = int(start_str) if start_str else None
            end_row = int(end_str) if end_str else None
        except ValueError:
            guih.alert_user("Invalid Row Range", "Start/end row must be integers.", "error")
            return False
        if start_row is not None or end_row is not None:
            selected_files = [
                FileData(fd.filename, fd.filepath, fd.parts, fd.df.iloc[start_row:end_row].reset_index(drop=True))
                for fd in selected_files
            ]

        self.prompt.print(f"Graphing {len(selected_files)} selected file(s)...")

        # Parse GUI values
        try:
            x_scale_str = self.x_scale.get().strip()
            y_scale_str = self.y_scale.get().strip()
            x_scale = float(x_scale_str)
            y_scale = float(y_scale_str)
        except ValueError as e:
            error_msg = (
                f"Invalid scale factor: {str(e)}\n\n"
                f"X-scale: '{x_scale_str}'\n"
                f"Y-scale: '{y_scale_str}'\n\n"
                f"Accepted formats:\n"
                f"  • Decimal: 0.001, 1.5, 1000\n"
                f"  • Scientific: 1e-3, 1.5e2, 2E+4\n"
                f"  • Integer: 1, 10, 1000"
            )
            guih.alert_user("Invalid Scale Factor", error_msg, "error")
            self.prompt.print(f"Error: Invalid scale factor - X: '{x_scale_str}', Y: '{y_scale_str}'", "error")
            return False

        # Determine labeling mode and configuration
        if self.var_use_file_labeler.get() and self.var_use_data_labeler.get():
            # Both checkboxes checked - use combined mode
            labeling_mode = 'both'
            try:
                file_label_idx = int(self.file_labeler.get("1.0", "end").strip("\n"))
            except ValueError:
                file_label_idx = 0
            data_label_var = self.data_labeler.get("1.0", "end").strip("\n")
            label_config = {
                'file_label_idx': file_label_idx,
                'data_label_var': data_label_var,
                'normalize_colors': self.var_normalize_colors.get()
            }
        elif self.var_use_file_labeler.get():
            labeling_mode = 'filename'
            try:
                file_label_idx = int(self.file_labeler.get("1.0", "end").strip("\n"))
            except ValueError:
                file_label_idx = 0
            label_config = {'file_label_idx': file_label_idx}
        elif self.var_use_data_labeler.get():
            labeling_mode = 'data'
            data_label_var = self.data_labeler.get("1.0", "end").strip("\n")
            label_config = {
                'data_label_var': data_label_var,
                'normalize_colors': self.var_normalize_colors.get()
            }
        else:
            labeling_mode = 'none'
            label_config = {}

        # Get plot style
        plot_style = self.plot_style_drop[1].get()

        # Call abstracted plotting function
        ac = self.appearance_config
        try:
            plotter.plot_multi_file_data(
                file_data_list=selected_files,
                x_var=self.x_var.get("1.0", "end").strip("\n"),
                y_var=self.y_var.get("1.0", "end").strip("\n"),
                x_scale=x_scale,
                y_scale=y_scale,
                title=self.title.get("1.0", "end").strip("\n"),
                xlabel=self.x_label.get("1.0", "end").strip("\n"),
                ylabel=self.y_label.get("1.0", "end").strip("\n"),
                labeling_mode=labeling_mode,
                label_config=label_config,
                plot_style=plot_style,
                figsize=(ac["figsize_w"], ac["figsize_h"]),
                marker='o',
                markersize=ac["markersize"],
                show_grid=ac["show_grid"],
                grid_alpha=ac["grid_alpha"],
                xtick_rotation=ac["xtick_rotation"],
                ytick_rotation=ac["ytick_rotation"],
                show_legend=ac["show_legend"],
                legend_loc=ac["legend_loc"],
                linewidth=ac["linewidth"],
                alpha=ac["alpha"],
                xtick_max=ac["xtick_max"],
            )
            self.prompt.print("Graph complete!")
            return True
        except KeyError as e:
            col_lines = "\n".join(f"  {fd.filename}: {list(fd.df.columns)}" for fd in selected_files)
            guih.alert_user("Key Error in Data File", f"{e}\n\nAvailable columns:\n{col_lines}", "error")
            self.prompt.print(f"Error: column {e} not found. Available columns:", "error")
            for fd in selected_files:
                self.prompt.print(f"  {fd.filename}: {list(fd.df.columns)}", "error")
            return False
        except ValueError as e:
            guih.alert_user("Value Error", str(e), "error")
            self.prompt.print(f"Error: {str(e)}", "error")
            return False
        except Exception as e:
            guih.alert_user("Plotting Error", f"An unexpected error occurred: {str(e)}", "error")
            self.prompt.print(f"Error: {str(e)}", "error")
            return False

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
            col_stats = data_helper.summarize_dataframe(df)
            if col_stats:
                self.prompt.print("\nStatistics:")
                for col, s in col_stats.items():
                    self.prompt.print(
                        f"  {col}: mean={s['mean']:.4f}, std={s['std']:.4f}, min={s['min']:.4f}, max={s['max']:.4f}")

            # Time-series analysis (requires a 'Time' column written by the logger)
            if "Time" in df.columns:
                try:
                    dtime_arr = stats_analysis.create_datetime(df["Time"].dropna().tolist())
                    if len(dtime_arr) >= 2:
                        t = stats_analysis.analyze_time(dtime_arr)
                        self.prompt.print("\nTime Analysis:")
                        self.prompt.print(f"  Duration:     {t['dur_sec']:.3f} s  ({t['dur_min']:.2f} min)")
                        self.prompt.print(f"  Samples:      {t['samples']}")
                        self.prompt.print(f"  Sample rate:  {t['frequency']:.3f} Hz  ({1000/t['frequency']:.1f} ms/sample)")

                        # FFT — dominant frequency per numeric column
                        if self.var_analyze_fft.get():
                            dt = 1.0 / t['frequency']
                            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                            fft_channels = []
                            if numeric_cols:
                                self.prompt.print(f"\nFFT Analysis (Fs={t['frequency']:.3f} Hz):")
                                for col in numeric_cols:
                                    data = pd.to_numeric(df[col], errors='coerce').dropna().values
                                    if len(data) < 8:
                                        continue
                                    fft_mag = np.abs(np.fft.rfft(data - np.mean(data)))
                                    freqs = np.fft.rfftfreq(len(data), d=dt)
                                    if len(fft_mag) > 1:
                                        dom_idx = np.argmax(fft_mag[1:]) + 1
                                        self.prompt.print(f"  {col}: dominant freq = {freqs[dom_idx]:.4f} Hz")
                                        fft_channels.append((freqs, fft_mag, col))
                                if fft_channels:
                                    plotter.plot_fft(fft_channels, title=f"FFT — {filename}")
                    else:
                        self.prompt.print("\nTime Analysis: not enough samples")
                except Exception as e:
                    self.prompt.print(f"\nTime Analysis failed: {e}", "warning")

        self.prompt.print("\nAnalysis complete!")
        return True

    ##############################################################################
    ####      PRESET FUNCTIONS        ############################################
    ##############################################################################

    def refresh_presets(self):
        """Scan preset directory and populate dropdown with available presets"""
        preset_files = []
        if os.path.exists(self.preset_dir):
            for filename in os.listdir(self.preset_dir):
                if filename.endswith('.json'):
                    preset_files.append(filename[:-5])  # Remove .json extension

        self.preset_combo['values'] = sorted(preset_files)
        if preset_files:
            self.preset_combo.set('')  # Clear selection

    def on_preset_select(self, event):
        """Callback when a preset is selected from dropdown"""
        selected = self.preset_combo.get()
        if selected:
            self.load_preset()

    def save_preset(self):
        """Save current graph parameters to a preset file"""
        # Ask user for preset name
        from tkinter import simpledialog
        preset_name = simpledialog.askstring("Save Preset", "Enter preset name:")

        if not preset_name:
            return

        # Remove .json extension if user added it
        if preset_name.endswith('.json'):
            preset_name = preset_name[:-5]

        # Gather all parameters
        preset_data = {
            "title": self.title.get("1.0", "end").strip("\n"),
            "x_label": self.x_label.get("1.0", "end").strip("\n"),
            "y_label": self.y_label.get("1.0", "end").strip("\n"),
            "x_scale": self.x_scale.get(),
            "y_scale": self.y_scale.get(),
            "x_var": self.x_var.get("1.0", "end").strip("\n"),
            "y_var": self.y_var.get("1.0", "end").strip("\n"),
            "plot_style": self.plot_style_drop[1].get(),
            "use_file_regex": self.var_use_file_regex.get(),
            "file_filter": self.file_filter.get("1.0", "end").strip("\n"),
            "use_file_labeler": self.var_use_file_labeler.get(),
            "file_labeler": self.file_labeler.get("1.0", "end").strip("\n"),
            "use_data_labeler": self.var_use_data_labeler.get(),
            "data_labeler": self.data_labeler.get("1.0", "end").strip("\n"),
            "normalize_colors": self.var_normalize_colors.get(),
            "start_row": self.entry_start_row.get().strip(),
            "end_row":   self.entry_end_row.get().strip(),
            # Future use - data source configuration
            # "data_dir": self.data_dir
        }

        # Save to JSON file
        filepath = os.path.join(self.preset_dir, f"{preset_name}.json")
        try:
            with open(filepath, 'w') as f:
                json.dump(preset_data, f, indent=4)
            self.prompt.print(f"Preset saved: {preset_name}")
            self.refresh_presets()
            self.preset_combo.set(preset_name)
        except Exception as e:
            guih.alert_user("Save Error", f"Failed to save preset: {str(e)}", "error")
            self.prompt.print(f"Error saving preset: {str(e)}", "error")

    def load_preset(self):
        """Load a preset and populate all graph parameters"""
        selected = self.preset_combo.get()
        if not selected:
            guih.alert_user("No Preset Selected", "Please select a preset to load", "warning")
            return

        filepath = os.path.join(self.preset_dir, f"{selected}.json")

        try:
            with open(filepath, 'r') as f:
                preset_data = json.load(f)

            # Clear and populate text widgets
            self.title.delete("1.0", "end")
            self.title.insert("1.0", preset_data.get("title", ""))

            self.x_label.delete("1.0", "end")
            self.x_label.insert("1.0", preset_data.get("x_label", ""))

            self.y_label.delete("1.0", "end")
            self.y_label.insert("1.0", preset_data.get("y_label", ""))

            self.x_var.delete("1.0", "end")
            self.x_var.insert("1.0", preset_data.get("x_var", ""))

            self.y_var.delete("1.0", "end")
            self.y_var.insert("1.0", preset_data.get("y_var", ""))

            self.file_filter.delete("1.0", "end")
            self.file_filter.insert("1.0", preset_data.get("file_filter", ""))

            self.file_labeler.delete("1.0", "end")
            self.file_labeler.insert("1.0", preset_data.get("file_labeler", ""))

            self.data_labeler.delete("1.0", "end")
            self.data_labeler.insert("1.0", preset_data.get("data_labeler", ""))

            # Set spinbox values
            self.x_scale.delete(0, "end")
            self.x_scale.insert(0, preset_data.get("x_scale", "1"))

            self.y_scale.delete(0, "end")
            self.y_scale.insert(0, preset_data.get("y_scale", "1"))

            # Set plot style dropdown
            self.plot_style_drop[1].set(preset_data.get("plot_style", "Line + Scatter"))

            # Set checkbox values
            self.var_use_file_regex.set(preset_data.get("use_file_regex", 0))
            self.var_use_file_labeler.set(preset_data.get("use_file_labeler", 0))
            self.var_use_data_labeler.set(preset_data.get("use_data_labeler", 0))
            self.var_normalize_colors.set(preset_data.get("normalize_colors", 0))

            self.entry_start_row.delete(0, "end")
            self.entry_start_row.insert(0, preset_data.get("start_row", ""))
            self.entry_end_row.delete(0, "end")
            self.entry_end_row.insert(0, preset_data.get("end_row", ""))

            # Future: data_dir loading
            # if "data_dir" in preset_data:
            #     self.data_dir = preset_data["data_dir"]
            #     self.lbl_data_directory.config(text=self.data_dir)

            self.prompt.print(f"Preset loaded: {selected}")

        except FileNotFoundError:
            guih.alert_user("Preset Not Found", f"Preset file not found: {selected}", "error")
            self.prompt.print(f"Error: Preset file not found: {selected}", "error")
        except json.JSONDecodeError as e:
            guih.alert_user("Invalid Preset", f"Preset file is corrupted: {str(e)}", "error")
            self.prompt.print(f"Error: Invalid preset file: {str(e)}", "error")
        except Exception as e:
            guih.alert_user("Load Error", f"Failed to load preset: {str(e)}", "error")
            self.prompt.print(f"Error loading preset: {str(e)}", "error")

    def clear_all_fields(self):
        """Clear all graph parameter fields and reset to defaults"""
        # Clear all text widgets
        self.title.delete("1.0", "end")
        self.x_label.delete("1.0", "end")
        self.y_label.delete("1.0", "end")
        self.x_var.delete("1.0", "end")
        self.y_var.delete("1.0", "end")
        self.file_filter.delete("1.0", "end")
        self.file_labeler.delete("1.0", "end")
        self.data_labeler.delete("1.0", "end")
        self.entry_start_row.delete(0, "end")
        self.entry_end_row.delete(0, "end")

        # Reset spinbox values to 1
        self.x_scale.delete(0, "end")
        self.x_scale.insert(0, "1")
        self.y_scale.delete(0, "end")
        self.y_scale.insert(0, "1")

        # Reset plot style to default
        self.plot_style_drop[1].set("Line + Scatter")

        # Uncheck all checkboxes
        self.var_use_file_regex.set(0)
        self.var_use_file_labeler.set(0)
        self.var_use_data_labeler.set(0)
        self.var_normalize_colors.set(0)

        # Clear preset selection
        self.preset_combo.set('')

        self.prompt.print("All fields cleared")
