"""Digital multimeter control and data acquisition tab."""

# import needed GUI packages
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb

# import needed packages
import time
import configparser
from datetime import datetime

# import user defined modules
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS
from common.path_helper import get_config_path
from gui import gui_helper as guih
from gui import gui_class as guic






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

        # Load DMM configuration
        self.default_sample_speed = self.load_dmm_config()

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
        self.fr_info.grid(row=0, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky='W')
        self.fr_control.grid(row=0, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_port.grid(row=0, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.prompt.grid(row=1, column=0, columnspan=4, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky='NSEW')

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def load_dmm_config(self):
        """Load DMM configuration from master.ini"""
        config = configparser.ConfigParser()
        config.read(get_config_path())

        # Get sample speed with default fallback
        sample_speed = "fast"  # Default value
        if "DMM" in config:
            sample_speed = config["DMM"].get("sample_speed", "fast").strip()

        # Validate the value
        valid_speeds = ["slow", "medium", "fast"]
        if sample_speed not in valid_speeds:
            print(f"Invalid DMM sample_speed '{sample_speed}' in config. Using 'fast'.")
            sample_speed = "fast"

        print(f"DMM default sample speed: {sample_speed}")
        return sample_speed

    def initTabContent(self):
        print("Initializing tab 3 (DMM) content")
        self.init_fr_info()
        self.init_fr_control()

    def init_fr_info(self):
        fr_m = self.fr_info

        self.labelInfo = ttk.Label(self.fr_info, text='DMM_Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("dmm")
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

        # Load and set previous model if available
        previous_model = self.cc.get_used_model("DMM_Serial")
        if previous_model and previous_model in self.registry:
            self.ate_drop[1].set(previous_model)
            print(f"Restored previous DMM model: {previous_model}")

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
        self.valueRange = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueFu1 = tk.Label(self.fr_info, width=9, text='', relief='sunken', anchor='w')
        self.valueMeas1 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueFu2 = tk.Label(self.fr_info, width=9, text='', relief='sunken', anchor='w')
        self.valueMeas2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')

        # add some drop-downs for unit handling
        self.unitMeas1_drop = guih.generate_drop_down(fr_m,
                                                   ["uV", "mV", "V"],
                                                   callback_func=self.set_meas1_unit)

        # Position the value labels
        self.valueRange.grid(row=3, column=1, sticky='W', padx=5, pady=2)
        self.valueFu1.grid(row=4, column=1, sticky='W', padx=5, pady=2)
        self.valueMeas1.grid(row=5, column=1, sticky='W', padx=5, pady=2)
        self.unitMeas1_drop[0].grid(row=5, column=2)
        self.valueFu2.grid(row=6, column=1, sticky='W', padx=5, pady=2)
        self.valueMeas2.grid(row=7, column=1, sticky='W', padx=5, pady=2)

        # ADD A REFRESH
        self.btn_update = tk.Button(self.fr_info, text='UPDATE DMM', command=lambda: self.gui_refresh_DMM(kind="full"))
        self.btn_update.grid(row=7, column=2, pady=5, padx=3, sticky='W')

    def init_fr_control(self):
        fr_m = self.fr_control

        labelInfo = ttk.Label(fr_m, text='DMM_Control', style="TPinkLabel.TLabel", width=15)
        labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # mode control
        self.mode_drop = guih.generate_drop_down(fr_m,
                                                   ["VDC", "VAC", "IDC", "IAC", "RES_2WIRE", "RES_4WIRE"],
                                                   callback_func=self.dmm_set_mode)

        self.range_drop = guih.generate_drop_down(fr_m,
                                                   ["AUTO", "LOWEST", "HIGHEST"],
                                                   callback_func=self.dmm_set_range)

        # sample rate control
        self.sample_drop = guih.generate_drop_down(fr_m,
                                                   ["slow", "medium", "fast"],
                                                   callback_func=self.dmm_set_sample)

        # Set the default sample speed from config
        self.sample_drop[1].set(self.default_sample_speed)

        self.mode_drop[0].grid(row=1 ,column=1, pady=self.theme_config["size"]["ypad_s"])
        self.range_drop[0].grid(row=2, column=1, pady=self.theme_config["size"]["ypad_s"])
        self.sample_drop[0].grid(row=3, column=1, pady=self.theme_config["size"]["ypad_s"])

    def gui_refresh_DMM(self, kind="partial"):
        if not self.fr_port.status:
            return

        self.dmm_Meas1 = self.cc.dmm.read_value()
        self.dmm_Meas1 = self.dmm_Meas1 * self.meas1_scale

        if kind == "full":
            self.dmm_Range = self.cc.dmm.get_range()
            self.dmm_Fu1 = self.cc.dmm.get_mode()

        # update Label
        if self.fr_port.status:
            self.valueRange.config(text='{:8s}'.format(self.dmm_Auto + ':' + self.dmm_Range))
            self.valueFu1.config(text='{:8s}'.format(self.dmm_Fu1))
            self.valueMeas1.config(text=self.dmm_Meas1)
            self.valueFu2.config(text='{:8s}'.format(self.dmm_Fu2))
            self.valueMeas2.config(text=self.dmm_Meas2)

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()

        # refresh DMM information
        if self.fr_port.status:
            if event == "auto":
                self.gui_refresh_DMM("full")


    ##############################################################################
    ####      DMM FUNCTIONS           ############################################
    ##############################################################################

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

    def dmm_set_range(self):
        if self.cc.dmm is not None:
            dmm_range = self.range_drop[1].get()
            self.prompt.print(f"Setting DMM range to {dmm_range}")
            self.cc.dmm.set_range(dmm_range)

    def dmm_set_sample(self):
        if self.cc.dmm is not None:
            sample_speed = self.sample_drop[1].get()
            self.prompt.print(f"Setting DMM sample speed to {sample_speed}")
            self.cc.dmm.set_sample_speed(sample_speed)


    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()

        ate_temp = self.registry[self.ate_drop[1].get()]
        dmm = ate_temp(self.fr_port.get_port())

        time.sleep(1)

        try:
            self.dmm_id = dmm.test_conn()
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't connect to DMM", e, "warning")
            self.fr_port.set_status(False)
            return False

        # BAD ID received
        if self.dmm_id == '' or self.dmm_id is None:
            self.prompt.print("Connection failed", "error")
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False
        # GOOD ID received
        else:
            self.prompt.print("Connected to DMM")
            self.prompt.print(f"Got id: {self.dmm_id}")
            self.cc.set_dmm(dmm)

            # Set sample speed from config
            self.cc.dmm.set_sample_speed(self.default_sample_speed)
            self.prompt.print(f"DMM sample speed set to: {self.default_sample_speed}")

            # Save the selected model for next time
            selected_model = self.ate_drop[1].get()
            self.cc.set_used_model(selected_model, "DMM_Serial")

            self.gui_refresh("call")
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.labelIDValue.config(text=self.dmm_id)
            self.fr_port.set_status(True)
            return True

    def port_close(self):
        self.prompt.print(f"Closing DMM resource!")
        try:
            self.cc.dmm.disconnect()
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't disconnect PS", e, "warning")
        self.fr_port.set_status(False)
        self.cc.set_dmm(None)

