"""
@file     guiTab_3_DMM.py
@author   Anders Bandt
@date     May 2024
@brief    control multimeter test equipment
"""


# import needed GUI packages
import tkinter
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
from EEequipment.xdm1041.xdm1041main import XDM1041, XDM1041Mode
from EEequipment.xdm1041 import xdm1041helper
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.guiTab_parent import ThemedFrame


class tabDMM(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file, autoconnect):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        # set up frames
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_rec = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_info.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        self.fr_rec.grid(row=1, column=0, pady=10, padx=10)

        # set up serial / DMM variables
        self.dmm = None
        self.dmm_id = None
        self.ser_status = False
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
        self.prompt = guic.Prompt(self, "DMM Console Output", height=21, width=140)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

        # set up port
        self.fr_port = guic.SerialConnFrame(
            self,
            self.cc,
            "DMM_Serial",
            self.port_init,
            self.port_close
        )
        self.fr_port.initialize_fr()
        if autoconnect:
            # TODO: add some timeout here
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, padx=30, pady=12)

    def initTabContent(self):
        print("Initializing tab 3 (DMM) content")
        self.init_fr_info()
        self.init_fr_rec()
        self.init_fr_PT100()
        # remaining initialisation and start of main loop
        # self.entryPort.focus_set()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='DMM_Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

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
        self.btn_update = ttk.Button(self.fr_info, text='UPDATE DMM', command=lambda: self.update_DMM(kind="full"))
        self.btn_update.grid(row=7, column=2, pady=5, padx=3, sticky='W')

    def init_fr_rec(self):
        fr_m = self.fr_rec
        ttk.Label(fr_m, text="Record DMM", style="TPinkLabel.TLabel").grid(row=0, column=0, pady=10, padx=15)

        self.labelRNums = ttk.Label(fr_m, text='', width=8, relief='sunken')
        self.labelRecFn = ttk.Label(fr_m, text='{:24s}'.format(self.recName), width=40, relief='sunken')
        self.labelRNums.grid(row=1, column=0, padx=10, pady=10, sticky='W')
        self.labelRecFn.grid(row=1, column=1, sticky='E')

        options = ['1s', '2s', '5s', '10s', '30s', '60s', '5m', '10m', '30m', '1h', '0.5s']
        self.optRecSpd, self.RecSpdVal = guih.generate_drop_down(fr_m, options)
        self.optRecSpd.grid(row=2, column=0, padx=3, sticky='W')
        self.btn_record = tk.Button(fr_m, text='RECORD THIS', command=self.record_DMM)
        self.btn_record.grid(row=2, column=3, pady=5, padx=3, sticky='W')

    def init_fr_PT100(self):
            self.optframe = tk.Frame(self)

            self.PT100UnitList = ('C', 'F', 'K')
            self.PT100UnitVal = tk.StringVar()
            self.PT100UnitVal.set(self.PT100UnitList[0])
            self.optPT100Unit = tk.OptionMenu(self.optframe, self.PT100UnitVal, *self.PT100UnitList,
                                              command=self.DoPT100Unit)
            self.buttonPT100 = tk.Button(self.optframe, text='PT100', bd=5, command=self.DoPT100, width=5)

            self.optPT100Unit.grid(row=0, column=0, sticky='W')
            self.buttonPT100.grid(row=0, column=1, sticky='W')

            self.optframe.grid(row=6, column=0, columnspan=2)

            self.PT100_On = False
            self.PT100_Unit = self.PT100UnitList[0]


    ##############################################################################
    ####      DMM FUNCTIONS           ############################################
    ##############################################################################

    def update_DMM(self, kind="partial"):
        print(f"Updating ({kind}) dmm ...")
        self.dmm_Meas1 = self.dmm.read_val1_str().strip("\n")
        self.dmm_Meas2 = self.dmm.read_val2_str().strip("\n")

        if kind == "full":
            self.dmm_Auto = self.dmm.get_range_auto()
            self.dmm_Range = self.dmm.get_range().strip("\n")
            self.dmm_Fu1 = self.dmm.get_func1()
            self.dmm_Fu2 = self.dmm.get_func2()

        self.gui_refresh("call")

    ##############################################################################
    ####      PT100 FUNCTIONS        ############################################
    ##############################################################################

    def DoPT100Unit(self, event=None):
        """
            changes the unit for PT100
        """
        self.PT100_Unit = self.PT100UnitVal.get()

    def DoPT100(self, event=None):
        """
            enables PT100 mode. i.e. we convert a 100+ ohm value into
            a temperature
        """
        if self.Fu1.upper() == 'RES' and self.Range.upper() == '500 OHM':
            self.PT100_On = not self.PT100_On
            if self.PT100_On:
                self.buttonPT100.config(relief='sunken')
            else:
                self.buttonPT100.config(relief='raised')
        else:
            tkmb.showinfo('info', 'switch to 500 Ohm RES mode with REL to compensate for wire res.')

    def update_PT100(self):
        def PT100_temp_convert(self, ohm, vnull=0.0):
            """
                convert a resistance reading of a standard PT100 probe to
                a temperature in celsius. The resistance must be >=100 Ohm
            """
            TC = 0.00385
            A = 3.9083E-03
            B = 5.775E-07
            C = -4.183E-12
            R0 = 100.0
            return (-A + math.sqrt(A * A - 4 * B * (1 - (ohm - vnull) / R0))) / (2 * B)

        if self.PT100_On:
            if self.Range.upper() == '500 OHM':
                if (self.Meas1 >= 100) and (self.Meas1 < 550):
                    self.Fu2 = 'PT100'
                    self.Meas2 = PT100_temp_convert(self.Meas1)
                    if self.PT100_Unit == 'F':
                        self.Meas2 = 32 + self.Meas2 * (9 / 5)
                    elif self.PT100_Unit == 'K':
                        self.Meas2 = 273.15 + self.Meas2

                else:
                    tkmb.showinfo('info', 'resistance out of range for PT100')
                    self.PT100_On = False
                    self.buttonPT100.config(relief='raised')

            else:
                tkmb.showinfo('info', 'must be in 500 Ohm range to use PT100')
                self.PT100_On = False
                self.buttonPT100.config(relief='raised')

    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    # starts the DMM recording
    def record_DMM(self):
        # conditionally STOP / START the recording
        if not self.record_status:
            if self.ser_status:
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

        while self.record_status and self.ser_status:
            print("Taking DMM measurement ...")
            val_str = self.cc.dmm.read_val1_str()
            print(f"Anders you're looking at this value string: {val_str}")

            # add row to data file
            if val_str is not None:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                self.csvh.add_row([timestamp, "xxx_range", "xxx_func", xdm1041helper.parse_voltage_str(val_str)])

                # update value counter
                self.recCnt += 1
                self.labelRNums.config(text='#{:7n}'.format(self.recCnt)) # TODO: this is not properly icncrement during recording

            time.sleep(self.record_speed)

        # if serial disconnect caused termination, call the start/stop record function
        if self.record_status:
            self.record_DMM()

        print("DMM record thread exiting.")

    # TODO: don't think "tab into page and auto call this" is working for the DMM
    def gui_refresh(self, event):
        # refresh DMM information
        if self.ser_status:
            if event == "auto":
                self.update_DMM("full")

        # update Label
        if self.ser_status:
            self.valueRange.config(text='{:8s}'.format(self.dmm_Auto + ':' + self.dmm_Range))
            self.valueFu1.config(text='{:8s}'.format(self.dmm_Fu1))
            self.valueMeas1.config(text=self.dmm_Meas1) # TODO: figure out how to use PrettyFloat on this (in data helper)
            self.valueFu2.config(text='{:8s}'.format(self.dmm_Fu2))
            self.valueMeas2.config(text=self.dmm_Meas2)


    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()

        self.dmm = XDM1041(port, XDM1041Mode.MODE_VOLTAGE_DC)
        time.sleep(1)
        self.dmm_id = self.dmm.test_conn()

        # BAD ID received
        if self.dmm_id == '' or self.dmm_id is None:
            self.prompt.print("Connection failed")
            self.dmm = None
            self.ser_status = False
            self.fr_port.set_status(self.ser_status)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False
        # GOOD ID received
        else:
            self.prompt.print("Connected to DMM")
            self.prompt.print(f"Got id: {self.dmm_id}")
            self.cc.set_dmm(self.dmm)
            self.cc.dmm.set_mode_dcv()
            self.cc.dmm.set_sample_speed_fast()

            self.gui_refresh("call")
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.labelIDValue.config(text=self.dmm_id)
            self.ser_status = True
            self.fr_port.set_status(self.ser_status)
            return True

    def port_close(self):
        # NOTE: added this Exception because we might call this after app is destroyed
        try:
            self.prompt.print(f"Serial close!")
        except tkinter.TclError:
            pass

        self.dmm.disconnect()
        self.ser_status = False
        self.fr_port.set_status(self.ser_status)

