"""Data logging, live plotting, and stimulus control tab."""


# import needed GUI modules
import logging
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle

# import needed modules
import os
import threading
import time
from datetime import datetime
import pandas as pd
from queue import Queue

# import user defined modules
from common import logger
from common import plotter
from common import path_helper
from common.math_columns import MathColumn, MathConfig, MathEvaluator, save_math_config, load_math_config

_logger = logging.getLogger(__name__)




class TabLog(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath

        self.grid(row=0, column=0)

        # set up recording information
        self.record_speed = 1
        self.record_status = False
        self.recCnt = 0
        self.data_dir = path_helper.get_full_data_path()
        self.csvh = None
        self.record_config = None
        self.stimulus_config = None
        self.stimulus_generator = None
        self.bus = None
        self._record_thread = None
        self._dash_thread = None
        self._paused = False
        self._live_state = {}
        self.math_config = MathConfig()
        self.math_evaluator = None
        self.math_preset_dir = os.path.join(os.path.dirname(basefilepath), "config", "math_presets")

        # create top row Frames (parented to self)
        self.fr_status = tk.Frame(self, bg=self.theme_config["dark_2"])
        self.fr_setup = tk.Frame(self, bg=self.theme_config["dark_2"])

        # bottom row container (its own grid, independent column sizing from top row)
        self.fr_bottom = tk.Frame(self, bg=self.theme_config["bg_dark"])
        self.fr_stimulus = tk.Frame(self.fr_bottom, bg=self.theme_config["dark_2"])
        self.fr_math = tk.Frame(self.fr_bottom, bg=self.theme_config["dark_2"])

        # Prompt parent depends on mode:
        #   compact -> inside fr_bottom (beside stimulus/math)
        #   normal  -> on its own row at the bottom of the tab (full width)
        compact = self.theme_config.get("compact", False)
        prompt_parent = self.fr_bottom if compact else self
        self.prompt = guic.Prompt(prompt_parent, self.theme_config, "Data Logger Output")

        # place top row
        self.fr_status.grid(row=0, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nw")
        self.fr_setup.grid(row=0, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nw")

        # place bottom row container spanning full width
        self.fr_bottom.grid(row=1, column=0, columnspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nsew")

        # place items inside bottom row (independent column sizing)
        self.fr_stimulus.grid(row=0, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nw")
        self.fr_math.grid(row=0, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nw")

        if compact:
            # compact: prompt sits beside stimulus/math in fr_bottom
            self.prompt.grid(row=0, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nsew")
            self.fr_bottom.columnconfigure(2, weight=1)
            self.fr_bottom.rowconfigure(0, weight=1)
        else:
            # normal: prompt gets its own full-width row at the bottom
            self.prompt.grid(row=2, column=0, columnspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nsew")
            self.rowconfigure(2, weight=1)

        # parent weights
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        _logger.debug("Initializing tab 8 (Logger) content")

        self.init_fr_status()
        self.init_fr_setup()
        self.init_fr_stimulus()
        self.init_fr_math()

    def init_fr_status(self):
        # Serial connection status
        self.labelSerStat = ttk.Label(self.fr_status, width=10, text='Serial', style="TLabel", anchor='w')
        self.ser_status = ColorCircle(self.fr_status, width=25, height=25,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelSerStat.grid(row=0, column=0)
        self.ser_status.grid(row=0, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # DMM connection status
        self.labelDmmStat = ttk.Label(self.fr_status, width=10, text='DMM', style="TLabel", anchor='w')
        self.dmm_status = ColorCircle(self.fr_status, width=25, height=25,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelDmmStat.grid(row=1, column=0)
        self.dmm_status.grid(row=1, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # PS connection status
        self.labelPsStat = ttk.Label(self.fr_status, width=10, text='PS', style="TLabel", anchor='w')
        self.ps_status = ColorCircle(self.fr_status, width=25, height=25,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelPsStat.grid(row=2, column=0)
        self.ps_status.grid(row=2, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # FG connection status
        self.labelFgStat = ttk.Label(self.fr_status, width=10, text='FG', style="TLabel", anchor='w')
        self.fg_status = ColorCircle(self.fr_status, width=25, height=25,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelFgStat.grid(row=3, column=0)
        self.fg_status.grid(row=3, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # OSC connection status
        self.labelOscStat = ttk.Label(self.fr_status, width=10, text='OSC', style="TLabel", anchor='w')
        self.osc_status = ColorCircle(self.fr_status, width=25, height=25,
                                    bg=self.theme_config["bg_dark"])
        self.labelOscStat.grid(row=4, column=0)
        self.osc_status.grid(row=4, column=1, pady=self.theme_config["pad"]["ypad_s"])

    def init_fr_setup(self):
        # add directory search
        self.lbl_data_directory = tk.Label(self.fr_setup, text=self.data_dir, bg=self.theme_config["bg_light"])
        self.lbl_data_directory.grid(row=2, column=0)
        btn_set_directory = tk.Button(self.fr_setup, text="Set directory",
                                 command=lambda: self.set_record_directory(),
                                 fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"],
                                height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_set_directory.grid(row=2, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # add output file name box
        tk.Label(self.fr_setup, text="Output file name").grid(row=2, column=2, padx=5, pady=20)
        self.output_file_name = tk.Text(self.fr_setup, height=2, width=20)
        self.output_file_name.grid(row=2, column=3, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # add check boxes for the various options
        self.var_use_ser = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use Serial",
                        variable=self.var_use_ser,
                        onvalue=1, offvalue=0,
                        command=self.toggle_use_ser).grid(row=3, column=0, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])


        self.var_use_dmm = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use DMM",
                        variable=self.var_use_dmm,
                        onvalue=1, offvalue=0).grid(row=3, column=1)

        self.var_use_ps = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use PS",
                        variable=self.var_use_ps,
                        onvalue=1, offvalue=0,
                        command=self.toggle_use_ps).grid(row=3, column=2)

        self.var_use_fg = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use FG",
                        variable=self.var_use_fg,
                        onvalue=1, offvalue=0).grid(row=3, column=3)

        # OSC checkbox and configure button
        self.var_use_osc = tk.IntVar()
        self.osc_record_config = None
        ttk.Checkbutton(self.fr_setup,
                        text="Use OSC",
                        variable=self.var_use_osc,
                        onvalue=1, offvalue=0,
                        command=self.toggle_use_osc).grid(row=3, column=4)
        self.btn_osc_config = tk.Button(self.fr_setup, text="Configure OSC...",
                                 command=self.open_osc_config_dialog,
                                 fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"],
                                 state=tk.DISABLED)
        self.btn_osc_config.grid(row=4, column=4, padx=self.theme_config["pad"]["xpad_s"],
                                 pady=self.theme_config["pad"]["ypad_s"])

        # add serial parameters box
        self.lbl_use_ser = tk.Label(self.fr_setup, text="Serial columns (comma-separated):")
        self.serial_log_params = tk.Text(self.fr_setup, height=2, width=40)
        self.serial_log_params.insert("1.0", "col1,col2,col3")
        self.serial_log_params.tag_add("placeholder", "1.0", "end")
        self.serial_log_params.tag_config("placeholder", foreground="gray")

        self.lbl_use_ser.grid(row=4, column=1, padx=5, pady=5)
        self.serial_log_params.grid(row=4, column=2, padx=self.theme_config["pad"]["xpad_s"],
                                    pady=self.theme_config["pad"]["ypad_s"])
        self.toggle_use_ser() # NOTE: initial state should be OFF so serial parameters should be hidden

        # sample rate: number entry + unit dropdown
        fr_sample_rate = tk.Frame(self.fr_setup, bg=self.theme_config["dark_2"])
        fr_sample_rate.grid(row=6, column=0, padx=self.theme_config["pad"]["xpad_s"],
                            pady=self.theme_config["pad"]["ypad_s"])
        ttk.Label(fr_sample_rate, text="Rate:", style="TSpunkLabel.TLabel").pack(side="left", padx=(0, 3))
        self.entry_sample_val = tk.Entry(fr_sample_rate, width=6)
        self.entry_sample_val.insert(0, "1")
        self.entry_sample_val.pack(side="left")
        self.optRecSpdUnit, self.RecSpdUnitVal = guih.generate_drop_down(fr_sample_rate, ['s', 'min', 'hr'])
        self.optRecSpdUnit.pack(side="left", padx=(3, 0))

        # add PS channel setup
        self.lbl_rec_ps_channel = (ttk.Label(self.fr_setup, text="PS Channel:", style="TSpunkLabel.TLabel"))
        self.lbl_rec_ps_channel.grid(row=5, column=1, sticky='e', padx=5, pady=2)
        self.rec_ps_channel_drop = guih.generate_drop_down(
            self.fr_setup,
            [1, 2]
        )
        self.rec_ps_channel_drop[0].grid(row=5, column=2, padx=5, pady=2)
        self.toggle_use_ps()

        # set up button START recording
        btn_start_entry = tk.Button(self.fr_setup, text="Start Record",
                                 command=lambda: self.start_record(),
                                 bg=self.theme_config["success"], fg=self.theme_config["fg_light"], height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=6, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button STOP recording
        btn_stop_entry = tk.Button(self.fr_setup, text="Stop Record",
                                command=lambda: self.stop_record(),
                                bg=self.theme_config["error"], fg=self.theme_config["fg_light"], height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_stop_entry.grid(row=6, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button PAUSE/RESUME recording (disabled until recording starts)
        self.btn_pause = tk.Button(self.fr_setup, text="Pause",
                                   command=lambda: self.pause_record(),
                                   bg=self.theme_config["warning"], fg=self.theme_config["fg_dark"],
                                   height=self.theme_config["size"]["h_button"],
                                   width=self.theme_config["size"]["w_button"],
                                   state=tk.DISABLED)
        self.btn_pause.grid(row=6, column=4, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        self.labelRNums = ttk.Label(self.fr_setup, text='', width=12, relief='sunken')
        self.labelRNums.grid(row=6, column=3, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"], sticky='W')

        # add check button to graph data
        self.var_graph_data = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Graph",
                        variable=self.var_graph_data,
                        onvalue=1,
                        offvalue=0,
                        command=self.toggle_graph_options).grid(row=7, column=2)

        # graph sub-options (only visible when Graph is checked)
        self.var_3d_plot = tk.IntVar()
        self.chk_3d_plot = ttk.Checkbutton(self.fr_setup,
                        text="3D Plot",
                        variable=self.var_3d_plot,
                        onvalue=1,
                        offvalue=0)
        self.chk_3d_plot.grid(row=8, column=2)
        self.chk_3d_plot.grid_remove()

        self.var_subplots = tk.IntVar(value=1)
        self.chk_subplots = ttk.Checkbutton(self.fr_setup,
                        text="Subplots",
                        variable=self.var_subplots,
                        onvalue=1,
                        offvalue=0)
        self.chk_subplots.grid(row=7, column=3)
        self.chk_subplots.grid_remove()

        # add check button to graph data
        self.var_save_data = tk.IntVar(value=1)
        ttk.Checkbutton(self.fr_setup,
                        text="Save data",
                        variable=self.var_save_data,
                        onvalue=1,
                        offvalue=0).grid(row=7, column=3)

        # live plot checkbox
        self.var_live_plot = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Live Plot",
                        variable=self.var_live_plot,
                        onvalue=1,
                        offvalue=0,
                        command=self.toggle_live_plot_options).grid(row=7, column=1)

        # live plot buffer size (only visible when Live Plot is checked)
        self.lbl_buf_size = ttk.Label(self.fr_setup, text="Buffer size:", style="TSpunkLabel.TLabel")
        self.lbl_buf_size.grid(row=8, column=0, sticky='e', padx=5, pady=2)
        self.entry_buf_size = tk.Entry(self.fr_setup, width=8)
        self.entry_buf_size.insert(0, "3000")
        self.entry_buf_size.grid(row=8, column=1, sticky='w', padx=5, pady=2)
        self.entry_buf_size.bind("<KeyRelease>", lambda e: self._update_time_window_label())

        self.lbl_time_window = ttk.Label(self.fr_setup, text="", style="TSpunkLabel.TLabel")
        self.lbl_time_window.grid(row=9, column=0, columnspan=2, padx=5, pady=2)

        self.btn_export_html = tk.Button(self.fr_setup, text="Export HTML",
                                         command=lambda: self.export_live_plot_html(),
                                         fg=self.theme_config["fg_dark"],
                                         bg=self.theme_config["light_4"])
        self.btn_export_html.grid(row=8, column=2, padx=5, pady=2)

        # hide buffer options initially
        self.lbl_buf_size.grid_remove()
        self.entry_buf_size.grid_remove()
        self.lbl_time_window.grid_remove()
        self.btn_export_html.grid_remove()

        # update time window label when sample rate changes
        self.entry_sample_val.bind("<KeyRelease>", lambda e: self._update_time_window_label())
        self.RecSpdUnitVal.trace_add("write", lambda *_: self._update_time_window_label())

    def init_fr_stimulus(self):
        """Initialize stimulus sweep configuration UI"""
        # Title
        ttk.Label(self.fr_stimulus, text="Stimulus Sweep", style="TPinkLabel.TLabel").grid(row=0, column=0, columnspan=2, pady=5, padx=10)

        # Enable stimulus checkbox
        self.var_use_stimulus = tk.IntVar()
        ttk.Checkbutton(self.fr_stimulus,
                        text="Enable Stimulus Sweep",
                        variable=self.var_use_stimulus,
                        onvalue=1, offvalue=0,
                        command=self.toggle_stimulus).grid(
            row=1, column=0, columnspan=2, padx=5, pady=5
        )

        # Enable dual stimulus checkbox
        self.var_use_dual_stimulus = tk.IntVar()
        ttk.Checkbutton(self.fr_stimulus,
                        text="Enable Dual Sweep (Nested Loop)",
                        variable=self.var_use_dual_stimulus,
                        onvalue=1, offvalue=0,
                        command=self.toggle_dual_stimulus).grid(
            row=1, column=2, columnspan=2, padx=5, pady=5
        )

        # === FIRST STIMULUS (or Outer Loop) ===
        tk.Label(self.fr_stimulus, text="--- Parameter 1 (Outer Loop) ---",
                 font=('TkDefaultFont', 9, 'bold')).grid(row=2, column=0, columnspan=2)

        # Stimulus type dropdown
        ttk.Label(self.fr_stimulus, text="Stimulus Type:", style="TSpunkLabel.TLabel").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.stimulus_type_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [s.value for s in logger.StimulusType if s is not logger.StimulusType.NONE],
        )
        self.stimulus_type_drop[0].grid(row=3, column=1, padx=5, pady=2)

        # Sweep mode dropdown
        ttk.Label(self.fr_stimulus, text="Sweep Mode:", style="TSpunkLabel.TLabel").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        self.sweep_mode_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [s.value for s in logger.SweepMode],
        )
        self.sweep_mode_drop[0].grid(row=4, column=1, padx=5, pady=2)

        # Start value
        ttk.Label(self.fr_stimulus, text="Start Value:", style="TSpunkLabel.TLabel").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        self.stim_start_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_start_entry.grid(row=5, column=1, padx=5, pady=2)
        self.stim_start_entry.insert(0, "1.0")

        # Stop value
        ttk.Label(self.fr_stimulus, text="Stop Value:", style="TSpunkLabel.TLabel").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        self.stim_stop_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_stop_entry.grid(row=6, column=1, padx=5, pady=2)
        self.stim_stop_entry.insert(0, "10.0")

        # Step mode dropdown (Increment OR Number of Steps)
        self.step_mode_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [s.value for s in logger.StepMode],
            theme_config=self.theme_config,
            width=10
        )
        self.step_mode_drop[0].grid(row=7, column=0, stick='w', padx=5, pady=2)

        # Step value (used for both INCREMENT and NUM_STEPS modes)
        self.stim_step_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_step_entry.grid(row=7, column=1, padx=5, pady=2)
        self.stim_step_entry.insert(0, "1.0")

        # Settling time
        ttk.Label(self.fr_stimulus, text="Settling Time (s):", style="TSpunkLabel.TLabel").grid(row=8, column=0, sticky='w', padx=5, pady=2)
        self.stim_settling_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_settling_entry.grid(row=8, column=1, padx=5, pady=2)
        self.stim_settling_entry.insert(0, "0.5")

        # Equipment channel
        ttk.Label(self.fr_stimulus, text="Channel:", style="TSpunkLabel.TLabel").grid(row=9, column=0, sticky='w', padx=5, pady=2)
        self.stim_ps_channel_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [1, 2]
        )
        self.stim_ps_channel_drop[0].grid(row=9, column=1, padx=5, pady=2)

        # === SECOND STIMULUS (Inner Loop) - Only shown when dual sweep enabled ===
        self.lbl_stim2_header = ttk.Label(self.fr_stimulus, text="--- Parameter 2 (Inner Loop) ---",
                                          font=('TkDefaultFont', 9, 'bold'))
        self.lbl_stim2_header.grid(row=2, column=2, columnspan=2, pady=5)

        # Stimulus 2 type dropdown
        self.lbl_stim2_type = ttk.Label(self.fr_stimulus, text="Stimulus Type:", style="TSpunkLabel.TLabel")
        self.lbl_stim2_type.grid(row=3, column=2, sticky='w', padx=5, pady=2)
        self.stimulus2_type_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [s.value for s in logger.StimulusType if s is not logger.StimulusType.NONE],
        )
        self.stimulus2_type_drop[0].grid(row=3, column=3, padx=5, pady=2)
        self.stimulus2_type_drop[1].set("FG Duty Cycle")  # Default to different param

        # Sweep mode 2 dropdown
        self.lbl_stim2_mode = ttk.Label(self.fr_stimulus, text="Sweep Mode:", style="TSpunkLabel.TLabel")
        self.lbl_stim2_mode.grid(row=4, column=2, sticky='w', padx=5, pady=2)
        self.sweep2_mode_drop = guih.generate_drop_down(
            self.fr_stimulus,
            ["Linear", "Logarithmic"]
        )
        self.sweep2_mode_drop[0].grid(row=4, column=3, padx=5, pady=2)

        # Start value 2
        self.lbl_stim2_start = ttk.Label(self.fr_stimulus, text="Start Value:", style="TSpunkLabel.TLabel")
        self.lbl_stim2_start.grid(row=5, column=2, sticky='w', padx=5, pady=2)
        self.stim2_start_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim2_start_entry.grid(row=5, column=3, padx=5, pady=2)
        self.stim2_start_entry.insert(0, "10.0")

        # Stop value 2
        self.lbl_stim2_stop = ttk.Label(self.fr_stimulus, text="Stop Value:", style="TSpunkLabel.TLabel")
        self.lbl_stim2_stop.grid(row=6, column=2, sticky='w', padx=5, pady=2)
        self.stim2_stop_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim2_stop_entry.grid(row=6, column=3, padx=5, pady=2)
        self.stim2_stop_entry.insert(0, "90.0")

        # Step mode dropdown (Increment OR Number of Steps)
        self.step2_mode_drop = guih.generate_drop_down(
            self.fr_stimulus,
            ["Increment size", "Number of Steps"],
        )
        self.step2_mode_drop[0].grid(row=7, column=2, stick='w', padx=5, pady=2)

        # Step value 2 (used for both INCREMENT and NUM_STEPS modes)
        self.stim2_step_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim2_step_entry.grid(row=7, column=3, padx=5, pady=2)
        self.stim2_step_entry.insert(0, "1.0")

        # PS Channel 2 (only relevant for PS voltage)
        self.lbl_stim2_channel = ttk.Label(self.fr_stimulus, text="Channel:", style="TSpunkLabel.TLabel")
        self.lbl_stim2_channel.grid(row=9, column=2, sticky='w', padx=5, pady=2)
        self.stim2_channel_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [1, 2]
        )
        self.stim2_channel_drop[0].grid(row=9, column=3, padx=5, pady=2)


        # Store second stimulus widgets for easy show/hide
        self.stim2_widgets = [
            self.lbl_stim2_header, self.lbl_stim2_type, self.stimulus2_type_drop[0],
            self.lbl_stim2_mode, self.sweep2_mode_drop[0],
            self.lbl_stim2_start, self.stim2_start_entry,
            self.lbl_stim2_stop, self.stim2_stop_entry,
            self.step2_mode_drop[0], self.stim2_step_entry,
            self.lbl_stim2_channel, self.stim2_channel_drop[0]
        ]

        # Initially hide stimulus controls
        self.toggle_stimulus()

    def init_fr_math(self):
        """Initialize the Math Columns configuration UI frame."""
        # Title
        ttk.Label(self.fr_math, text="Math Columns", style="TPinkLabel.TLabel").grid(
            row=0, column=0, columnspan=3, pady=5, padx=10)

        # Listbox showing configured columns
        self.math_listbox = tk.Listbox(self.fr_math, width=40, height=6,
                                       bg=self.theme_config["bg_light"],
                                       fg=self.theme_config["fg_light"],
                                       selectmode=tk.SINGLE)
        math_scrollbar = ttk.Scrollbar(self.fr_math, orient="vertical", command=self.math_listbox.yview)
        self.math_listbox.config(yscrollcommand=math_scrollbar.set)
        self.math_listbox.grid(row=1, column=0, columnspan=2, padx=(5, 0), pady=5, sticky="ns")
        math_scrollbar.grid(row=1, column=2, padx=(0, 5), pady=5, sticky="ns")

        # Add / Edit / Remove buttons
        btn_frame = tk.Frame(self.fr_math, bg=self.theme_config["dark_2"])
        btn_frame.grid(row=2, column=0, columnspan=3, pady=2)

        tk.Button(btn_frame, text="Add", width=6,
                  command=self._math_col_add,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Edit", width=6,
                  command=self._math_col_edit,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Remove", width=6,
                  command=self._math_col_remove,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)

        # Move Up / Move Down buttons
        order_frame = tk.Frame(self.fr_math, bg=self.theme_config["dark_2"])
        order_frame.grid(row=3, column=0, columnspan=3, pady=2)

        tk.Button(order_frame, text="Up", width=6,
                  command=self._math_col_move_up,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)
        tk.Button(order_frame, text="Down", width=6,
                  command=self._math_col_move_down,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)

        # Load / Save Preset buttons
        preset_frame = tk.Frame(self.fr_math, bg=self.theme_config["dark_2"])
        preset_frame.grid(row=4, column=0, columnspan=3, pady=2)

        tk.Button(preset_frame, text="Load Preset", width=10,
                  command=self._math_load_preset,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)
        tk.Button(preset_frame, text="Save Preset", width=10,
                  command=self._math_save_preset,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).pack(side="left", padx=2)

        # Summary label
        self.lbl_math_summary = ttk.Label(self.fr_math, text="0 math columns configured",
                                          style="TSpunkLabel.TLabel")
        self.lbl_math_summary.grid(row=5, column=0, columnspan=3, pady=2)

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
            if self.cc.get_fg_status():
                self.fg_status.set_color(self.theme_config["success"])
            else:
                self.fg_status.set_color(self.theme_config["error"])
            if self.cc.get_osc_status():
                self.osc_status.set_color(self.theme_config["success"])
            else:
                self.osc_status.set_color(self.theme_config["error"])


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################
    # NOTE: some of these are linked to Checkbuttons (instead of Buttons)

    def toggle_graph_options(self):
        """Show/hide graph sub-options based on Graph checkbox"""
        if self.var_graph_data.get():
            self.chk_3d_plot.grid()
            self.chk_subplots.grid()
        else:
            self.chk_3d_plot.grid_remove()
            self.chk_subplots.grid_remove()
            self.var_3d_plot.set(0)

    def toggle_use_ser(self):
        if self.var_use_ser.get():
            self.lbl_use_ser.grid()
            self.serial_log_params.grid()
        else:
            self.lbl_use_ser.grid_remove()
            self.serial_log_params.grid_remove()

    def toggle_use_ps(self):
        if self.var_use_ps.get():
            self.lbl_rec_ps_channel.grid()
            self.rec_ps_channel_drop[0].grid()
        else:
            self.lbl_rec_ps_channel.grid_remove()
            self.rec_ps_channel_drop[0].grid_remove()

    def toggle_use_osc(self):
        if self.var_use_osc.get():
            self.btn_osc_config.config(state=tk.NORMAL)
        else:
            self.btn_osc_config.config(state=tk.DISABLED)

    def toggle_live_plot_options(self):
        if self.var_live_plot.get():
            self.lbl_buf_size.grid()
            self.entry_buf_size.grid()
            self.lbl_time_window.grid()
            self.btn_export_html.grid()
            self._update_time_window_label()
        else:
            self.lbl_buf_size.grid_remove()
            self.entry_buf_size.grid_remove()
            self.lbl_time_window.grid_remove()
            self.btn_export_html.grid_remove()

    def _update_time_window_label(self):
        """Compute and display estimated time window from buffer size and sample rate."""
        try:
            buf_size = int(self.entry_buf_size.get())
            interval = self._get_sample_interval()
        except (ValueError, TypeError):
            self.lbl_time_window.config(text="")
            return

        total_secs = buf_size * interval

        # Format nicely
        if total_secs < 60:
            time_str = f"{total_secs:.1f}s"
        elif total_secs < 3600:
            time_str = f"{total_secs / 60:.1f} min"
        elif total_secs < 86400:
            time_str = f"{total_secs / 3600:.1f} hrs"
        else:
            time_str = f"{total_secs / 86400:.1f} days"

        self.lbl_time_window.config(text=f"~{time_str} window ({buf_size} samples)")

    def open_osc_config_dialog(self):
        """Open a modal popup to configure oscilloscope measurement selections."""
        dialog = tk.Toplevel(self)
        dialog.title("Oscilloscope Recording Configuration")
        dialog.configure(bg=self.theme_config["bg_light"])
        dialog.grab_set()

        # Title
        ttk.Label(dialog, text="Select Measurements per Channel",
                  style="TPinkLabel.TLabel",
                  font=(self.theme_config["font"]["family"], 12, "bold")).grid(
            row=0, column=0, columnspan=5, pady=10, padx=10)

        # Header row
        ttk.Label(dialog, text="Measurement", style="TLabel", anchor='w', width=14).grid(row=1, column=0, padx=5, pady=2)
        for ch in range(1, 5):
            ttk.Label(dialog, text=f"CH{ch}", style="TLabel").grid(row=1, column=ch, padx=5, pady=2)

        # Create checkbox grid: osc_vars[meas_name][ch] = IntVar
        self._osc_dialog_vars = {}
        for row_idx, meas_name in enumerate(logger.AVAILABLE_OSC_MEASUREMENTS, start=2):
            label = logger.OSC_MEASUREMENT_LABELS.get(meas_name, meas_name)
            ttk.Label(dialog, text=label, style="TLabel", anchor='w', width=14).grid(
                row=row_idx, column=0, padx=5, pady=1, sticky='w')
            self._osc_dialog_vars[meas_name] = {}
            for ch in range(1, 5):
                var = tk.IntVar()
                # Pre-check if we have an existing config
                if (self.osc_record_config and
                        ch in self.osc_record_config.channels and
                        meas_name in self.osc_record_config.channels[ch]):
                    var.set(1)
                ttk.Checkbutton(dialog, variable=var, onvalue=1, offvalue=0).grid(
                    row=row_idx, column=ch, padx=5, pady=1)
                self._osc_dialog_vars[meas_name][ch] = var

        # "Select All" buttons per channel
        btn_row = 2 + len(logger.AVAILABLE_OSC_MEASUREMENTS)
        for ch in range(1, 5):
            tk.Button(dialog, text=f"All CH{ch}",
                      command=lambda c=ch: self._osc_select_all_channel(c),
                      fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).grid(
                row=btn_row, column=ch, padx=5, pady=5)

        # OK / Cancel buttons
        btn_frame = tk.Frame(dialog, bg=self.theme_config["bg_light"])
        btn_frame.grid(row=btn_row + 1, column=0, columnspan=5, pady=10)
        tk.Button(btn_frame, text="OK", width=10,
                  command=lambda: self._osc_dialog_ok(dialog),
                  bg=self.theme_config["success"], fg=self.theme_config["fg_light"]).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Cancel", width=10,
                  command=dialog.destroy,
                  bg=self.theme_config["error"], fg=self.theme_config["fg_light"]).pack(side="left", padx=10)

    def _osc_select_all_channel(self, ch):
        """Toggle all measurement checkboxes for a given channel."""
        # If any are unchecked, check all; otherwise uncheck all
        all_checked = all(self._osc_dialog_vars[m][ch].get() for m in logger.AVAILABLE_OSC_MEASUREMENTS)
        new_val = 0 if all_checked else 1
        for meas_name in logger.AVAILABLE_OSC_MEASUREMENTS:
            self._osc_dialog_vars[meas_name][ch].set(new_val)

    def _osc_dialog_ok(self, dialog):
        """Build OscRecordConfig from dialog checkboxes and close."""
        channels = {}
        for meas_name in logger.AVAILABLE_OSC_MEASUREMENTS:
            for ch in range(1, 5):
                if self._osc_dialog_vars[meas_name][ch].get():
                    if ch not in channels:
                        channels[ch] = []
                    channels[ch].append(meas_name)
        self.osc_record_config = logger.OscRecordConfig(channels=channels)
        dialog.destroy()

    def toggle_stimulus(self):
        if self.var_use_stimulus.get():
            # Show all stimulus configuration widgets
            for widget in self.fr_stimulus.winfo_children():
                if widget != self.var_use_stimulus:  # Don't hide the checkbox itself
                    widget.grid()
            # Update dual stimulus visibility
            self.toggle_dual_stimulus()
        else:
            # Hide all stimulus configuration widgets except title and checkbox
            for widget in self.fr_stimulus.winfo_children():
                widget_info = widget.grid_info()
                if widget_info.get('row', 0) > 1:  # Keep row 0 (title) and row 1 (checkbox)
                    widget.grid_remove()

    def toggle_dual_stimulus(self):
        """Show/hide second stimulus parameter controls"""
        if self.var_use_dual_stimulus.get() and self.var_use_stimulus.get():
            # Show second stimulus widgets
            for widget in self.stim2_widgets:
                widget.grid()
        else:
            # Hide second stimulus widgets
            for widget in self.stim2_widgets:
                widget.grid_remove()

    # ── Math column actions ───────────────────────────────────────────────────

    def _refresh_math_listbox(self):
        """Repopulate the math listbox from self.math_config."""
        self.math_listbox.delete(0, tk.END)
        for col in self.math_config.columns:
            self.math_listbox.insert(tk.END, f"{col.name} = {col.expression}")
        n = len(self.math_config.columns)
        self.lbl_math_summary.config(text=f"{n} math column{'s' if n != 1 else ''} configured")

    def _math_col_add(self):
        self._open_math_col_dialog()

    def _math_col_edit(self):
        sel = self.math_listbox.curselection()
        if not sel:
            guih.alert_user("No selection", "Select a math column to edit.", "warning")
            return
        self._open_math_col_dialog(edit_index=sel[0])

    def _math_col_remove(self):
        sel = self.math_listbox.curselection()
        if not sel:
            guih.alert_user("No selection", "Select a math column to remove.", "warning")
            return
        del self.math_config.columns[sel[0]]
        self._refresh_math_listbox()

    def _math_col_move_up(self):
        sel = self.math_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.math_config.columns[i - 1], self.math_config.columns[i] = (
            self.math_config.columns[i], self.math_config.columns[i - 1])
        self._refresh_math_listbox()
        self.math_listbox.selection_set(i - 1)

    def _math_col_move_down(self):
        sel = self.math_listbox.curselection()
        if not sel or sel[0] >= len(self.math_config.columns) - 1:
            return
        i = sel[0]
        self.math_config.columns[i], self.math_config.columns[i + 1] = (
            self.math_config.columns[i + 1], self.math_config.columns[i])
        self._refresh_math_listbox()
        self.math_listbox.selection_set(i + 1)

    def _math_load_preset(self):
        filepath = filedialog.askopenfilename(
            initialdir=self.math_preset_dir,
            title="Load Math Preset",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return
        try:
            self.math_config = load_math_config(filepath)
            self._refresh_math_listbox()
            self.prompt.print(f"Loaded math preset: {os.path.basename(filepath)}")
        except Exception as e:
            guih.alert_user("Load Error", str(e), "error")

    def _math_save_preset(self):
        if self.math_config.is_empty():
            guih.alert_user("Nothing to save", "No math columns configured.", "warning")
            return
        os.makedirs(self.math_preset_dir, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            initialdir=self.math_preset_dir,
            title="Save Math Preset",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return
        try:
            save_math_config(self.math_config, filepath)
            self.prompt.print(f"Saved math preset: {os.path.basename(filepath)}")
        except Exception as e:
            guih.alert_user("Save Error", str(e), "error")

    def _open_math_col_dialog(self, edit_index=None):
        """Modal dialog to add or edit a math column."""
        dialog = tk.Toplevel(self)
        dialog.title("Edit Math Column" if edit_index is not None else "Add Math Column")
        dialog.configure(bg=self.theme_config["bg_light"])
        dialog.grab_set()

        existing = self.math_config.columns[edit_index] if edit_index is not None else None

        ttk.Label(dialog, text="Name:", style="TLabel").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_name = tk.Entry(dialog, width=30)
        entry_name.grid(row=0, column=1, padx=5, pady=5)
        if existing:
            entry_name.insert(0, existing.name)

        ttk.Label(dialog, text="Expression:", style="TLabel").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        entry_expr = tk.Entry(dialog, width=30)
        entry_expr.grid(row=1, column=1, padx=5, pady=5)
        if existing:
            entry_expr.insert(0, existing.expression)

        ttk.Label(dialog, text="Description:", style="TLabel").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_desc = tk.Entry(dialog, width=30)
        entry_desc.grid(row=2, column=1, padx=5, pady=5)
        if existing:
            entry_desc.insert(0, existing.description)

        # Available variables hint
        hint_text = ("Available variables: Time, DMM_Meas1, PS_Vset1, PS_Vmeas1, PS_Imeas1,\n"
                     "PS_Vset2, PS_Vmeas2, PS_Imeas2, FG_Freq, OSC_CH*_*, prior math cols\n"
                     "Serial columns: use names you entered in 'Serial columns' field (e.g. col1, col2)\n"
                     "Functions: abs, round, min, max, sqrt, log, log10, exp, pow\n"
                     "Constants: pi, e")
        ttk.Label(dialog, text=hint_text, style="TLabel", wraplength=350).grid(
            row=3, column=0, columnspan=2, padx=5, pady=5)

        def on_ok():
            name = entry_name.get().strip()
            expr = entry_expr.get().strip()
            desc = entry_desc.get().strip()
            if not name or not expr:
                guih.alert_user("Missing fields", "Name and Expression are required.", "warning")
                return
            # Disallow spaces in name (used as CSV header / variable name)
            if " " in name:
                guih.alert_user("Invalid name", "Column name must not contain spaces.", "warning")
                return
            col = MathColumn(name=name, expression=expr, description=desc)
            if edit_index is not None:
                self.math_config.columns[edit_index] = col
            else:
                self.math_config.columns.append(col)
            self._refresh_math_listbox()
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self.theme_config["bg_light"])
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="OK", width=10, command=on_ok,
                  bg=self.theme_config["success"], fg=self.theme_config["fg_light"]).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Cancel", width=10, command=dialog.destroy,
                  bg=self.theme_config["error"], fg=self.theme_config["fg_light"]).pack(side="left", padx=10)

    def _apply_math_columns(self, row):
        """Evaluate math columns and merge results into the row dict."""
        if self.math_evaluator is not None:
            results = self.math_evaluator.evaluate_row(row)
            row.update(results)

    # ── Recording functions ───────────────────────────────────────────────────

    def start_record(self):
        # Prevent double-start
        if self._record_thread is not None and self._record_thread.is_alive():
            self.prompt.print("Recording is already in progress!", print_type="warning")
            return

        # Organize parameters first
        self.organize_record_params()
        self.set_record_speed()
        self.record_status = False
        self.recorded_data = []
        self.recCnt = 0

        # Check Serial if requested
        if self.record_config.use_ser:
            if not self.cc.get_ser_status():
                guih.alert_user("Can't start record!", "Serial connection is not valid!", "error")
                return

        # Check DMM if requested
        if self.record_config.use_dmm:
            if not self.cc.get_dmm_status():
                guih.alert_user("Can't start record!", "DMM connection is not valid!", "error")
                return

        # Check Power Supply if requested
        if self.record_config.use_ps:
            if not self.cc.get_ps_status():
                guih.alert_user("Can't start record!", "Power Supply connection is not valid!", "error")
                return

        # Check Function Generator if requested
        if self.record_config.use_fg:
            if not self.cc.get_fg_status():
                guih.alert_user("Can't start record!", "Function Generator connection is not valid!", "error")
                return

        # Check Oscilloscope if requested
        if self.record_config.use_osc:
            if not self.cc.get_osc_status():
                guih.alert_user("Can't start record!", "Oscilloscope connection is not valid!", "error")
                return
            if not self.osc_record_config or not self.osc_record_config.has_measurements():
                guih.alert_user("Can't start record!", "No oscilloscope measurements configured. Click 'Configure OSC...'", "warning")
                return

        # Check stimulus configuration if enabled
        if self.var_use_stimulus.get():
            if isinstance(self.stimulus_config, logger.DualStimulusConfig):
                # Check both outer and inner loop requirements
                for loop_config in [self.stimulus_config.outer_loop, self.stimulus_config.inner_loop]:
                    stim_type = loop_config.stimulus_type
                    if stim_type == logger.StimulusType.PS_VOLTAGE:
                        if not self.cc.get_ps_status():
                            guih.alert_user("Can't start record!", "PS stimulus requires Power Supply connection!", "error")
                            return
                    elif stim_type in [logger.StimulusType.FG_FREQUENCY, logger.StimulusType.FG_DUTY_CYCLE]:
                        if not self.cc.get_fg_status():
                            guih.alert_user("Can't start record!", "FG stimulus requires Function Generator connection!", "error")
                            return
            else:
                # Single stimulus check
                stim_type = self.stimulus_config.stimulus_type
                if stim_type == logger.StimulusType.PS_VOLTAGE:
                    if not self.cc.get_ps_status():
                        guih.alert_user("Can't start record!", "PS stimulus requires Power Supply connection!", "error")
                        return
                elif stim_type in [logger.StimulusType.FG_FREQUENCY, logger.StimulusType.FG_DUTY_CYCLE]:
                    if not self.cc.get_fg_status():
                        guih.alert_user("Can't start record!", "FG stimulus requires Function Generator connection!", "error")
                        return

        # Validate that at least one instrument OR stimulus config is selected
        has_instrument = (self.record_config.use_ser or
                         self.record_config.use_dmm or
                         self.record_config.use_ps or
                         self.record_config.use_fg or
                         self.record_config.use_osc)
        has_stimulus = self.var_use_stimulus.get()

        if not has_instrument and not has_stimulus:
            guih.alert_user("Can't start record!",
                          "Please select at least one instrument to record OR enable stimulus mode",
                          "warning")
            return

        # Validate math columns (if any configured)
        if not self.math_config.is_empty():
            headers = logger.build_headers(self.record_config, self.stimulus_config)
            self.math_evaluator = MathEvaluator(self.math_config)
            valid, err = self.math_evaluator.validate(headers)
            if not valid:
                guih.alert_user("Math Column Error", err, "error")
                self.math_evaluator = None
                return
            self.prompt.print(f"Math columns validated: {len(self.math_config.columns)} column(s)")
        else:
            self.math_evaluator = None

        # If we reach here, all requested instruments are ready and user has selected at least 1 instrument or stimulus
        if self.var_save_data.get():
            logger.start_recording(self.csvh)
        self.record_status = True
        self.cc.recording = True  # Signal to ClassController that recording is active
        self.prompt.print(f"Starting recording at: {self.data_dir}{self.recName}")
        self.prompt.print(f"Recording every {self.record_speed} seconds ...")

        self.btn_pause.config(state=tk.NORMAL, text="Pause", command=lambda: self.pause_record())

        # Start live plot if requested
        if self.var_live_plot.get():
            self._start_live_plot()

        self._record_thread = guic.StoppableThread(target=self.thread_record)
        self._record_thread.start()

    def stop_record(self):
        self._paused = False
        self.record_status = False
        if self._record_thread is not None:
            self._record_thread.stop()
        self.cc.recording = False  # Signal to ClassController that recording has stopped
        self.btn_pause.config(state=tk.DISABLED, text="Pause", command=lambda: self.pause_record())
        self.prompt.print("Stopped data record!")

        # plot data if requested
        if self.record_config.make_graph:
            self.final_plot()

    def pause_record(self):
        """Pause recording — stops the thread but keeps CSV and accumulated data intact."""
        self._paused = True
        self.record_status = False
        if self._record_thread is not None:
            self._record_thread.stop()
        self.cc.recording = False
        self.btn_pause.config(text="Resume", command=lambda: self.resume_record())
        self.prompt.print("Recording paused")

    def resume_record(self):
        """Resume recording from paused state — continues writing to the existing CSV."""
        if not self._paused:
            return
        self._paused = False
        self.record_status = True
        self.cc.recording = True
        self.btn_pause.config(text="Pause", command=lambda: self.pause_record())
        self.prompt.print(f"Resuming recording ...")
        self._record_thread = guic.StoppableThread(target=self.thread_record)
        self._record_thread.start()

    def export_live_plot_html(self):
        """Export the recorded session data as a self-contained Plotly HTML file."""
        if not self.recorded_data:
            self.prompt.print("No data to export yet", print_type="warning")
            return

        # Default filename derived from CSV name (or timestamped fallback)
        if self.recName:
            default_name = os.path.splitext(self.recName)[0] + ".html"
        else:
            default_name = f"live_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        filepath = filedialog.asksaveasfilename(
            initialdir=self.data_dir,
            initialfile=default_name,
            title="Export HTML Plot",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if not filepath:
            return
        html_path = filepath

        # Determine x-key and channels matching the live plot config
        if self.stimulus_config and self.stimulus_config.enabled:
            if self.stimulus_config.is_dual:
                stim_type = self.stimulus_config.outer_loop.stimulus_type
            else:
                stim_type = self.stimulus_config.stimulus_type
            x_key = logger.get_stimulus_column_name(stim_type)
            title = "Stimulus Sweep — Exported"
        else:
            x_key = logger.COL_TIME
            title = "Live Plot — Exported"

        channels = []
        if self.record_config.use_dmm:
            channels.append(logger.COL_DMM_MEAS1)
        if self.record_config.use_ps:
            channels.extend([logger.COL_PS_VMEAS1, logger.COL_PS_IMEAS1])
        if self.record_config.use_osc and self.record_config.osc_config:
            channels += logger.build_osc_columns(self.record_config.osc_config)

        plotter.export_recorded_data_html(self.recorded_data, x_key, channels, title, html_path)
        self.prompt.print(f"Exported HTML to: {html_path}")

    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    def set_record_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    def _get_sample_interval(self):
        """Return the sample interval in seconds from the rate entry + unit dropdown."""
        UNIT_MULTIPLIERS = {'s': 1, 'min': 60, 'hr': 3600}
        val = float(self.entry_sample_val.get())
        unit = self.RecSpdUnitVal.get()
        return val * UNIT_MULTIPLIERS.get(unit, 1)

    def set_record_speed(self):
        self.record_speed = self._get_sample_interval()

    def set_stimulus(self):
        stimulus_type_str = self.stimulus_type_drop[1].get()
        sweep_mode_str = self.sweep_mode_drop[1].get()
        step_mode_str = self.step_mode_drop[1].get()

        try:
            if self.var_use_dual_stimulus.get():
                # === DUAL STIMULUS MODE ===
                # only need to get these values from GUI elements in dual-stimulus mode
                stimulus2_type_str = self.stimulus2_type_drop[1].get()
                sweep2_mode_str = self.sweep2_mode_drop[1].get()
                step2_mode_str = self.step2_mode_drop[1].get()

                outer_config = logger.StimulusConfig(
                    enabled=True,
                    stimulus_type=logger.StimulusType(stimulus_type_str),
                    sweep_mode=logger.SweepMode(sweep_mode_str),
                    step_mode=logger.StepMode(step_mode_str),
                    start_value=float(self.stim_start_entry.get()),
                    stop_value=float(self.stim_stop_entry.get()),
                    step_value=float(self.stim_step_entry.get()),
                    settling_time=float(self.stim_settling_entry.get()),
                    channel=int(self.stim_ps_channel_drop[1].get())
                )

                # Create inner loop config
                inner_config = logger.StimulusConfig(
                    enabled=True,
                    stimulus_type=logger.StimulusType(stimulus2_type_str),
                    sweep_mode=logger.SweepMode(sweep2_mode_str),
                    step_mode=logger.StepMode(step2_mode_str),
                    start_value=float(self.stim2_start_entry.get()),
                    stop_value=float(self.stim2_stop_entry.get()),
                    step_value=float(self.stim2_step_entry.get()),
                    settling_time=0.0,  # Inner loop uses outer loop's settling time (applied in _thread_record_dual_stimulus)
                    channel=int(self.stim2_channel_drop[1].get())
                )

                # Create dual stimulus config
                self.stimulus_config = logger.DualStimulusConfig(
                    enabled=True,
                    outer_loop=outer_config,
                    inner_loop=inner_config
                )

                # Validate the config
                valid, error_msg = self.stimulus_config.validate()
                if not valid:
                    guih.alert_user("Invalid Dual Stimulus Config", error_msg, "error")
                    raise ValueError(error_msg)

                # Create the stimulus generator
                self.stimulus_generator = logger.DualStimulusGenerator(self.stimulus_config)
                self.prompt.print(f"Dual stimulus sweep configured: {len(self.stimulus_generator)} total steps")
                self.prompt.print(f"  Outer loop: {len(self.stimulus_generator.outer_gen)} steps")
                self.prompt.print(f"  Inner loop: {len(self.stimulus_generator.inner_gen)} steps")

            else:
                # === SINGLE STIMULUS MODE ===
                self.stimulus_config = logger.StimulusConfig(
                    enabled=True,
                    stimulus_type=logger.StimulusType(stimulus_type_str),
                    sweep_mode=logger.SweepMode(sweep_mode_str),
                    step_mode=logger.StepMode(step_mode_str),
                    start_value=float(self.stim_start_entry.get()),
                    stop_value=float(self.stim_stop_entry.get()),
                    step_value=float(self.stim_step_entry.get()),
                    settling_time=float(self.stim_settling_entry.get()),
                    channel=int(self.stim_ps_channel_drop[1].get())
                )

                # Validate the config
                valid, error_msg = self.stimulus_config.validate()
                if not valid:
                    guih.alert_user("Invalid Stimulus Config", error_msg, "error")
                    raise ValueError(error_msg)

                # Create the stimulus generator
                self.stimulus_generator = logger.StimulusGenerator(self.stimulus_config)
                self.prompt.print(f"Stimulus sweep configured: {len(self.stimulus_generator)} steps")

        except ValueError as e:
            guih.alert_user("Invalid Stimulus Values", str(e), "error")
            raise

    def organize_record_params(self):
        # get all needed GUI elements
        prefix = path_helper.get_logger_prefix()
        ext_text = self.output_file_name.get("1.0", "end").strip("\n")

        # create recording config
        self.record_config = logger.create_record_config(
            self.var_use_ser.get(),
            self.var_use_dmm.get(),
            self.var_use_ps.get(),
            self.var_use_fg.get(),
            self.rec_ps_channel_drop[1].get(),
            self.serial_log_params.get("1.0", "end").strip(),
            self.var_graph_data.get(),
            use_osc=self.var_use_osc.get(),
            osc_config=self.osc_record_config
        )
        _logger.debug(self.record_config.pretty())

        # create stimulus config if enabled
        if self.var_use_stimulus.get():
            self.set_stimulus()
        else:
            self.stimulus_config = None
            self.stimulus_generator = None

        # setup recording (only create CSV file if saving)
        math_cfg = self.math_config if not self.math_config.is_empty() else None
        if self.var_save_data.get():
            self.recName, self.csvh = logger.setup_recording(
                    self.data_dir,
                    prefix,
                    ext_text,
                    self.record_config,
                    self.stimulus_config,
                    math_config=math_cfg
            )
        else:
            self.recName = ""
            self.csvh = None

    def thread_record(self):
        # Check if stimulus-based recording
        if self.stimulus_config and self.stimulus_config.enabled:
            self.start_record_stimulus()
        elif self.record_config.use_ser:
            self.thread_record_serial()
        else:
            self.thread_record_timed()

    def thread_record_timed(self):
        while self.record_status:
            t_start = time.monotonic()

            # Build a row of data based on what user wants
            row = self._collect_data_row()
            self._apply_math_columns(row)

            # save row (locally and to sinks)
            self.recorded_data.append(row)
            self._save_data_row(row)

            # Update record counter and UI (thread-safe)
            self.recCnt += 1
            cnt = self.recCnt
            self.after(0, lambda n=cnt: self.labelRNums.config(text=f'#{n:7d}'))

            # Deadline-based sleep: only sleep the remaining time in the interval
            elapsed = time.monotonic() - t_start
            remaining = self.record_speed - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def start_record_stimulus(self):
        self.prompt.print(f"Starting stimulus sweep with {len(self.stimulus_generator)} steps")

        # turn on power supply if being used as a stimulus
        if self.stimulus_config.uses_ps():
            self.cc.ps_service.output_on(self.stimulus_config.channel)

        # start stimulus thread
        try:
            if self.stimulus_config.is_dual:
                self._thread_record_dual_stimulus()
            else:
                self._thread_record_single_stimulus()

            # Sweep complete
            if self.record_status:
                self.prompt.print("Stimulus sweep completed!")
                self.stop_record()
                return

        except Exception as e:
            self.prompt.print(f"Error during stimulus sweep: {e}")
            guih.alert_user("Error during stimulus sweep", str(e), "error")
            self.stop_record()
            raise e

    def thread_record_serial(self):
        """Serial-triggered data collection: collects test equipment data each time serial line is received"""
        self.prompt.print("Starting serial recording thread ...")
        while self.record_status:
            try:
                # Wait for serial data (blocks until \n is received)
                serial_data = self.cc.ser.read_line().decode('utf-8').rstrip('\r\n')

                # Collect all data using shared helper
                row = self._collect_data_row(serial_data=serial_data)
                self._apply_math_columns(row)

                # Save row (locally and to sinks)
                self.recorded_data.append(row)
                self._save_data_row(row)

                # Update record counter and UI (thread-safe)
                self.recCnt += 1
                cnt = self.recCnt
                self.after(0, lambda n=cnt: self.labelRNums.config(text=f'#{n:7d}'))

            except Exception as e:
                self.prompt.print(f"Error in serial-triggered recording: {e}")
                self.record_status = False
                guih.alert_user("Serial Recording Error", str(e), "error")
                break

    def _thread_record_single_stimulus(self):
        """Single parameter stimulus sweep"""
        for step_num, stimulus_value in enumerate(self.stimulus_generator, 1):
            if not self.record_status:
                break

            # Apply the stimulus
            self._apply_stimulus(stimulus_value)

            # Wait for settling
            time.sleep(self.stimulus_config.settling_time)

            # Collect data
            row = self._collect_data_row()

            # Add stimulus value to the row (use actual parameter name)
            param_name = logger.get_stimulus_column_name(self.stimulus_config.stimulus_type)
            row[param_name] = stimulus_value
            row[logger.COL_STIMULUS_STEP] = str(step_num)
            self._apply_math_columns(row)

            # Save row (locally and to sinks)
            self.recorded_data.append(row)
            self._save_data_row(row)

            # Update progress (thread-safe)
            self.recCnt += 1
            progress_text = f'Step {step_num}/{len(self.stimulus_generator)}'
            self.after(0, lambda t=progress_text: self.labelRNums.config(text=t))
            self.prompt.print(f"Step {step_num}: Stimulus={stimulus_value:.3f}")

    def _thread_record_dual_stimulus(self):
        """Dual parameter stimulus sweep (nested loops)"""
        for step_num, (outer_value, inner_value) in enumerate(self.stimulus_generator, 1):
            if not self.record_status:
                break

            # Apply both stimuli
            self._apply_stimulus(outer_value, dual=1)
            self._apply_stimulus(inner_value, dual=2)
            self.prompt.print(f"Step {step_num}: Outer={outer_value:.3f}, Inner={inner_value:.3f}")

            # Wait for settling (use outer loop settling time)
            time.sleep(self.stimulus_config.outer_loop.settling_time)

            # Collect data
            row = self._collect_data_row()

            # Add stimulus values to the row (use actual parameter names)
            outer_name = logger.get_stimulus_column_name(self.stimulus_config.outer_loop.stimulus_type)
            inner_name = logger.get_stimulus_column_name(self.stimulus_config.inner_loop.stimulus_type)
            row[outer_name] = outer_value
            row[inner_name] = inner_value
            row[logger.COL_STIMULUS_STEP] = step_num
            self._apply_math_columns(row)

            # Save row (locally and to sinks)
            self.recorded_data.append(row)
            self._save_data_row(row)

            # Update progress (thread-safe)
            self.recCnt += 1
            progress_text = f'Step {step_num}/{len(self.stimulus_generator)}'
            self.after(0, lambda t=progress_text: self.labelRNums.config(text=t))

    def _collect_data_row(self, serial_data=None):
        row = {logger.COL_TIME: datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}

        # Serial data if requested
        if self.record_config.use_ser:
            if serial_data is None:
                raw = self.cc.ser.read_line()
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8').rstrip('\r\n')
                serial_data = raw
            serial_cols = logger.parse_serial_params(self.record_config.serial_params)
            if serial_cols:
                parts = serial_data.split(",")
                for i, col in enumerate(serial_cols):
                    row[col] = parts[i].strip() if i < len(parts) else ""
            else:
                row[logger.COL_SERIAL] = serial_data

        # DMM data if requested
        if self.record_config.use_dmm:
            val, _ = self.cc.dmm_service.read_value()
            row[logger.COL_DMM_MEAS1] = val if val is not None else "ERROR"

        # Power Supply data if requested
        if self.record_config.use_ps:
            row[logger.COL_PS_VSET1] = self.cc.ps_service.read_set_voltage(1) or "ERROR"
            row[logger.COL_PS_VMEAS1] = self.cc.ps_service.read_voltage(1) or "ERROR"
            row[logger.COL_PS_IMEAS1] = self.cc.ps_service.read_current(1) or "ERROR"
            if self.record_config.ps_channel == 2:
                row[logger.COL_PS_VSET2] = self.cc.ps_service.read_set_voltage(2) or "ERROR"
                row[logger.COL_PS_VMEAS2] = self.cc.ps_service.read_voltage(2) or "ERROR"
                row[logger.COL_PS_IMEAS2] = self.cc.ps_service.read_current(2) or "ERROR"

        # Function Generator data if requested
        if self.record_config.use_fg:
            row[logger.COL_FG_FREQ] = self.cc.fg_service.get_frequency() or "ERROR"
            row[logger.COL_FG_WAVEFORM] = self.cc.fg_service.get_shape() or "ERROR"

        # Oscilloscope data if requested
        if self.record_config.use_osc and self.record_config.osc_config:
            try:
                osc_data = logger.collect_osc_measurements(self.cc.osc, self.record_config.osc_config)
                row.update(osc_data)
            except Exception:
                for col in logger.build_osc_headers(self.record_config.osc_config):
                    row[col] = "ERROR"

        return row

    def _apply_stimulus(self, value, dual=None):
        """Apply the stimulus value to the appropriate instrument"""
        if dual is None:
            loop_config = self.stimulus_config
        elif dual == 1:
            loop_config = self.stimulus_config.outer_loop
        elif dual == 2:
            loop_config = self.stimulus_config.inner_loop
        else:
            return

        if loop_config.stimulus_type == logger.StimulusType.PS_VOLTAGE:
            self.cc.ps_service.set_voltage(loop_config.channel, value)

        elif loop_config.stimulus_type == logger.StimulusType.FG_FREQUENCY:
            self.cc.fg_service.set_frequency(value)

        elif loop_config.stimulus_type == logger.StimulusType.FG_DUTY_CYCLE:
            self.cc.fg_service.set_duty(value)

        else:
            raise ValueError(f"Unknown stimulus type: {loop_config.stimulus_type}")

    def _save_data_row(self, row):
        if self.var_save_data.get() and self.csvh:
            self.csvh.add_row_from_dict(row)
        if self.bus is not None:
            self.bus.put(row)

    ##############################################################################
    ####      PLOTTING FUNCTIONS        ##########################################
    ##############################################################################

    def final_plot(self):
        df = pd.DataFrame(self.recorded_data)

        # build list of y channels: (column_key, label)
        y_channels = []
        if self.record_config.use_dmm:
            y_channels.append((logger.COL_DMM_MEAS1, "DMM (V)"))
        if self.record_config.use_ps:
            y_channels.append((logger.COL_PS_VMEAS1, "PS Voltage (V)"))
            y_channels.append((logger.COL_PS_IMEAS1, "PS Current (A)"))
        if self.record_config.use_osc and self.record_config.osc_config:
            for col in logger.build_osc_columns(self.record_config.osc_config):
                y_channels.append((col, col))

        if not y_channels:
            return

        # determine x-axis
        if self.stimulus_config and self.stimulus_config.enabled:
            if self.stimulus_config.is_dual:
                stim_type = self.stimulus_config.outer_loop.stimulus_type
            else:
                stim_type = self.stimulus_config.stimulus_type
            x_var = logger.get_stimulus_column_name(stim_type)
            xlabel = logger.get_stimulus_label(stim_type)
            title = "Stimulus based logging"
        else:
            x_var = logger.COL_TIME
            xlabel = "Time"
            title = "Time based logging"

        # dual stimulus special plots (3D or grouped)
        if self.stimulus_config and self.stimulus_config.enabled and self.stimulus_config.is_dual:
            outer_type = self.stimulus_config.outer_loop.stimulus_type
            inner_type = self.stimulus_config.inner_loop.stimulus_type
            outer_col = logger.get_stimulus_column_name(outer_type)
            inner_col = logger.get_stimulus_column_name(inner_type)
            outer_label = logger.get_stimulus_label(outer_type)
            inner_label = logger.get_stimulus_label(inner_type)

            for y_var, ylabel in y_channels:
                if self.var_3d_plot.get():
                    plotter.plot_3d_from_df(
                        df,
                        x_var=outer_col,
                        y_var=inner_col,
                        z_var=y_var,
                        xlabel=outer_label,
                        ylabel=inner_label,
                        zlabel=ylabel,
                        title=f"{outer_label} vs {inner_label} vs {ylabel}",
                    )
                else:
                    plotter.plot_grouped(
                        df,
                        x_var=outer_col,
                        y_var=y_var,
                        group_var=inner_col,
                        xlabel=outer_label,
                        ylabel=ylabel,
                        title=f"{outer_label} vs {ylabel} (grouped by {inner_label})",
                    )
            return

        # single channel: simple plot
        if len(y_channels) == 1:
            y_var, ylabel = y_channels[0]
            plotter.plot(df[x_var], df[y_var], xlabel=xlabel, ylabel=ylabel, title=title)
            return

        # multiple channels
        if self.var_subplots.get():
            # stacked subplots, shared x-axis
            channels = [(df[y_var], ylabel) for y_var, ylabel in y_channels]
            plotter.plot_subplots(df[x_var], channels, xlabel=xlabel, title=title)
        else:
            # separate plot windows
            for y_var, ylabel in y_channels:
                plotter.plot(df[x_var], df[y_var], xlabel=xlabel, ylabel=ylabel, title=f"{title} - {ylabel}")

    def _start_live_plot(self):
        """Start the Dash live plot server, or update its config if already running."""
        try:
            buf_size = int(self.entry_buf_size.get())
        except ValueError:
            buf_size = 3000
        self.bus = Queue(maxsize=buf_size + 1000)

        # Determine x-axis: stimulus value if in stimulus mode, otherwise time
        if self.stimulus_config and self.stimulus_config.enabled:
            if self.stimulus_config.is_dual:
                stim_type = self.stimulus_config.outer_loop.stimulus_type
            else:
                stim_type = self.stimulus_config.stimulus_type
            x_key = logger.get_stimulus_column_name(stim_type)
            x_label = logger.get_stimulus_label(stim_type)
            title = "Stimulus Sweep"
        else:
            x_key = logger.COL_TIME
            x_label = "Time"
            title = "Live Plot"

        # Build channels list from record config
        channels = []
        if self.record_config.use_ser:
            serial_cols = logger.parse_serial_params(self.record_config.serial_params)
            if serial_cols:
                channels.extend(serial_cols)
            else:
                channels.append(logger.COL_SERIAL)
        if self.record_config.use_dmm:
            channels.append(logger.COL_DMM_MEAS1)
        if self.record_config.use_ps:
            channels.append(logger.COL_PS_VMEAS1)
            channels.append(logger.COL_PS_IMEAS1)
        if self.record_config.use_osc and self.record_config.osc_config:
            channels += logger.build_osc_columns(self.record_config.osc_config)

        if not channels:
            self.prompt.print("No channels selected for live plot")
            return

        # If Dash is already running, update shared state with new config
        if self._dash_thread is not None and self._dash_thread.is_alive():
            plotter.update_live_plot_state(
                self._live_state, self.bus, x_key, channels, buf_size, x_label)
            self.prompt.print("Live plot updated with new configuration")
            return

        self._dash_thread = threading.Thread(
            target=plotter.start_live_plot,
            kwargs=dict(
                data_bus=self.bus,
                x_key=x_key,
                channels=channels,
                buffer_size=buf_size,
                refresh_ms=150,
                x_label=x_label,
                title=title,
                port=8050,
                debug=False,
                state=self._live_state,
            ),
            daemon=True
        )
        self._dash_thread.start()
        self.prompt.print("Live plot started at http://127.0.0.1:8050")