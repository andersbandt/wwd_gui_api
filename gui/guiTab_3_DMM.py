"""
@file     guiTab_3_DMM.py
@author   Anders Bandt
@date     May 2024
@brief    control multimeter test equipment
"""

# import needed GUI packages
import tkinter as tk
from tkinter import *
from tkinter import ttk
import tkinter.scrolledtext as tkst
import tkinter.filedialog as tkfd
import tkinter.messagebox as tkmb
import tkinter.font as tkFont

# import needed packages
from collections import namedtuple
import threading
import time
from time import localtime, strftime, perf_counter_ns
import math


# import user defined modules
from data.csv_helper import CSVHelper
# from EEequipment.xdm1041.xdm1041defs import XDM1041Mode, XDM1041Cmd
# from EEequipment.xdm1041.xdm1041main import XDM1041

from EEequipment import xdm1041

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

        self.dmm = None
        self.record_speed = 1
        self.ser_status = False

        # set up recording information
        self.recording = False
        self.data_dir = "data/dmm_data/"
        self.csvh = None

        # set up prompt
        self.fr_prompt = tk.Frame(self.frame, bg="gray")
        self.fr_prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)
        self.prompt = guic.Prompt(self.fr_prompt, "DMM Console Output", "black", height=25, width=140)

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

        # row 3: rec status monitor split into 2 columns
        #
        #        (8)           (40)                         = 48
        #         0              1
        #   0   #recs         <filename>
        self.recmon = tk.Frame(self.frame)
        self.RecName = ''
        self.labelRNums = tk.Label(self.recmon, text='', width=8, relief='sunken')
        self.labelRecFn = tk.Label(self.recmon, text='{:24s}'.format(self.RecName), width=40, relief='sunken')
        self.labelRNums.grid(row=0, column=0, sticky='W')
        self.labelRecFn.grid(row=0, column=1, sticky='E')
        self.recmon.grid(row=2, column=0, columnspan=2)

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

        self.Range = ''
        self.Fu1 = ''
        self.Fu1Old = ''
        self.Meas1 = 0
        self.Fu2 = ''
        self.Meas2 = 0
        self.Auto = ''

    def init_fr_rec(self):
        fr_m = self.fr_rec
        options = ['1s', '2s', '5s', '10s', '30s', '60s', '5m', '10m', '30m', '1h']
        self.optRecSpd, self.RecSpdVal = guih.generate_drop_down(fr_m, options)
        self.btn_record = tk.Button(fr_m, text='RECORD THIS', bd=5, command=self.record_DMM, width=12)
        self.optRecSpd.grid(row=0, column=0, sticky='W')
        self.btn_record.grid(row=0, column=3, sticky='W')

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
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def GetResponse(self, Cmd, Numeric=False):
        """
            sends a command (that will trigger a response) and returns
            that response

            Because of bugs in the XDM1041, it may sometimes timeout and
            sometimes return multiple responses. For timeouts, a "?" is
            returned. Multiple responses are discarded.

            It also translates some of the weird characters send by the
            XDM1041 for non-ASCII chars
        """
        Successful = False
        n = 0
        while not Successful:
            s = self.dmm.send_cmd(Cmd)
            print(f"Anders your response says {s}")

            if s != '':
                if Numeric:
                    try:
                        v = float(s)
                        Successful = True
                        Res = v
                    except ValueError:
                        Successful = True
                        Res = 0
                else:
                    Successful = True
                    if s.endswith('\\xa6\\xb8'):
                        s = s[:-8] + 'Ohm'
                    elif s.endswith('\\xa6\\xccF'):
                        s = s[:-9] + 'uF'
                    elif s.endswith('"'):
                        s = s.strip('"')
                    Res = s
            else:
                # print('nothing'+str(n))
                sleep(0.1)
                n = n + 1
                if n > 5:
                    if Numeric:
                        Res = 0
                    else:
                        Res = '?'
                    break
        # print(Cmd+str(Res))
        return Res


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


    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    # starts the DMM recording
    def record_DMM(self):

        # conditionally STOP / START the recording
        if not self.recording:
            if self.ser_status:
                self.change_record_speed()
                self.prompt.print(f"Starting DMM record every {self.record_speed} seconds ...")
                self.csvh = CSVHelper(self.data_dir + 'AREC_' + strftime('%Y%m%d%H%M%S', localtime()) + '.csv')
                self.csvh.initialize_file(["Time", "Range", "Func1", "Meas1"])
                # self.PollCount = 0
                # self.RecNums = 0

                self.labelRecFn.config(text='{:24s}'.format(self.RecName))
                # self.labelRNums.config(text='#{:7n}'.format(XXXXXX))
                self.recording = True

                # start the thread
                threading.Thread(target=lambda: self.thread_record_dmm()).start()
            else:
                guih.alert_user("Can't start record!", "DMM connection is not valid!", "error")
                # tkmb.showerror("rec error", "can't create " + self.RecName) # TODO: compare this error method to my alert method
        else:
            self.prompt.print("Stopped DMM record !")
            self.labelRNums.config(text='')
            self.btn_record.config(relief='raised')
            self.recording = False

        # successful exit of record function
        return True


    # changes the recording speed
    def change_record_speed(self):
        try:
            self.record_speed = self.parse_time_to_seconds(self.RecSpdVal.get())
        except Exception as e:
            raise(e)


    # polls the meter every 1 second. The time is adjusted to maintain accuracy
    def PollMiniBM(self, event=None):

        def WriteRec(n, m2):
            """
                write a record to the recording file
            """
            self.f.write('{:5n},{:10s},{:10s},{:10s},{:10s},{:10s}\n'.format(
                n,
                self.Auto + ':' + self.Range,
                self.Fu1,
                str(self.Meas1),
                self.Fu2,
                m2))
            self.RecNums += 1

        def PT100(ohm, vnull=0.0):
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

        if self.dmm != None:
            self.PollCount += 1
            self.labeltime.config(text='{:8n}'.format(self.PollCount))
            err = False
            try:
                self.Meas1 = self.GetResponse('MEAS1?', Numeric=True)
                self.Auto = 'A' if self.GetResponse('AUTO?') == '1' else 'M'
                self.Fu1 = self.GetResponse('FUNC1?')
                if (self.Fu1.upper() == 'DIOD' or self.Fu1.upper() == 'CONT'):
                    self.Range = ''
                else:
                    self.Range = self.GetResponse('RANGE?')

                if self.Fu1.upper().endswith('AC'):
                    self.Fu2 = self.GetResponse('FUNC2?')
                    if self.Fu2.upper() == 'NONE':
                        self.Fu2 = ''
                    else:
                        self.Meas2 = self.GetResponse('MEAS2?', Numeric=True)
                        #
                        # bug fix: the XDM1041 scales the frequency wrongly
                        #
                        if self.Range.endswith('mV'):
                            self.Meas2 = self.Meas2 * 1000
                        elif self.Range.endswith('uA'):
                            self.Meas2 = self.Meas2 * 1000000
                        elif self.Range.endswith('mA'):
                            self.Meas2 = self.Meas2 * 1000
                else:
                    self.Fu2 = ''
                    self.Meas2 = 0

                if self.Fu1Old.upper() == 'RES' and self.Fu1.upper() != 'RES':
                    self.PT100_On = False
                    self.buttonPT100.config(relief='raised')

                self.Fu1Old = self.Fu1

            except:
                err = True
                raise
            if err:
                tkmb.showerror("comms error", "lost connection ")
                self.frame.quit()
            else:
                if self.PT100_On:
                    if self.Range.upper() == '500 OHM':
                        if (self.Meas1 >= 100) and (self.Meas1 < 550):
                            self.Fu2 = 'PT100'
                            self.Meas2 = PT100(self.Meas1)
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

                self.valueRange.config(text='{:8s}'.format(self.Auto + ':' + self.Range))
                self.valueFu1.config(text='{:8s}'.format(self.Fu1))
                self.valueMeas1.config(text=self.PrettyFloat(self.Meas1))
                self.valueFu2.config(text='{:8s}'.format(self.Fu2))
                m2 = ''
                if self.Fu2 != '':
                    m2 = self.PrettyFloat(self.Meas2)
                self.valueFu2.config(text='{:8s}'.format(self.Fu2))
                self.valueMeas2.config(text=m2)

                if self.RecName != '':
                    if self.ARec_On:
                        if self.PollCount % self.RecSpd == 0:
                            WriteRec(self.PollCount, m2)
                    elif self.MRec_On:
                        if self.Man_On:
                            WriteRec(self.RecNums + 1, m2)
                            self.Man_On = False
                            self.buttonMan.config(relief='raised')

                    self.labelRNums.config(text='{:8n}'.format(self.RecNums))

        elapsed = (perf_counter_ns() - self.ProgStart) // 1000000  # time in ms since start
        # time2sleep = 1000 - (elapsed % 1000)
        time2sleep = 5*1000
        self.frame.after(time2sleep, self.PollMiniBM)



    #################################
    #### THREADS SHIT    ############
    #################################

    def thread_record_dmm(self):
        print("Starting DMM record!")
        while self.recording:
            print("Taking DMM measurement ...")
            val = self.cc.dmm.read_val1_str()
            self.csvh.add_row("xxx_time", "xxx_range", "xxx_func", xdm1041)
            time.sleep(self.record_speed)


    #################################
    #### SERIAL (COM)  ##############
    #################################

    def connect_serial(self, event=None):
        port = self.fr_port.get_port()

        self.dmm = XDM1041(port, XDM1041Mode.MODE_VOLTAGE_DC, 1)
        self.id = self.dmm.test_conn()

        self.prompt.print("Connected to DMM")
        self.prompt.print(f"Got id: {self.id}")

        # BAD ID received
        if self.id == '' or len(self.id) < 3:
            self.dmm = None
            self.ser_status = False
            self.fr_port.set_status(self.ser_status)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
        # GOOD ID received
        else:
            # self.buttonConn.config(relief='sunken')
            self.cc.set_dmm(self.dmm)
            self.labelId.config(text=self.id)
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