"""
@file     guiTab_3_DMM.py
@author   Anders Bandt
@date     May 2024
@brief    control multimeter test equipment
"""

# import needed GUI packages
import tkinter as tk
import tkinter.scrolledtext as tkst
import tkinter.messagebox as tkmb
import tkinter.font as tkFont  # TODO: let's figure out how to use this

# import needed packages
from collections import namedtuple
import threading
import time
from time import localtime, strftime, perf_counter_ns
import math
from datetime import datetime


# import user defined modules
from data.csv_helper import CSVHelper
from EEequipment.xdm1041.xdm1041main import XDM1041, XDM1041Mode
from EEequipment.xdm1041 import xdm1041helper
from gui import gui_helper as guih
from gui import gui_class as guic


class tabDMM:
    def __init__(self, master, class_controller, basefilepath):
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.frame = tk.Frame(self.master)
        self.frame.grid(row=0, column=0)
        self.fr_rec = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_rec.grid(row=5, column=0, pady=10, padx=10)

        # set up serial / DMM variables
        self.ser_status = False

        # set up recording information
        self.record_speed = 1
        self.record_status = False
        self.recCnt = 0
        self.recName = ''
        self.data_dir = "data/dmm_data/"
        self.csvh = None

        # set up prompt
        # self.fr_prompt = tk.Frame(self.frame, bg="gray")
        # self.fr_prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)
        self.prompt = guic.Prompt(self.frame, "DMM Console Output", height=25, width=140)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        # the overall structure is aranged in 6 rows
        #  row	use
        #    0  port
        #    1  id
        #    2  recording status monitor
        #    3  labels for values
        #    4  values
        #    5  recording control
        #    6  options
        print("Initializing tab 3 (DMM) content")
        self.init_fr_port()
        self.init_fr_info()
        self.init_fr_rec()
        self.init_fr_PT100()

        # remaining intitalisation and start of main loop
        # self.entryPort.focus_set()
        self.PollCount = 0
        self.ProgStart = perf_counter_ns()
        # self.PollMiniBM()

    def init_fr_port(self):
        self.fr_port = guic.SerialConnFrame(self.frame,
                                            "DMM Serial",
                                            self.connect_serial,
                                            self.serial_close,
                                            bg="#00bcd4")
        self.fr_port.initialize_fr()
        self.fr_port.grid(row=0, column=1, padx=30, pady=12)

    def init_fr_info(self):
        # row 1: id split into 2 columns
        #  (8)                  (40)               = 48
        #   0                     1
        #  time             id (as reported)
        self.idframe = tk.Frame(self.frame)
        self.labeltime = tk.Label(self.idframe, width=8, text='', relief='sunken')
        self.labelId = tk.Label(self.idframe, width=40, text='', relief='sunken')
        self.labeltime.grid(row=0, column=0, sticky='E')
        self.labelId.grid(row=0, column=1, sticky='E')
        self.idframe.grid(row=1, column=0, columnspan=2)

        # row 4: labels split into 5 columns
        #   (10)     (9)     10)    (9)     (10)    = 48
        #     0       1       3      4       5
        #   range   fu1    meas1    fu2     meas2
        self.labelframe = tk.Frame(self.frame)

        self.labelRange = tk.Label(self.labelframe, width=10, text='Range')
        self.labelFu1 = tk.Label(self.labelframe, width=9, text='Func1')
        self.labelMeas1 = tk.Label(self.labelframe, width=10, text='Meas1')
        self.labelFu2 = tk.Label(self.labelframe, width=9, text='Func2')
        self.labelMeas2 = tk.Label(self.labelframe, width=10, text='Meas2')
        self.labelRange.grid(row=0, column=0, sticky='W')
        self.labelFu1.grid(row=0, column=1, sticky='W')
        self.labelMeas1.grid(row=0, column=2, sticky='W')
        self.labelFu2.grid(row=0, column=3, sticky='W')
        self.labelMeas2.grid(row=0, column=4, sticky='W')
        self.labelframe.grid(row=3, column=0, columnspan=5)

        # row 5: values split into 5 columns
        #   (10)     (9)     10)    (9)     (10)    = 48
        #     0       1       3      4       5
        #   range   fu1    meas1    fu2     meas2
        self.valueframe = tk.Frame(self.frame)

        self.valueRange = tk.Label(self.valueframe, width=10, text='', relief='sunken')
        self.valueFu1 = tk.Label(self.valueframe, width=9, text='', relief='sunken')
        self.valueMeas1 = tk.Label(self.valueframe, width=10, text='', relief='sunken')
        self.valueFu2 = tk.Label(self.valueframe, width=9, text='', relief='sunken')
        self.valueMeas2 = tk.Label(self.valueframe, width=10, text='', relief='sunken')
        self.valueRange.grid(row=0, column=0, sticky='W')
        self.valueFu1.grid(row=0, column=1, sticky='W')
        self.valueMeas1.grid(row=0, column=2, sticky='W')
        self.valueFu2.grid(row=0, column=3, sticky='W')
        self.valueMeas2.grid(row=0, column=4, sticky='W')
        self.valueframe.grid(row=4, column=0, columnspan=5)

    def init_fr_rec(self):
        fr_m = self.fr_rec

        self.labelRNums = tk.Label(fr_m, text='', width=8, relief='sunken')
        self.labelRecFn = tk.Label(fr_m, text='{:24s}'.format(self.recName), width=40, relief='sunken')
        self.labelRNums.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        self.labelRecFn.grid(row=0, column=1, sticky='E')

        options = ['1s', '2s', '5s', '10s', '30s', '60s', '5m', '10m', '30m', '1h']
        self.optRecSpd, self.RecSpdVal = guih.generate_drop_down(fr_m, options)
        self.btn_record = tk.Button(fr_m, text='RECORD THIS', bd=5, command=self.record_DMM, width=12)
        self.optRecSpd.grid(row=1, column=0, padx=3, sticky='W')
        self.btn_record.grid(row=1, column=3, pady=5, padx=3, sticky='W')

    def init_fr_PT100(self):
            #        (8)      (10)   (10)   (10)   (10)        = 48
            #         0        1      2      3       4
            #   0   PT100Unit PT100
            self.optframe = tk.Frame(self.frame)

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

    def update_DMM(self):
        self.dmm_Auto = self.dmm.get_range_auto()
        self.dmm_Range = None
        self.dmm_Fu1 = None
        self.dmm_Fu2 = None
        self.dmm_Meas1 = self.dmm.read_val1_str()
        self.dmm_Meas2 = self.dmm.read_val2_str()


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
                self.cc.dmm.set_range_auto() # ensure we are in AUTO mode

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
                self.record_status = True

                # start the thread
                threading.Thread(target=lambda: self.thread_record_dmm()).start()
            else:
                guih.alert_user("Can't start record!", "DMM connection is not valid!", "error")
        else:
            # STOP RECORDING
            self.prompt.print("Stopped DMM record !")
            self.labelRNums.config(text='')
            self.btn_record.config(relief='raised')
            self.record_status = False

        # successful exit of record function
        return True

    def change_record_speed(self):
        # changes the recording speed
        try:
            self.record_speed = self.parse_time_to_seconds(self.RecSpdVal.get())
        except Exception as e:
            raise e

    #################################
    #### THREADS SHIT    ############
    #################################

    def thread_record_dmm(self):
        print("Starting DMM record!")
        while self.record_status and self.ser_status:
            print("Taking DMM measurement ...")
            val_str = self.cc.dmm.read_val1_str()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            self.csvh.add_row([timestamp, "xxx_range", "xxx_func", xdm1041helper.parse_voltage_str(val_str)])
            self.recCnt += 1
            time.sleep(self.record_speed)

        # if serial disconnect caused termination, call the start/stop record function
        if self.record_status:
            self.record_DMM()

        print("DMM record thread exiting.")


    def gui_refresh(self):
        self.valueRange.config(text='{:8s}'.format(self.dmm_Auto + ':' + self.dmm_Range))
        self.valueFu1.config(text='{:8s}'.format(self.dmm_Fu1))
        self.valueMeas1.config(text=self.PrettyFloat(self.dmm_Meas1))
        self.valueFu2.config(text='{:8s}'.format(self.dmm_Fu2))
        self.valueMeas1.config(text=self.PrettyFloat(self.dmm_Meas2))


    #################################
    #### SERIAL (COM)  ##############
    #################################

    def connect_serial(self, event=None):
        port = self.fr_port.get_port()

        self.dmm = XDM1041(port, XDM1041Mode.MODE_VOLTAGE_DC, 1)
        self.dmm_id = self.dmm.test_conn()

        self.prompt.print("Connected to DMM")
        self.prompt.print(f"Got id: {self.dmm_id}")

        # BAD ID received
        if self.dmm_id == '' or len(self.id) < 3:
            self.dmm = None
            self.ser_status = False
            self.fr_port.set_status(self.ser_status)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
        # GOOD ID received
        else:
            self.cc.set_dmm(self.dmm)
            self.cc.dmm.set_sample_speed_fast()
            self.gui_refresh()
            self.labelId.config(text=self.dmm_id)
            self.ser_status = True
            self.fr_port.set_status(self.ser_status)

    def serial_close(self):
        self.prompt.print(f"Serial close!")
        self.dmm.disconnect()
        self.ser_status = False
        self.fr_port.set_status(self.ser_status)


    #################################
    #### HELPER        ##############
    #################################

    def parse_time_to_seconds(self, time_str):
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