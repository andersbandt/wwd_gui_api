
# import needed packages
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import threading
import os
import time
from datetime import datetime

# import user defined modules
from common import logger

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle




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
        self.data_dir = basefilepath + "/data/"
        self.csvh = None
        self.record_config = None
        self.stimulus_config = None
        self.stimulus_generator = None

        self.fr_status = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_setup = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_stimulus = tk.Frame(self, bg=self.theme_config["light_4"])
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
        self.fr_status.grid(row=1, column=0, pady=15, padx=15)
        self.fr_setup.grid(row=1, column=1, pady=15, padx=15)
        self.fr_stimulus.grid(row=1, column=2, pady=15, padx=15)
        self.fr_analysis.grid(row=2, column=0, pady=15, padx=15)
        self.prompt.grid(row=2, column=1, columnspan=4, padx=30, pady=12)

    def initTabContent(self):
        print("Initializing tab 2 (Logger) content")

        # print welcome text_data
        l1 = ttk.Label(self, text="Data Logger", style="BW.TLabel",
                       font=(self.theme_config["font"]["family"], 16))
        l1.grid(column=0, row=0, columnspan=4)

        self.init_fr_status()
        self.init_fr_setup()
        self.init_fr_stimulus()
        self.init_fr_analysis()

    def init_fr_status(self):
        # Serial connection status
        self.labelSerStat = ttk.Label(self.fr_status, width=10, text='Serial', style="TLabel", anchor='w')
        self.ser_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelSerStat.grid(row=0, column=0)
        self.ser_status.grid(row=0, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # DMM connection status
        self.labelDmmStat = ttk.Label(self.fr_status, width=10, text='DMM', style="TLabel", anchor='w')
        self.dmm_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelDmmStat.grid(row=1, column=0)
        self.dmm_status.grid(row=1, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # PS connection status
        self.labelPsStat = ttk.Label(self.fr_status, width=10, text='PS', style="TLabel", anchor='w')
        self.ps_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelPsStat.grid(row=2, column=0)
        self.ps_status.grid(row=2, column=1, pady=self.theme_config["pad"]["ypad_s"])
        # FG connection status
        self.labelFgStat = ttk.Label(self.fr_status, width=10, text='FG', style="TLabel", anchor='w')
        self.fg_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelFgStat.grid(row=3, column=0)
        self.fg_status.grid(row=3, column=1, pady=self.theme_config["pad"]["ypad_s"])

    def init_fr_setup(self):
        # add directory search
        self.lbl_data_directory = tk.Label(self.fr_setup, text=self.data_dir, bg=self.theme_config["bg_light"])
        self.lbl_data_directory.grid(row=2, column=0)
        btn_set_directory = tk.Button(self.fr_setup, text="Set directory",
                                 command=lambda: self.set_record_directory(),
                                 bg=self.theme_config["light_1"], fg="black", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
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
                        onvalue=1,
                        offvalue=0,
                        command=self.toggle_use_ser).grid(row=3, column=0, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])


        self.var_use_dmm = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use DMM",
                        variable=self.var_use_dmm,
                        onvalue=1,
                        offvalue=0).grid(row=3, column=1)

        self.var_use_ps = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use PS",
                        variable=self.var_use_ps,
                        onvalue=1,
                        offvalue=0).grid(row=3, column=2)

        self.var_use_fg = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use FG",
                        variable=self.var_use_fg,
                        onvalue=1,
                        offvalue=0).grid(row=3, column=3)

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
                                 bg=self.theme_config["success"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_start_entry.grid(row=5, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        # set up button STOP recording
        btn_stop_entry = tk.Button(self.fr_setup, text="Stop Record",
                                command=lambda: self.stop_record(),
                                bg=self.theme_config["error"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_stop_entry.grid(row=5, column=2, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

        self.labelRNums = ttk.Label(self.fr_setup, text='', width=8, relief='sunken')
        self.labelRNums.grid(row=5, column=3, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"], sticky='W')

        # set up button START live GRAPH
        btn_live_graph = tk.Button(self.fr_setup, text="Live Graph",
                                command=lambda: None,
                                bg=self.theme_config["dark_3"], fg="white", height=self.theme_config["size"]["h_button"], width=self.theme_config["size"]["w_button"])
        btn_live_graph.grid(row=6, column=1, padx=self.theme_config["pad"]["xpad_s"], pady=self.theme_config["pad"]["ypad_s"])

    def init_fr_stimulus(self):
        """Initialize stimulus sweep configuration UI"""
        # Title
        ttk.Label(self.fr_stimulus, text="Stimulus Sweep", style="TPinkLabel.TLabel").grid(
            row=0, column=0, columnspan=2, pady=5, padx=10
        )

        # Enable stimulus checkbox
        self.var_use_stimulus = tk.IntVar()
        ttk.Checkbutton(self.fr_stimulus,
                        text="Enable Stimulus Sweep",
                        variable=self.var_use_stimulus,
                        onvalue=1,
                        offvalue=0,
                        command=self.toggle_stimulus).grid(
            row=1, column=0, columnspan=2, padx=5, pady=5
        )

        # Stimulus type dropdown
        tk.Label(self.fr_stimulus, text="Stimulus Type:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        self.stimulus_type_drop = guih.generate_drop_down(
            self.fr_stimulus,
            ["PS Voltage", "FG Frequency", "FG Duty Cycle"]
        )
        self.stimulus_type_drop[0].grid(row=2, column=1, padx=5, pady=2)

        # Sweep mode dropdown
        tk.Label(self.fr_stimulus, text="Sweep Mode:").grid(row=3, column=0, sticky='w', padx=5, pady=2)
        self.sweep_mode_drop = guih.generate_drop_down(
            self.fr_stimulus,
            ["Linear", "Logarithmic"]
        )
        self.sweep_mode_drop[0].grid(row=3, column=1, padx=5, pady=2)

        # Start value
        tk.Label(self.fr_stimulus, text="Start Value:").grid(row=4, column=0, sticky='w', padx=5, pady=2)
        self.stim_start_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_start_entry.grid(row=4, column=1, padx=5, pady=2)
        self.stim_start_entry.insert(0, "1.0")

        # Stop value
        tk.Label(self.fr_stimulus, text="Stop Value:").grid(row=5, column=0, sticky='w', padx=5, pady=2)
        self.stim_stop_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_stop_entry.grid(row=5, column=1, padx=5, pady=2)
        self.stim_stop_entry.insert(0, "10.0")

        # Step value
        tk.Label(self.fr_stimulus, text="Step Value:").grid(row=6, column=0, sticky='w', padx=5, pady=2)
        self.stim_step_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_step_entry.grid(row=6, column=1, padx=5, pady=2)
        self.stim_step_entry.insert(0, "1.0")

        # Settling time
        tk.Label(self.fr_stimulus, text="Settling Time (s):").grid(row=7, column=0, sticky='w', padx=5, pady=2)
        self.stim_settling_entry = tk.Entry(self.fr_stimulus, width=15)
        self.stim_settling_entry.grid(row=7, column=1, padx=5, pady=2)
        self.stim_settling_entry.insert(0, "0.5")

        # PS Channel (only relevant for PS voltage)
        tk.Label(self.fr_stimulus, text="PS Channel:").grid(row=8, column=0, sticky='w', padx=5, pady=2)
        self.stim_ps_channel_drop = guih.generate_drop_down(
            self.fr_stimulus,
            [1, 2]
        )
        self.stim_ps_channel_drop[0].grid(row=8, column=1, padx=5, pady=2)

        # Status label for showing sweep progress
        self.stim_progress_label = tk.Label(self.fr_stimulus, text="", relief='sunken', width=20)
        self.stim_progress_label.grid(row=9, column=0, columnspan=2, padx=5, pady=5)

        # Initially hide stimulus controls
        self.toggle_stimulus()

    def init_fr_analysis(self):
        # Simple placeholder for file analysis
        # For graphing, use the GRAPH tab (Tab 8)
        ttk.Label(self.fr_analysis, text="File Analysis", style="TPinkLabel.TLabel").grid(
            row=0, column=0, pady=5, padx=10
        )

        info_label = tk.Label(self.fr_analysis,
                              text="For graphing and analysis,\nplease use the GRAPH tab",
                              bg=self.theme_config["light_4"])
        info_label.grid(row=1, column=0, padx=10, pady=20)

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
    # NOTE: some of these are linked to Checkbuttons

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
                if widget != self.var_use_stimulus.master:  # Don't hide the checkbox itself
                    widget.grid()
        else:
            # Hide all stimulus configuration widgets except title and checkbox
            for widget in self.fr_stimulus.winfo_children():
                widget_info = widget.grid_info()
                if widget_info.get('row', 0) > 1:  # Keep row 0 (title) and row 1 (checkbox)
                    widget.grid_remove()

    def start_record(self):
        # Organize parameters first
        self.organize_record_params()
        self.record_status = False
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
            stim_type = self.stimulus_config.stimulus_type

            if stim_type == logger.StimulusType.PS_VOLTAGE:
                if not self.cc.get_ps_status():
                    guih.alert_user("Can't start record!", "PS stimulus requires Power Supply connection!", "error")
                    return
            elif stim_type in [logger.StimulusType.FG_FREQUENCY, logger.StimulusType.FG_DUTY_CYCLE]:
                if not self.cc.get_fg_status():
                    guih.alert_user("Can't start record!", "FG stimulus requires Function Generator connection!", "error")
                    return

        if not self.record_status:
            guih.alert_user("Can't start record!", "No instruments selected", "error")
            return

        # If we reach here, all requested instruments are ready and user has selected at least 1 instrument
        logger.start_recording(self.csvh)
        self.record_status = True
        self.prompt.print(f"Starting recording at: {self.data_dir}{self.recName}")
        self.prompt.print(f"Recording every {self.record_speed} seconds ...")
        threading.Thread(target=self.thread_record).start()

    def stop_record(self):
        self.record_status = False
        self.prompt.print("Stopping data record!")

    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    def set_record_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    # TODO: this function needs to know if we want serial data to base our timing off that value (record samples at each UART output)
    def set_record_speed(self):
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

    def organize_record_params(self):
        # get all needed GUI elements
        prefix = "AREC"
        data_dir = self.data_dir
        ext_text = self.output_file_name.get("1.0", "end").strip("\n")

        # create recording config
        self.record_config = logger.create_record_config(
            self.var_use_ser.get(),
            self.var_use_dmm.get(),
            self.var_use_ps.get(),
            self.var_use_fg.get(),
            1,
            self.serial_log_params.get("1.0", "end").strip()
        )

        # create stimulus config if enabled
        if self.var_use_stimulus.get():
            stimulus_type_str = self.stimulus_type_drop[1].get()
            sweep_mode_str = self.sweep_mode_drop[1].get()

            # Map strings to enums
            stimulus_type_map = {
                "PS Voltage": logger.StimulusType.PS_VOLTAGE,
                "FG Frequency": logger.StimulusType.FG_FREQUENCY,
                "FG Duty Cycle": logger.StimulusType.FG_DUTY_CYCLE
            }
            sweep_mode_map = {
                "Linear": logger.SweepMode.LINEAR,
                "Logarithmic": logger.SweepMode.LOGARITHMIC
            }

            try:
                self.stimulus_config = logger.StimulusConfig(
                    enabled=True,
                    stimulus_type=stimulus_type_map[stimulus_type_str],
                    sweep_mode=sweep_mode_map[sweep_mode_str],
                    start_value=float(self.stim_start_entry.get()),
                    stop_value=float(self.stim_stop_entry.get()),
                    step_value=float(self.stim_step_entry.get()),
                    settling_time=float(self.stim_settling_entry.get()),
                    ps_channel=int(self.stim_ps_channel_drop[1].get())
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
        else:
            self.stimulus_config = None
            self.stimulus_generator = None

        # setup recording
        self.recName, self.csvh = logger.setup_recording(
                data_dir,
                prefix,
                ext_text,
                self.record_config,
                self.stimulus_config
        )

    def thread_record(self):
        # Check if stimulus-based recording
        if self.stimulus_config and self.stimulus_config.enabled:
            self.thread_record_stimulus()
        else:
            self.thread_record_timed()

    def thread_record_timed(self):
        """Time-based recording (original behavior)"""
        while self.record_status:
            # Build a row of data based on what user wants
            row = self._collect_data_row()

            # Update record counter and UI
            self.recCnt += 1
            self.labelRNums.config(text=f'#{self.recCnt:7d}')

            # Append to CSV
            self.csvh.add_row_from_dict(row)

            # Wait for next sample
            time.sleep(self.record_speed)

    def thread_record_stimulus(self):
        """Stimulus-based recording (sweep mode)"""
        self.prompt.print(f"Starting stimulus sweep with {len(self.stimulus_generator)} steps")

        try:
            for step_num, stimulus_value in enumerate(self.stimulus_generator, 1):
                if not self.record_status:
                    break

                # Apply the stimulus
                self._apply_stimulus(stimulus_value)

                # Wait for settling
                time.sleep(self.stimulus_config.settling_time)

                # Collect data
                row = self._collect_data_row()

                # Add stimulus value to the row
                row["Stimulus_Value"] = stimulus_value
                row["Stimulus_Step"] = step_num

                # Update progress
                self.recCnt += 1
                progress_text = f'Step {step_num}/{len(self.stimulus_generator)}'
                self.labelRNums.config(text=progress_text)
                self.stim_progress_label.config(text=progress_text)

                # Append to CSV
                self.csvh.add_row_from_dict(row)

                self.prompt.print(f"Step {step_num}: Stimulus={stimulus_value:.3f}")

            # Sweep complete
            if self.record_status:
                self.prompt.print("Stimulus sweep completed!")
                self.record_status = False

        except Exception as e:
            self.prompt.print(f"Error during stimulus sweep: {e}", "error")
            self.record_status = False

    def _collect_data_row(self):
        """Collect a single row of data from all enabled instruments"""
        row = {"Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}

        # Serial data if requested
        if self.record_config.get("use_ser", False):
            row["SerialData"] = self.cc.ser.read_line()

        # DMM data if requested
        if self.record_config.get("use_dmm", False):
            row["DMM_Meas1"] = self.cc.dmm.read_value()

        # Power Supply data if requested
        if self.record_config.get("use_ps", False):
            row["PS_Vset1"] = self.cc.ps.get_set_voltage(1)
            row["PS_Vmeas1"] = self.cc.ps.get_voltage(1)
            row["PS_Imeas1"] = self.cc.ps.get_current(1)
            if self.record_config["ps_channels"] == 2:
                row["PS_Vset2"] = self.cc.ps.get_set_voltage(2)
                row["PS_Vmeas2"] = self.cc.ps.get_set_voltage(2)
                row["PS_Imeas1"] = self.cc.ps.get_current(1)

        # Function Generator data if requested
        if self.record_config.get("use_fg", False):
            try:
                row["FG_Freq"] = self.cc.fg.query(
                    self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_frequency")
                )
                row["FG_Waveform"] = self.cc.fg.query(
                    self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_shape")
                )
            except Exception as e:
                row["FG_Freq"] = "ERROR"
                row["FG_Waveform"] = "ERROR"

        return row

    def _apply_stimulus(self, value):
        """Apply the stimulus value to the appropriate instrument"""
        stim_type = self.stimulus_config.stimulus_type

        if stim_type == logger.StimulusType.PS_VOLTAGE:
            channel = self.stimulus_config.ps_channel
            self.cc.ps.set_voltage(value, channel)

        elif stim_type == logger.StimulusType.FG_FREQUENCY:
            self.cc.fg.set_frequency(value)

        elif stim_type == logger.StimulusType.FG_DUTY_CYCLE:
            self.cc.fg.set_duty(value)

        else:
            raise ValueError(f"Unknown stimulus type: {stim_type}")







