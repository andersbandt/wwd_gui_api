"""Digital multimeter control and data acquisition tab."""

# import needed GUI packages
import logging
import tkinter as tk
from tkinter import ttk

# import user defined modules
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS
from gui import gui_helper as guih
from gui import gui_class as guic

logger = logging.getLogger(__name__)



class TabDMM(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        # set up frames
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up DMM variables
        self.dmm_id = None
        self.dmm_Auto = ''
        self.dmm_Range = ''
        self.dmm_Fu1 = ''
        self.dmm_Meas1 = ''
        self.meas1_scale = 1
        self.dmm_Fu2 = ''
        self.dmm_Meas2 = ''
        self.dmm_Rate = ''

        # Load DMM configuration
        self.default_rate = self.cc.config_svc.get_dmm_rate()

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "DMM Console Output")

        # initialize tab content
        self.initTabContent()

        # set up port
        self.fr_port = guic.SerialConnFrame(
            self,
            self.theme_config,
            self.cc,
            "DMM_Serial",
            self.port_init,
            self.port_close,
            port_func=3,
            status_cmd=lambda: self.cc.get_dmm_status()
        )
        self.fr_port.initialize_fr()
        if autoconnect:
            self.fr_port.connect_previous_port()


        # place Frames into grid
        self.fr_info.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky='W')
        self.fr_control.grid(row=1, column=1, rowspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_port.grid(row=1, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.prompt.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky='NSEW')

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    def initTabContent(self):
        logger.debug("Initializing tab 2 (DMM) content")
        self.create_tab_header("DMM Control", columnspan=3)
        self.init_fr_info()
        self.init_fr_control()

    def init_fr_info(self):
        fr_m = self.fr_info

        self.labelInfo = ttk.Label(self.fr_info, text='DMM_Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("dmm")
        self.cc.dmm_service.set_registry(self.registry)
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

        # Load and set previous model if available
        previous_model = self.cc.get_used_model("DMM_Serial")
        if previous_model and previous_model in self.registry:
            self.ate_drop[1].set(previous_model)
            logger.info(f"Restored previous DMM model: {previous_model}")

        # Add labels for device information
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=40, relief='sunken', anchor='w')

        self.labelTimeConnected = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        # Position the device information labels
        self.labelID.grid(row=1, column=0, sticky='W', padx=5, pady=2)
        self.labelIDValue.grid(row=1, column=1, sticky='W', padx=5, pady=2)

        self.labelTimeConnected.grid(row=2, column=0, sticky='W', padx=5, pady=2)
        self.labelTimeConnectedValue.grid(row=2, column=1, sticky='W', padx=5, pady=2)

        # Add labels for range and measurements
        self.labelRange = ttk.Label(self.fr_info, width=10, text='Range', style="TLabel", anchor='w')
        self.labelFu1 = ttk.Label(self.fr_info, width=9, text='Func1', style="TLabel", anchor='w')
        self.labelMeas1 = ttk.Label(self.fr_info, width=10, text='Meas1', style="TLabel", anchor='w')
        self.labelFu2 = ttk.Label(self.fr_info, width=9, text='Func2', style="TLabel", anchor='w')
        self.labelMeas2 = ttk.Label(self.fr_info, width=10, text='Meas2', style="TLabel", anchor='w')

        # Position the range and measurement labels
        self.labelRange.grid(row=3, column=0, sticky='W', padx=5, pady=2)
        self.labelFu1.grid(row=4, column=0, sticky='W', padx=5, pady=2)
        self.labelMeas1.grid(row=5, column=0, sticky='W', padx=5, pady=2)
        self.labelFu2.grid(row=6, column=0, sticky='W', padx=5, pady=2)
        self.labelMeas2.grid(row=7, column=0, sticky='W', padx=5, pady=2)

        # Add value labels for range and measurements
        self.valueRange = tk.Label(self.fr_info, width=18, text='', relief='sunken', anchor='w')
        self.valueFu1 = tk.Label(self.fr_info, width=18, text='', relief='sunken', anchor='w')
        self.valueMeas1 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueFu2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueMeas2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')

        # add some drop-downs for unit handling
        self.unitMeas1_drop = guih.generate_drop_down(fr_m,
                                                   ["V", "mV", "uV"],
                                                   callback_func=self.set_meas1_unit)

        # Position the value labels
        self.valueRange.grid(row=3, column=1, sticky='W', padx=5, pady=2)
        self.valueFu1.grid(row=4, column=1, sticky='W', padx=5, pady=2)
        self.valueMeas1.grid(row=5, column=1, sticky='W', padx=5, pady=2)
        self.unitMeas1_drop[0].grid(row=5, column=2)
        self.valueFu2.grid(row=6, column=1, sticky='W', padx=5, pady=2)
        self.btn_func2_toggle = tk.Button(self.fr_info, text='FREQ On/Off', command=self.toggle_func2)
        self.btn_func2_toggle.grid(row=6, column=2, padx=3, pady=2)
        self.valueMeas2.grid(row=7, column=1, sticky='W', padx=5, pady=2)

        # hide secondary display by default (shown when DMM supports it)
        self._secondary_visible = False
        self._hide_secondary_display()

        self.labelRate = ttk.Label(self.fr_info, width=10, text='Rate', style="TLabel", anchor='w')
        self.valueRate = tk.Label(self.fr_info, width=18, text='', relief='sunken', anchor='w')
        self.labelRate.grid(row=8, column=0, sticky='W', padx=5, pady=2)
        self.valueRate.grid(row=8, column=1, sticky='W', padx=5, pady=2)

        # ADD A REFRESH
        self.btn_update = tk.Button(self.fr_info, text='UPDATE DMM', command=self.gui_refresh_DMM)
        self.btn_update.grid(row=7, column=2, pady=5, padx=3, sticky='W')

    def init_fr_control(self):
        fr_m = self.fr_control

        labelInfo = ttk.Label(fr_m, text='DMM_Control', style="TPinkLabel.TLabel", width=15)
        labelInfo.grid(row=0, column=0, columnspan=3, pady=5)

        # mode control
        ttk.Label(fr_m, text='Mode:', style="TLabel", anchor='e').grid(row=1, column=0, padx=5, sticky='E')
        self.mode_drop = guih.generate_drop_down(fr_m,
                                                   ["VDC", "VAC", "IDC", "IAC", "RES_2WIRE", "RES_4WIRE"])
        self.mode_drop[0].grid(row=1, column=1, pady=self.theme_config["size"]["ypad_s"])
        tk.Button(fr_m, text='Set', command=self.dmm_set_mode).grid(row=1, column=2, padx=5)

        # range control — dynamic buttons populated after connection
        self.fr_range = tk.Frame(fr_m, bg=self.theme_config["light_4"])
        self.btn_range_auto = tk.Button(self.fr_range, text="Auto Range", command=self.dmm_set_range_auto)
        self.btn_range_auto.grid(row=0, column=0, columnspan=2, pady=2)
        self.fr_range_buttons = tk.Frame(self.fr_range, bg=self.theme_config["light_4"])
        self.fr_range_buttons.grid(row=1, column=0, columnspan=2)
        self._range_labels = {}
        self.fr_range.grid(row=2, column=0, columnspan=3, pady=self.theme_config["size"]["ypad_s"])

        # sample rate control
        ttk.Label(fr_m, text='Rate:', style="TLabel", anchor='e').grid(row=3, column=0, padx=5, sticky='E')
        self.rate_drop = guih.generate_drop_down(fr_m, ["slow", "medium", "fast"])
        self.rate_drop[1].set(self.default_rate)
        self.rate_drop[0].grid(row=3, column=1, pady=self.theme_config["size"]["ypad_s"])
        tk.Button(fr_m, text='Set', command=self.dmm_set_rate).grid(row=3, column=2, padx=5)

        # reset button
        tk.Button(fr_m, text='Reset DMM',
                  command=self.dmm_reset,
                  bg=self.theme_config["warning"],
                  fg=self.theme_config["fg_dark"]).grid(row=4, column=0, columnspan=3, pady=(10, 2))

    def _show_secondary_display(self):
        self.labelFu2.grid(row=6, column=0, sticky='W', padx=5, pady=2)
        self.valueFu2.grid(row=6, column=1, sticky='W', padx=5, pady=2)
        self.btn_func2_toggle.grid(row=6, column=2, padx=3, pady=2)
        self.labelMeas2.grid(row=7, column=0, sticky='W', padx=5, pady=2)
        self.valueMeas2.grid(row=7, column=1, sticky='W', padx=5, pady=2)
        self._secondary_visible = True

    def _hide_secondary_display(self):
        self.labelFu2.grid_remove()
        self.valueFu2.grid_remove()
        self.btn_func2_toggle.grid_remove()
        self.labelMeas2.grid_remove()
        self.valueMeas2.grid_remove()
        self._secondary_visible = False

    def _refresh_measurements(self):
        """Read current measurements and update display."""
        if not self.fr_port.status:
            return
        try:
            self.dmm_Meas1 = self.cc.dmm.read_value()
        except COMMUNICATION_ERRORS:
            self.fr_port.status = False
            return
        self.dmm_Meas1 = self.dmm_Meas1 * self.meas1_scale

        if self._secondary_visible:
            try:
                val = self.cc.dmm.read_secondary_value()
                self.dmm_Meas2 = val if val is not None else ""
            except COMMUNICATION_ERRORS:
                self.dmm_Meas2 = ""

        self.valueMeas1.config(text=self.dmm_Meas1)
        self.valueMeas2.config(text=self.dmm_Meas2)

    def _refresh_settings(self):
        """Query and display current DMM settings (mode, range, sample speed)."""
        if not self.fr_port.status:
            return
        self.dmm_Range = self.cc.dmm.get_range()
        self.dmm_Fu1 = self.cc.dmm.get_mode()
        if self._secondary_visible:
            try:
                self.dmm_Fu2 = self.cc.dmm.get_secondary_mode()
            except COMMUNICATION_ERRORS:
                self.dmm_Fu2 = ""
        try:
            rate = self.cc.dmm.get_rate()
            if rate is not None:
                self.dmm_Rate = rate
        except COMMUNICATION_ERRORS:
            pass

        self.valueRange.config(text='{:8s}'.format(self.dmm_Auto + ':' + self.dmm_Range))
        self.valueFu1.config(text='{:8s}'.format(self.dmm_Fu1))
        self.valueFu2.config(text='{:8s}'.format(self.dmm_Fu2))
        self.valueRate.config(text=self.dmm_Rate)

    def gui_refresh_DMM(self):
        """Full refresh: settings then measurements."""
        self._refresh_settings()
        self._refresh_measurements()

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()
        if self.fr_port.status:
            if event == "auto":
                self._refresh_measurements()
            else:
                self.gui_refresh_DMM()


    ##############################################################################
    ####      DMM FUNCTIONS           ############################################
    ##############################################################################

    def toggle_func2(self):
        if self.cc.dmm is None:
            return
        try:
            current = self.cc.dmm.get_secondary_mode().strip()
        except COMMUNICATION_ERRORS:
            self.prompt.print("Failed to query FUNC2 state", "error")
            return

        if current == "NONe":
            self.cc.dmm.set_secondary_mode("FREQ")
            self.prompt.print("Secondary display set to FREQ")
        else:
            self.cc.dmm.set_secondary_mode("NONe")
            self.prompt.print("Secondary display turned off")
        self.gui_refresh_DMM()

    def set_meas1_unit(self):
        unit = self.unitMeas1_drop[1].get()
        self.prompt.print(f"Setting measurement 1 units to {unit}")
        if unit == "mV":
            self.meas1_scale = 1e3
        elif unit == "uV":
            self.meas1_scale = 1e6
        elif unit == "V":
            self.meas1_scale = 1

    def dmm_set_mode(self):
        if self.cc.dmm is not None:
            mode = self.mode_drop[1].get()
            self.prompt.print(f"Setting DMM mode to {mode}")
            self.cc.dmm.set_mode(mode)

    def build_range_controls(self):
        for widget in self.fr_range_buttons.winfo_children():
            widget.destroy()
        self._range_labels = {}

        if self.cc.dmm is None:
            return

        model = self.cc.dmm.model
        registry = self.cc.dmm.registry
        cmds = registry.commands.get(model, {}).get("command", {})
        range_keys = sorted(
            [k for k in cmds if k.startswith("range_") and k != "range_auto"],
            key=lambda x: int(x.split("_")[1])
        )

        # Load human-readable labels from [range_labels] section if available
        labels = registry.get_config_section(model, "range_labels")

        for i, key in enumerate(range_keys):
            n = int(key.split("_")[1])
            label = labels.get(key, f"range_{n}")
            self._range_labels[n] = label
            btn = tk.Button(self.fr_range_buttons, text=label,
                            width=20,
                            command=lambda num=n: self.dmm_set_range_n(num))
            btn.grid(row=i, column=0, padx=3, pady=1)

    def dmm_set_range_auto(self):
        if self.cc.dmm is not None:
            self.prompt.print("Setting DMM range to AUTO")
            self.cc.dmm.set_range_auto()

    def dmm_set_range_n(self, n):
        if self.cc.dmm is not None:
            label = self._range_labels.get(n, f"range_{n}")
            self.prompt.print(f"Setting DMM range: {label}")
            try:
                success = self.cc.dmm.set_range(n)
                if not success:
                    self.prompt.print(f"Range {n} not supported by {self.cc.dmm.model}", "warning")
            except COMMUNICATION_ERRORS as e:
                self.prompt.print(f"Range {n} error: {e}", "error")

    def dmm_set_rate(self):
        if self.cc.dmm is not None:
            rate = self.rate_drop[1].get()
            self.prompt.print(f"Setting DMM rate to {rate}")
            self.cc.dmm.set_rate(rate)
            self.dmm_Rate = rate
            self.valueRate.config(text=self.dmm_Rate)

    def dmm_reset(self):
        if self.cc.dmm is None:
            self.prompt.print("Reset failed: no DMM connected", "error")
            return
        try:
            cmd = self.cc.dmm.registry.get_command(self.cc.dmm.model, "command", "reset")
        except ValueError:
            self.prompt.print(f"Reset not supported for {self.cc.dmm.model} (no 'reset' entry in config.ini)", "warning")
            return
        try:
            self.cc.dmm.write(cmd)
            self.prompt.print(f"DMM reset ({cmd})")
            self.build_range_controls()
            self.gui_refresh_DMM()
        except COMMUNICATION_ERRORS as e:
            self.prompt.print(f"Reset command failed: {e}", "error")


    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()
        model_name = self.ate_drop[1].get()
        result = self.cc.dmm_service.connect(port, model_name)

        if not result.success:
            self.prompt.print(result.error, "error")
            guih.alert_user("Can't connect to DMM", result.error, "warning")
            self.fr_port.set_status(False)
            return False

        self.prompt.print(f"Connected to DMM with id: {result.device_id}")
        self.cc.dmm.set_rate(self.default_rate)
        self.dmm_Rate = self.default_rate
        self.prompt.print(f"DMM rate set to: {self.default_rate}")

        self.labelTimeConnectedValue.config(text=result.timestamp)
        self.labelIDValue.config(text=result.device_id)
        self.build_range_controls()

        if self.cc.dmm.has_capability("secondary_display"):
            self._show_secondary_display()
        else:
            self._hide_secondary_display()

        self.fr_port.set_status(True)
        self.gui_refresh("connect")

        if result.error:
            self.prompt.print(f"Warning: {result.error}", "warning")
        return True

    def port_close(self):
        self.prompt.print("Closing DMM resource!")
        result = self.cc.dmm_service.disconnect()
        if not result.success:
            guih.alert_user("Can't disconnect DMM", result.error, "warning")
        self.build_range_controls()
        self._hide_secondary_display()
        self.fr_port.set_status(False)

