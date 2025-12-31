"""
@file     guiTab_3_DMM.py
@author   Anders Bandt
@date     May 2024
@brief    control multimeter test equipment
"""


# import needed GUI packages
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb

# import needed packages
import threading
import time
from time import localtime, strftime
import math
from datetime import datetime

# import user defined modules
from analysis.csv_helper import CSVHelper
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS
from EEequipment.XDM1041 import xdm1041helper # TODO: phase out this import module
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

        # set up serial / DMM variables
        self.dmm = None
        self.dmm_id = None
        self.dmm_Auto = ''
        self.dmm_Range = ''
        self.dmm_Fu1 = ''
        self.dmm_Meas1 = ''
        self.dmm_Fu2 = ''
        self.dmm_Meas2 = ''

        # set up recording information
        self.record_speed = 1
        self.record_status = False
        self.recCnt = 0
        self.recName = ''
        self.data_dir = "data/dmm_data/"
        self.csvh = None

        # set up prompt
        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                   "DMM Console Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])

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
            port_func=2
        )
        self.fr_port.initialize_fr()
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, padx=30, pady=12)

        # place Frames into grid
        self.fr_info.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        self.fr_control.grid(row=1, column=0, pady=10, padx=10)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

    def initTabContent(self):
        print("Initializing tab 3 (DMM) content")
        self.init_fr_info()
        self.init_fr_control()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='DMM_Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("dmm")
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

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

        # Position the value labels
        self.valueRange.grid(row=3, column=1, sticky='W', padx=5, pady=2)
        self.valueFu1.grid(row=4, column=1, sticky='W', padx=5, pady=2)
        self.valueMeas1.grid(row=5, column=1, sticky='W', padx=5, pady=2)
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


        self.mode_drop[0].grid(row=1 ,column=1, pady=self.theme_config["size"]["ypad_s"])
        self.range_drop[0].grid(row=2, column=1, pady=self.theme_config["size"]["ypad_s"])
        self.sample_drop[0].grid(row=3, column=1, pady=self.theme_config["size"]["ypad_s"])

    # TODO: for this and PS. How can I add some dynamic unit conversions?
    def gui_refresh_DMM(self, kind="partial"):
        if not self.fr_port.status:
            return

        # TODO: let's figure out how to add all of these things back with my new abstraction
        self.dmm_Meas1 = self.dmm.read_value()
        # self.dmm_Meas2 = self.dmm.read_val2_str().strip("\n")

        if kind == "full":
            pass
            # self.dmm_Auto = self.dmm.get_range_auto()
            # self.dmm_Range = self.dmm.get_range().strip("\n")
            # self.dmm_Fu1 = self.dmm.get_func1()
            # self.dmm_Fu2 = self.dmm.get_func2()

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

    def dmm_set_mode(self):
        if self.dmm is not None:
            mode = self.mode_drop[1].get()
            self.prompt.print(f"Setting DMM mode to {mode}")
            self.dmm.set_mode(mode)

    def dmm_set_range(self):
        if self.dmm is not None:
            dmm_range = self.range_drop[1].get()
            self.prompt.print(f"Setting DMM range to {dmm_range}")
            self.dmm.set_range(dmm_range)

    def dmm_set_sample(self):
        if self.dmm is not None:
            sample_speed = self.sample_drop[1].get()
            self.prompt.print(f"Setting DMM sample speed to {sample_speed}")
            self.dmm.set_sample_speed(sample_speed)


    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    # starts the DMM recording
    def record_DMM(self):
        # conditionally STOP / START the recording
        if not self.record_status:
            if self.fr_port.status:
                # SETUP DMM
                # self.cc.dmm.set_range_auto() # ensure we are in AUTO mode

                # START RECORDING
                self.change_record_speed()
                self.recName = 'AREC_' + strftime('%Y%m%d%H%M%S', localtime()) + '.csv'
                self.prompt.print(f"Starting DMM record every {self.record_speed} seconds ...")
                self.csvh = CSVHelper(self.data_dir + self.recName)
                self.csvh.initialize_file(["Time", "Range", "Func1", "Meas1"])

                self.btn_record.config(relief='sunken')
                self.labelRecFn.config(text='{:24s}'.format(self.recName))
                self.recCnt = 0
                self.labelRNums.config(text='#{:7n}'.format(self.recCnt))

                # start the thread
                self.record_status = True
                threading.Thread(target=lambda: self.thread_record_dmm()).start()
            else:
                guih.alert_user("Can't start record!", "DMM connection is not valid!", "error")
        else:
            # STOP RECORDING
            self.prompt.print("Stopped DMM record !")
            self.record_status = False
            self.btn_record.config(relief='raised')

        # successful exit of record function
        return True

    def change_record_speed(self):
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

    #################################
    #### THREADS SHIT    ############
    #################################

    def thread_record_dmm(self):
        print("Starting DMM record!")

        while self.record_status and self.fr_port.status:
            print("Taking DMM measurement ...")
            val_str = self.cc.dmm.read_val1_str()
            print(f"\tDMM: {val_str}")

            # add row to data file
            if val_str is not None:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                self.csvh.add_row([timestamp, "xxx_range", "xxx_func", xdm1041helper.parse_voltage_str(val_str)])

                # update value counter
                self.recCnt += 1
                self.labelRNums.config(text='#{:7n}'.format(self.recCnt))

            time.sleep(self.record_speed)

        # if serial disconnect caused termination, call the start/stop record function
        if self.record_status:
            self.record_DMM()

        print("DMM record thread exiting.")

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()

        ate_temp = self.registry[self.ate_drop[1].get()]
        self.dmm = ate_temp(self.fr_port.get_port())

        time.sleep(1)

        try:
            self.dmm_id = self.dmm.test_conn()
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't connect to DMM", e, "warning")
            self.fr_port.set_status(False)
            return False

        # BAD ID received
        if self.dmm_id == '' or self.dmm_id is None:
            self.prompt.print("Connection failed")
            self.dmm = None
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False
        # GOOD ID received
        else:
            self.prompt.print("Connected to DMM")
            self.prompt.print(f"Got id: {self.dmm_id}")
            self.cc.set_dmm(self.dmm)

            self.cc.dmm.set_sample_speed("fast")

            self.gui_refresh("call")
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.labelIDValue.config(text=self.dmm_id)
            self.fr_port.set_status(True)
            return True

    def port_close(self):
        # NOTE: added this Exception because we might call this after app is destroyed
        try:
            self.prompt.print(f"Serial close!")
        except tk.TclError:
            pass

        self.dmm.disconnect()
        self.fr_port.set_status(False)

