
# TODO: ask claude to enforce file header formatting for tabs only

# import needed GUI modules
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle

# import needed modules
import threading
import time
from datetime import datetime
import pandas as pd
from queue import Queue

# import user defined modules
from common import logger
from common import plotter
from common import path_helper
from EEequipment.equipment_manager import COMMUNICATION_ERRORS


# TODO: I should probably add an option to even save the data file at all. Useful for stimulus generating (and testing)

# TODO: have the labels on this page reference some ttk Style

# TODO: while I have my nice UART evm I should play with serial logging more
#   can it detect the proper number of named serial parameters first time? Just add names?


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
        self.is_dual_stimulus = False

        # Create container for all frames to use pack for better spacing control
        self.fr_top_container = tk.Frame(self, bg=self.theme_config["bg_dark"])

        # create rows in container
        top_row = tk.Frame(self.fr_top_container, bg=self.theme_config["bg_dark"])
        bottom_row = tk.Frame(self.fr_top_container, bg=self.theme_config["bg_dark"])
        top_row.pack(fill="x", padx=15, pady=self.theme_config["size"]["ypad_m"])
        bottom_row.pack(fill="x", padx=15, pady=(0, 15))

        # create Frames in container
        self.fr_status = tk.Frame(top_row, bg=self.theme_config["dark_2"])
        self.fr_setup = tk.Frame(top_row, bg=self.theme_config["dark_2"])
        self.fr_stimulus = tk.Frame(bottom_row, bg=self.theme_config["dark_2"])
        # set up prompt (also in container)
        self.prompt = guic.Prompt(bottom_row, self.theme_config, "Data Logger Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt_s"])

        # pack all Frames
        self.fr_status.pack(side="left", padx=(0, 15))
        self.fr_setup.pack(side="left")
        self.fr_stimulus.pack(side="left", padx=(0, 15))
        self.prompt.pack(side="left")

        # Place container with grid (only one grid call on main tab)
        self.fr_top_container.grid(row=1, column=0)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 8 (Logger) content")

        # print welcome text_data
        l1 = ttk.Label(self, text="Data Logger", style="BW.TLabel",
                       font=(self.theme_config["font"]["family"], 16))
        l1.grid(row=0, column=0, columnspan=4)

        self.init_fr_status()
        self.init_fr_setup()
        self.init_fr_stimulus()

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
                        onvalue=1, offvalue=0).grid(row=3, column=2)

        self.var_use_fg = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use FG",
                        variable=self.var_use_fg,
                        onvalue=1, offvalue=0).grid(row=3, column=3)

        # add serial parameters box
        self.lbl_use_ser = tk.Label(self.fr_setup, text="Serial parameters")
        self.serial_log_params = tk.Text(self.fr_setup, height=2, width=40)
        self.serial_log_params.insert("1.0", "placeholder")
        self.serial_log_params.tag_add("placeholder", "1.0", "end")
        self.serial_log_params.tag_config("placeholder", foreground="gray")

        self.lbl_use_ser.grid(row=4, column=1, padx=5, pady=5)
        self.serial_log_params.grid(row=4, column=2, padx=self.theme_config["pad"]["xpad_s"],
                                    pady=self.theme_config["pad"]["ypad_s"])
        self.toggle_use_ser() # NOTE: initial state should be OFF so serial parameters should be hidden

        # speed recording options
        options = ['1s', '2s', '5s', '10s', '30s', '60s', '5m', '10m', '30m', '1h', '0.5s']
        self.optRecSpd, self.RecSpdVal = guih.generate_drop_down(self.fr_setup, options)
        self.optRecSpd.grid(row=5, column=0, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button START recording
        btn_start_entry = tk.Button(self.fr_setup, text="Start Record",
                                 command=lambda: self.start_record(),
                                 bg=self.theme_config["success"], fg=self.theme_config["fg_light"], height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=5, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button STOP recording
        btn_stop_entry = tk.Button(self.fr_setup, text="Stop Record",
                                command=lambda: self.stop_record(),
                                bg=self.theme_config["error"], fg=self.theme_config["fg_light"], height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_stop_entry.grid(row=5, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        self.labelRNums = ttk.Label(self.fr_setup, text='', width=12, relief='sunken')
        self.labelRNums.grid(row=5, column=3, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"], sticky='W')

        # add check button to graph data
        self.var_graph_data = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Graph",
                        variable=self.var_graph_data,
                        onvalue=1,
                        offvalue=0).grid(row=6, column=2)

        # add check button to graph data
        self.var_save_data = tk.IntVar(value=1)
        ttk.Checkbutton(self.fr_setup,
                        text="Save data",
                        variable=self.var_save_data,
                        onvalue=1,
                        offvalue=0).grid(row=6, column=3)

        # set up button START live GRAPH
        btn_live_graph = tk.Button(self.fr_setup, text="Live Graph",
                                command=lambda: self.start_live_plot(),
                                bg=self.theme_config["dark_3"], fg=self.theme_config["fg_light"], height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_live_graph.grid(row=6, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

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
        # TODO: actually make sure this is implemented (will require me to properly implement channel handling in EE equipment too!)
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
            ["PS Voltage", "FG Frequency", "FG Duty Cycle"]
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


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################
    # NOTE: some of these are linked to Checkbuttons (instead of Buttons)

    def toggle_use_ser(self):
        if self.var_use_ser.get():
            self.lbl_use_ser.grid()
            self.serial_log_params.grid()
        else:
            self.lbl_use_ser.grid_remove()
            self.serial_log_params.grid_remove()

    def toggle_stimulus(self):
        """Show/hide stimulus configuration based on checkbox"""
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

    def start_record(self):
        # Organize parameters first
        self.organize_record_params()
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
                         self.record_config.use_fg)
        has_stimulus = self.var_use_stimulus.get()

        if not has_instrument and not has_stimulus:
            guih.alert_user("Can't start record!",
                          "Please select at least one instrument to record OR enable stimulus mode",
                          "warning")
            return

        # If we reach here, all requested instruments are ready and user has selected at least 1 instrument or stimulus
        # TODO: Claude should check to see if this is the cleanest way to manage NOT saving data
        if self.var_save_data.get():
            logger.start_recording(self.csvh)
        self.record_status = True
        self.cc.recording = True  # Signal to ClassController that recording is active
        self.prompt.print(f"Starting recording at: {self.data_dir}{self.recName}")
        self.prompt.print(f"Recording every {self.record_speed} seconds ...")
        threading.Thread(target=self.thread_record).start()

    def stop_record(self):
        self.record_status = False
        self.cc.recording = False  # Signal to ClassController that recording has stopped
        self.prompt.print("Stopped data record!")

        # plot data if requested
        if self.record_config.make_graph:
            self.final_plot()

    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    def set_record_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    def set_record_speed(self):
        # TODO: this function needs to know if we want serial data to base our timing off that value (record samples at each UART output)
        # changes the recording speed based on recording speed GUI element
        def parse_time_to_seconds(time_str):
            """Convert a time string to seconds.

            Args:
                time_str (str): Time string to convert. Should end with 's', 'm', or 'h'.

            Returns:
                int: Time in seconds.
            """
            if not isinstance(time_str, str):
                raise ValueError("Input should be a string.")

            time_str = time_str.strip().lower()
            if time_str.endswith('s'):
                return int(time_str[:-1])
            elif time_str.endswith('m'):
                return int(time_str[:-1]) * 60
            elif time_str.endswith('h'):
                return int(time_str[:-1]) * 3600
            else:
                raise ValueError("Time string should end with 's', 'm', or 'h'.")

        self.record_speed = parse_time_to_seconds(self.RecSpdVal.get())

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
                    settling_time=0.0,  # Use outer loop settling time # TODO: why is this 0.0?
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
                self.is_dual_stimulus = True
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
                self.is_dual_stimulus = False
                self.prompt.print(f"Stimulus sweep configured: {len(self.stimulus_generator)} steps")

        except ValueError as e:
            guih.alert_user("Invalid Stimulus Values", str(e), "error")
            raise

    def organize_record_params(self):
        # get all needed GUI elements
        prefix = "AREC" # tag:HARDCODE
        ext_text = self.output_file_name.get("1.0", "end").strip("\n")

        # create recording config
        self.record_config = logger.create_record_config(
            self.var_use_ser.get(),
            self.var_use_dmm.get(),
            self.var_use_ps.get(),
            self.var_use_fg.get(),
            1, # TODO: this is a hardcode, als shouldn't be named `ps_channels`
            self.serial_log_params.get("1.0", "end").strip(),
            self.var_graph_data.get()
        )
        self.record_config.print()

        # create stimulus config if enabled
        if self.var_use_stimulus.get():
            self.set_stimulus()
        else:
            self.stimulus_config = None
            self.stimulus_generator = None
            self.is_dual_stimulus = False

        # setup recording
        self.recName, self.csvh = logger.setup_recording(
                self.data_dir,
                prefix,
                ext_text,
                self.record_config,
                self.stimulus_config
        )

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
            # Build a row of data based on what user wants
            row = self._collect_data_row()

            # save row (locally and to a file if requested)
            self.recorded_data.append(row)
            if self.var_save_data.get():
                self._save_data_row(row)

            # Update record counter and UI
            self.recCnt += 1
            self.labelRNums.config(text=f'#{self.recCnt:7d}')

            # Wait for next sample
            time.sleep(self.record_speed)

    def start_record_stimulus(self):
        self.prompt.print(f"Starting stimulus sweep with {len(self.stimulus_generator)} steps")

        # turn on power supply if being used
        # TODO: I don't love how clunky this is (below). I should be able to just reference my stimulus_config variables to get all the info I need
        #   and not have to reference self.is_dual_stimulus
        # TODO: Claude can also broadly check how I can detect if I'm using a PS
        if self.is_dual_stimulus:
            if self.stimulus_config.outer_loop.stimulus_type == logger.StimulusType.PS_VOLTAGE:
                self.cc.ps.output_on(self.stimulus_config.channel)
            elif self.stimulus_config.inner_loop.stimulus_type == logger.StimulusType.PS_VOLTAGE:
                self.cc.ps.output_on(self.stimulus_config.channel)
        elif self.stimulus_config.stimulus_type == logger.StimulusType.PS_VOLTAGE:
            self.cc.ps.output_on(self.stimulus_config.channel)
        # end of equipment configure

        # start stimulus thread
        try:
            if self.is_dual_stimulus:
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

    # TODO: finish implementing this
    def thread_record_serial(self):
        pass

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
            row["Stimulus_Step"] = str(step_num)

            # Save row (locally and to a file if requested)
            self.recorded_data.append(row)
            if self.var_save_data.get():
                self._save_data_row(row)

            # Update progress
            self.recCnt += 1
            progress_text = f'Step {step_num}/{len(self.stimulus_generator)}'
            self.labelRNums.config(text=progress_text)
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
            row["Stimulus_Step"] = step_num

            # Save row (locally and to a file if requested)
            self.recorded_data.append(row)
            if self.var_save_data.get():
                self._save_data_row(row)

            # Update progress
            self.recCnt += 1
            progress_text = f'Step {step_num}/{len(self.stimulus_generator)}'
            self.labelRNums.config(text=progress_text)

    def _collect_data_row(self):
        row = {"Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}

        # Serial data if requested
        if self.record_config.use_ser is True:
            row["SerialData"] = self.cc.ser.read_line()

        # DMM data if requested
        if self.record_config.use_dmm:
            row["DMM_Meas1"] = self.cc.dmm.read_value()

        # Power Supply data if requested
        if self.record_config.use_ps:
            try:
                time.sleep(5)
                print("getting Vset1")
                row["PS_Vset1"] = self.cc.ps.get_set_voltage(1)
                time.sleep(5)
                print("getting Vmeas1")
                # TODO: some issue with E3640A where if in stimulus mode it turns off the output very briefly for measurement here
                #   I think the issue is at this line where output goes off
                #   is the format getting weird? Idk
                row["PS_Vmeas1"] = self.cc.ps.get_voltage(1)
                time.sleep(5)
                print("getting Imeas1")
                row["PS_Imeas1"] = self.cc.ps.get_current(1)
                time.sleep(5)
                if self.record_config.ps_channels == 2:
                    row["PS_Vset2"] = self.cc.ps.get_set_voltage(2)
                    row["PS_Vmeas2"] = self.cc.ps.get_set_voltage(2)
                    row["PS_Imeas1"] = self.cc.ps.get_current(1)
            except COMMUNICATION_ERRORS as e:
                self.record_status = False
                guih.alert_user("Communication Error", str(e), "error")


        # Function Generator data if requested
        if self.record_config.use_fg:
            try:
                row["FG_Freq"] = self.cc.fg.query(
                    self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_frequency")
                )
                row["FG_Waveform"] = self.cc.fg.query(
                    self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_shape")
                )
            except Exception:
                row["FG_Freq"] = "ERROR"
                row["FG_Waveform"] = "ERROR"

        return row

    def _apply_stimulus(self, value, dual=None):
        """Apply the stimulus value to the appropriate instrument"""
        if dual is None:
            stim_type = self.stimulus_config.stimulus_type
        else:
            if dual == 1:
                stim_type = self.stimulus_config.outer_loop.stimulus_type
            elif dual == 2:
                stim_type = self.stimulus_config.inner_loop.stimulus_type
            else:
                return

        if stim_type == logger.StimulusType.PS_VOLTAGE:
            channel = self.stimulus_config.channel
            self.cc.ps.set_voltage(value, channel=channel)

        elif stim_type == logger.StimulusType.FG_FREQUENCY:
            self.cc.fg.set_frequency(value)

        elif stim_type == logger.StimulusType.FG_DUTY_CYCLE:
            self.cc.fg.set_duty(value)

        else:
            raise ValueError(f"Unknown stimulus type: {stim_type}")

    def _save_data_row(self, row):
        # self.csvh.add_row_from_dict(row)
        self.bus.put(row)

    ##############################################################################
    ####      PLOTTING FUNCTIONS        ##########################################
    ##############################################################################

    def final_plot(self):
        df = pd.DataFrame(self.recorded_data)
        x_data = None
        y_data = None
        xlabel = ""
        ylabel = ""
        title = ""
        # TODO: add corresponding xlabel and ylabel stuff here (conditional on config)
        #   NOTE: there might be some reuse between final plot and live plot parameters

        # get X data based on either time based or stimulus
        if self.stimulus_config and self.stimulus_config.enabled:
            title = "Stimulus based logging"
            if self.stimulus_config.stimulus_type == logger.StimulusType.PS_VOLTAGE:
                x_data = df["PS_Voltage"]
                xlabel = "PS Voltage (V)"
        else:
            x_data = df["Time"]
            xlabel = "Time"
            title = "Time based logging"

        # TODO: 3D plots for this case? or that fancy label thing I have going on? Or both and the user can pick?
        # if self.is_dual_stimulus:

        if self.record_config.use_dmm:
            y_data = df["DMM_Meas1"]
            ylabel = "DMM (V)"

        # TODO: for time plots would be so much cleaner to exclude date from information
        plotter.plot(
            x_data,
            y_data,
            xlabel=xlabel,
            ylabel=ylabel,
            title=title
        )

    def start_live_plot(self):
        # organize params based on record config
        # if self.record_config.use_dmm:
        #     pass
        # if self.record_config.use_ps:
        #     pass
        xlabel = ""
        ylabel = ""
        title = ""
        # TODO: have Claude conditionally have these labels being formed

        self.bus = Queue(maxsize=50_000)
        self._dash_thread = None

        # don't save data
        # TODO: evaluate this (would saving the data actually glitch out live plot so much? What's the overhead on that?
        self.var_save_data.set(1)
        self.start_record()

        self.thread_live_plot(xlabel, ylabel, title)
        for i in range(0, 100):
            time.sleep(0.3)
            self.push_live_data()

    def stop_live_plot(self):
        self._dash_thread.stop()

    def thread_live_plot(self, xlabel, ylabel, title):
        self._dash_thread = threading.Thread(
            target=plotter.start_live_plot,
            kwargs=dict(
                data_bus=self.bus,
                x_key="Time",
                channels=["DMM_Meas1"],
                buffer_size=3000,
                refresh_ms=150,
                xlabel=xlabel,
                ylabel=ylabel,
                title=title,
                port=8050,
                debug=False, # disabling debug
            ),
            daemon=True
        )
        self._dash_thread.start()

    def push_live_data(self):
        pass
        # t = time.perf_counter()
        # sample = {"t": t, "PS Voltage": 2.5, "FG Frequency": 1000.0}
        # self.bus.put(sample)

    def thread_live_plot_old(self):
        # TODO: get creative about labeling here
        lplt = plotter.LivePlot("Live plot", "X-axis", "Y-axis")

        def animate(i):
            for j in range(0, 10):
                # TODO: actually retrieve the desired channel here (currently 1 is hardcoded)
                reading = self.cc.ps.get_current(1)
                # timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                lplt.xs.append(len(lplt.xs))  # or a timestamp
                lplt.ys.append(reading)

            # Clear and plot again, but avoid clearing the entire plot for better visual
            lplt.ax.clear()
            lplt.ax.plot(lplt.xs[-2000:], lplt.ys[-2000:], label="Current (A)")

        lplt.show_animation(animate, interval=200)