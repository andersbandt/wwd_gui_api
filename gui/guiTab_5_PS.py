"""Power supply control tab."""

# import needed GUI packages
import logging
import tkinter as tk
from tkinter import ttk

# import needed packages
import time
import threading

# import user defined modules
from EEequipment import equipment_manager

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle

logger = logging.getLogger(__name__)


class TabPS(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        self.fr_port = None
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_status = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up serial / PS variables
        self.channel_count = 0
        self.id = None
        self.ch1_on = False
        self.ch2_on = False
        self.ch1_scale = 1
        self.ch2_scale = 1
        self.ps_v1s = "?"
        self.ps_v2s = "?"
        self.ps_v1r = 0
        self.ps_v2r = 0
        self.ps_i1 = 0
        self.ps_i2 = 0

        # channel status cache — avoid querying the instrument on every tab switch
        self._STATUS_CACHE_TTL = 10.0  # seconds
        self._status_cache = None
        self._status_cache_time = 0.0
        self._poll_after_id = None

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "PS Console Output")

        # initialize tab content
        self.initTabContent()

        # set up serial port
        # NOTE: has to be done after tab content is initalized in initTabContent()
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "PS_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3,
                                            status_cmd=lambda: self.cc.get_ps_status())
        if autoconnect:
            self.fr_port.connect_previous_port()

        # place everything in grid
        self.fr_info.grid(row=1, column=0, columnspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="W")
        self.fr_port.grid(row=1, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_control.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_status.grid(row=2, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.prompt.grid(row=2, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(2, weight=1)
        self.rowconfigure(2, weight=1)

    def initTabContent(self):
        logger.debug("Initializing tab 5 (PS) content")
        self.create_tab_header("PS Control", columnspan=3)
        self.init_fr_info()
        self.init_fr_control()
        self.init_fr_status()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Power Supply Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("ps")
        self.cc.ps_service.set_registry(self.registry)
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

        # Load and set previous model if available
        previous_model = self.cc.get_used_model("PS_PyVISA")
        if previous_model and previous_model in self.registry:
            self.ate_drop[1].set(previous_model)
            logger.info(f"Restored previous PS model: {previous_model}")

        # Add labels for device information
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=40, relief='sunken', anchor='w')

        self.labelTimeConnected = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        self.labelVers = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        # Position the device information labels
        self.labelID.grid(row=1, column=0, sticky='W', padx=5, pady=2)
        self.labelIDValue.grid(row=1, column=1, sticky='W', padx=5, pady=2)
        self.labelTimeConnected.grid(row=2, column=0, sticky='W', padx=5, pady=2)
        self.labelTimeConnectedValue.grid(row=2, column=1, sticky='W', padx=5, pady=2)

        # Add labels for range and measurements
        self.labelV1_s = ttk.Label(self.fr_info, width=10, text='Voltage 1', style="TLabel", anchor='w')
        self.labelV1_r = ttk.Label(self.fr_info, width=15, text='Voltage 1 (read)', style="TLabel", anchor='w')
        self.labelI1 = ttk.Label(self.fr_info, width=10, text='Current 1', style="TLabel", anchor='w')
        self.labelV2_s = ttk.Label(self.fr_info, width=10, text='Voltage 2', style="TLabel", anchor='w')
        self.labelV2_r = ttk.Label(self.fr_info, width=15, text='Voltage 2 (read)', style="TLabel", anchor='w')
        self.labelI2 = ttk.Label(self.fr_info, width=10, text='Current 2', style="TLabel", anchor='w')

        # Position the range and measurement labels
        self.labelV1_s.grid(row=3, column=0, sticky='W', padx=5, pady=2)
        self.labelV1_r.grid(row=4, column=0, sticky='W', padx=5, pady=2)
        self.labelI1.grid(row=5, column=0, sticky='W', padx=5, pady=2)
        if self.channel_count == 2:
            self.labelV2_s.grid(row=6, column=0, sticky='W', padx=5, pady=2)
            self.labelV2_r.grid(row=7, column=0, sticky='W', padx=5, pady=2)
            self.labelI2.grid(row=8, column=0, sticky='W', padx=5, pady=2)

        # Add value labels for range and measurements
        self.valueV1_s = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueV1_r = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueI1 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueV2_s = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueV2_r = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueI2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueI2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')

        # add some drop-downs for unit handling
        self.unitCH1_drop = guih.generate_drop_down(self.fr_info,
                                                   ["A", "mA", "uA"],
                                                   callback_func=self.set_ch1_unit)
        self.unitCH2_drop = guih.generate_drop_down(self.fr_info,
                                                   ["A", "mA", "uA"],
                                                   callback_func=self.set_ch2_unit)

        # Position the value labels
        self.valueV1_s.grid(row=3, column=1, sticky='E', padx=5, pady=2)
        self.valueV1_r.grid(row=4, column=1, sticky='E', padx=5, pady=2)
        self.valueI1.grid(row=5, column=1, sticky='E', padx=5, pady=2)
        self.unitCH1_drop[0].grid(row=5, column=2, sticky='W', padx=5, pady=2)
        if self.channel_count == 2:
            self.valueV2_s.grid(row=6, column=1, sticky='E', padx=5, pady=2)
            self.valueV2_r.grid(row=7, column=1, sticky='E', padx=5, pady=2)
            self.valueI2.grid(row=8, column=1, sticky='E', padx=5, pady=2)
            self.unitCH2_drop[0].grid(row=8, column=2, sticky='W', padx=5, pady=2)

        # ADD A REFRESH
        self.btn_update = tk.Button(self.fr_info, text='UPDATE PS', command=self.update_PS)
        self.btn_update.grid(row=9, column=2, pady=5, padx=3, sticky='W')

    def init_fr_control(self):
        fr_m = self.fr_control

        # CHANNEL 1 CONTROLS
        self.ch1_label = ttk.Label(fr_m, text="Channel 1", style="TLabel")
        self.ch1_voltage = tk.Entry(fr_m)
        self.ch1_set_btn = tk.Button(fr_m, text="Set Voltage",
                                      command=lambda: self.set_voltage(1, self.ch1_voltage.get()))
        self.ch1_current = tk.Entry(fr_m)
        self.ch1_set_i_btn = tk.Button(fr_m, text="Set Current",
                                       command=lambda: self.set_current(1, self.ch1_current.get()))

        self.ch1_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(1))
        self.ch1_label.grid(row=0, column=0, padx=10, pady=10)
        self.ch1_voltage.grid(row=0, column=1, padx=10, pady=10)
        self.ch1_set_btn.grid(row=0, column=2, padx=10, pady=10)
        self.ch1_current.grid(row=0, column=3, padx=10, pady=10)
        self.ch1_set_i_btn.grid(row=0, column=4, padx=10, pady=10)
        self.ch1_toggle_btn.grid(row=0, column=5, padx=10, pady=10)

        # CHANNEL 2 CONTROLS
        self.ch2_label = ttk.Label(fr_m, text="Channel 2", style="TLabel")
        self.ch2_voltage = tk.Entry(fr_m)
        self.ch2_set_btn = tk.Button(fr_m, text="Set Voltage",
                                      command=lambda: self.set_voltage(2, self.ch2_voltage.get())
                                      )
        self.ch2_current = tk.Entry(fr_m)
        self.ch2_set_i_btn = tk.Button(fr_m, text="Set Current",
                                       command=lambda: self.set_current(2, self.ch2_current.get()))
        self.ch2_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(2))
        if self.channel_count == 2:
            self.ch2_label.grid(row=1, column=0, padx=10, pady=10)
            self.ch2_voltage.grid(row=1, column=1, padx=10, pady=10)
            self.ch2_set_btn.grid(row=1, column=2, padx=10, pady=10)
            self.ch2_current.grid(row=1, column=3, padx=10, pady=10)
            self.ch2_set_i_btn.grid(row=1, column=4, padx=10, pady=10)
            self.ch2_toggle_btn.grid(row=1, column=5, padx=10, pady=10)

    def init_fr_status(self):
        # channel 1 CV/CC mode
        self.labelCh1Mode = ttk.Label(self.fr_status, width=10, text='Ch 1 Mode', style="TLabel", anchor='w')
        self.ch1_mode = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelCh1Mode.grid(row=0, column=0, pady=15, padx=15)
        self.ch1_mode.grid(row=1, column=0, pady=15, padx=15)

        # channel 2 CV/CC mode
        self.labelCh2Mode = ttk.Label(self.fr_status, width=10, text='Ch 2 Mode', style="TLabel", anchor='w')
        self.ch2_mode = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        if self.channel_count == 2:
            self.labelCh2Mode.grid(row=0, column=1, pady=15, padx=15)
            self.ch2_mode.grid(row=1, column=1, pady=15, padx=15)

    def gui_refresh_info(self):
        if self.fr_port.status:
            self.valueV1_s.config(text='{:8s}'.format(str(self.ps_v1s)))
            self.valueV1_r.config(text='{:8s}'.format(str(self.ps_v1r)))
            self.valueI1.config(text='{:8s}'.format(str(self.ps_i1)))
            self.valueV2_s.config(text='{:8s}'.format(str(self.ps_v2s)))
            self.valueV2_r.config(text='{:8s}'.format(str(self.ps_v2r)))
            self.valueI2.config(text='{:8s}'.format(str(self.ps_i2)))

    def _get_status_cached(self):
        """Return cached channel status, querying the instrument only when the cache is stale."""
        now = time.monotonic()
        if self._status_cache is not None and (now - self._status_cache_time) < self._STATUS_CACHE_TTL:
            return self._status_cache
        status = self.cc.ps.check_status()
        self._status_cache = status
        self._status_cache_time = time.monotonic()
        return status

    def _schedule_status_poll(self):
        """Background poll every TTL seconds so the cache stays fresh even when the tab isn't visible."""
        if not self.cc.get_ps_status():
            return

        def _poll():
            status = self.cc.ps.check_status()
            self._status_cache = status
            self._status_cache_time = time.monotonic()

        threading.Thread(target=_poll, daemon=True).start()
        self._poll_after_id = self.after(int(self._STATUS_CACHE_TTL * 1000), self._schedule_status_poll)

    # NOTE: this function is quite similar to the relay one in tab 1
    def gui_refresh_channel_state(self):
        if self.cc.get_ps_status():
            status_decode = self._get_status_cached()
        else:
            return

        if status_decode.get("error"):
            self.prompt.print(f"Status query failed: {status_decode['error']}", "error")
            return

        try:
            if status_decode["ch1_state"] == "ON":
                self.ch1_toggle_btn.config(bg=self.theme_config["success"])
            else:
                self.ch1_toggle_btn.config(bg=self.theme_config["error"])

            if status_decode["ch1_mode"] == "CV":
                self.ch1_mode.set_color(self.theme_config["success"])
            else:
                self.ch1_mode.set_color(self.theme_config["error"])

            # if we have 2-channel PS
            if self.channel_count > 1:
                if status_decode["ch2_state"] == "ON":
                    self.ch2_toggle_btn.config(bg=self.theme_config["success"])
                else:
                    self.ch2_toggle_btn.config(bg=self.theme_config["error"])

                if status_decode["ch2_mode"] == "CV":
                    self.ch2_mode.set_color(self.theme_config["success"])
                else:
                    self.ch2_mode.set_color(self.theme_config["error"])

        except KeyError as e:
            guih.alert_user("Can't set channel CC/CV states", f"KeyError:{e}", "error")
            self.ch1_mode.set_color("black")
            self.ch2_mode.set_color("black")

    def gui_refresh(self, event):
        logger.debug("gui_refresh for PS ...")
        if event == "auto" and not self.fr_port.status:
            self.fr_port.refresh_ports()
            logger.debug("End of refreshing ports")
        self.gui_refresh_info()
        self.gui_refresh_channel_state()
        logger.debug("end of gui_refresh for PS!")

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def set_ch1_unit(self):
        unit = self.unitCH1_drop[1].get()
        self.prompt.print(f"Setting channel 1 units to {unit}")
        if unit == "mA":
            self.ch1_scale = 1e3
        elif unit == "uA":
            self.ch1_scale = 1e6
        elif unit == "A":
            self.ch1_scale = 1

    def set_ch2_unit(self):
        unit = self.unitCH2_drop[1].get()
        self.prompt.print(f"Setting channel 2 units to {unit}")
        if unit == "mA":
            self.ch2_scale = 1e3
        elif unit == "uA":
            self.ch2_scale = 1e6
        elif unit == "A":
            self.ch2_scale = 1

    def update_PS(self):
        if self.fr_port.status:
            self.ps_v1r = self.cc.ps.get_voltage(1)
            self.ps_i1 = self.cc.ps.get_current(1)
            self.ps_i1 = self.ps_i1 * self.ch1_scale
            if self.channel_count == 2:
                self.ps_v2r = self.cc.ps.get_voltage(2)
                self.ps_i2 = self.cc.ps.get_current(2)
                self.ps_i2 = self.ps_i2 * self.ch2_scale
            self.gui_refresh_info()

    def toggle_channel(self, channel):
        if not self.cc.get_ps_status():
            guih.alert_user("Can't toggle channel", "No PS connection!", "error")
            return False

        try:
            if channel == 1:
                if self.ch1_on is True:
                    self.cc.ps.output_off(channel)
                    self.ch1_on = False
                else:
                    self.cc.ps.output_on(channel)
                    self.ch1_on = True
            elif channel == 2:
                if self.ch2_on is True:
                    self.cc.ps.output_off(channel)
                    self.ch2_on = False
                else:
                    self.cc.ps.output_on(channel)
                    self.ch2_on = True
            else:
                raise ValueError("Wrong channel input")
        except ValueError as e:
            guih.alert_user("Can't toggle channel", f"Error: {e}", "error")
        else:
            state = None
            if channel == 1:
                state = self.ch1_on
            elif channel == 2:
                state = self.ch2_on
            self.prompt.print(f"Toggled channel {channel} to state {state}")

        # Patch the cache with the known new state so gui_refresh_channel_state
        # doesn't need to query the instrument again.
        if self._status_cache is not None:
            key = f"ch{channel}_state"
            self._status_cache[key] = "ON" if (self.ch1_on if channel == 1 else self.ch2_on) else "OFF"
            self._status_cache_time = time.monotonic()
        self.gui_refresh("call")

    def set_voltage(self, channel, voltage_str):
        if self.cc.get_ps_status():
            # have to format input text_data box into float
            voltage = float(voltage_str)
            self.cc.ps.set_voltage(voltage, channel=channel)
            self.prompt.print(f"Set voltage on channel {channel} to {voltage} V")
            if channel == 1:
                self.ps_v1s = voltage
            elif channel == 2:
                self.ps_v2s = voltage

            # refresh statistics and update GUI info
            self.update_PS()
            self.gui_refresh_info()
        else:
            guih.alert_user("Can't set voltage", "No PS connection!", "error")

    def set_current(self, channel, current_str):
        if not self.cc.get_ps_status():
            guih.alert_user("Can't set current", "No PS connection!", "error")
            return

        # interpret the entry in the channel's selected unit (A / mA / uA),
        # converting to amps before sending to the driver
        scale = self.ch1_scale if channel == 1 else self.ch2_scale
        try:
            current = float(current_str) / scale
        except ValueError:
            guih.alert_user("Can't set current", f"Invalid current: '{current_str}'", "error")
            return

        # driver applies the per-channel calibration offset automatically
        if self.cc.ps_service.set_current(channel, current):
            self.prompt.print(f"Set current limit on channel {channel} to {current_str} "
                              f"({current} A, before cal offset)")
            self.update_PS()
            self.gui_refresh_info()
        else:
            self.prompt.print(f"Failed to set current limit on channel {channel}", "error")

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PyVISA resource!")
        port = self.fr_port.get_port()
        model_name = self.ate_drop[1].get()
        result = self.cc.ps_service.connect(port, model_name)

        if not result.success:
            self.prompt.print(result.error, "error")
            guih.alert_user("Can't connect to PS", result.error, "warning")
            self.fr_port.set_status(False)
            return False

        for fr in (self.fr_info, self.fr_control, self.fr_status):
            for w in fr.winfo_children():
                w.destroy()
        self.channel_count = self.cc.ps.channel_count
        self.init_fr_info()
        self.init_fr_control()
        self.init_fr_status()

        self.prompt.print(f"Connected to PS with id: {result.device_id}")
        self.labelIDValue.config(text=result.device_id)
        self.labelTimeConnectedValue.config(text=result.timestamp)
        self.fr_port.set_status(True)

        self.ch1_on = 0
        self.ch2_on = 0
        # Invalidate cache so the first refresh actually queries the instrument
        self._status_cache = None
        self._status_cache_time = 0.0
        # Start background poll to keep cache warm
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
        self._poll_after_id = self.after(int(self._STATUS_CACHE_TTL * 1000), self._schedule_status_poll)
        self.gui_refresh("connect")

        if result.error:
            self.prompt.print(f"Warning: {result.error}", "warning")
        return True

    def port_close(self):
        self.prompt.print("Closing PS resource!")
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        self._status_cache = None
        result = self.cc.ps_service.disconnect()
        if not result.success:
            guih.alert_user("Can't disconnect PS", result.error, "warning")
        self.fr_port.set_status(False)
