"""
@file     guiTab_6_PS.py
@author   Anders Bandt
@date     May 2024
@brief    control power supply test equipment
"""

# import needed GUI packages
import tkinter as tk
import tkinter.scrolledtext as tkst
import tkinter.messagebox as tkmb

# import needed packages
import time
from time import localtime, strftime, perf_counter_ns


# import user defined modules
from EEequipment.spd3303x import SPD3303X
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.guiTab_parent import ThemedFrame


class tabPS(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)
        self.fr_control = tk.Frame(self, bg="#00bcd4")
        self.fr_control.grid(row=0, column=0, pady=10, padx=10)

        # set up serial / PS variables
        self.ps = None
        self.conn_status = False # TODO: rename all the other frames "connection" variable to align with this one
        self.ch1_on = False
        self.ch2_on = False

        # set up prompt
        # self.fr_prompt = tk.Frame(self, bg="gray")
        # self.fr_prompt
        self.prompt = guic.Prompt(self, "PS Console Output", height=25, width=140)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 6 (PS) content")
        self.init_fr_port()
        self.init_fr_control()

    def init_fr_port(self):
        self.fr_port = guic.SerialConnFrame(self,
                                            "Power supply PyVISA",
                                            self.connect_pyvisa,
                                            self.disconnect_pyvisa,
                                            port_func=3,
                                            bg="#00bcd4")
        self.fr_port.initialize_fr()
        self.fr_port.grid(row=0, column=1, padx=30, pady=12)

    def init_fr_control(self):
        fr_m = self.fr_control

        # TODO: just add some direct ON and OFF buttons to ensure that I don't get messed with the toggle
        # CHANNEL 1 CONTROLS
        self.ch1_label = tk.Label(fr_m, text="Channel 1")
        self.ch1_label.grid(row=0, column=0, padx=10, pady=10)

        self.ch1_voltage = tk.Entry(fr_m)
        self.ch1_voltage.grid(row=0, column=1, padx=10, pady=10)

        self.ch1_set_btn = tk.Button(fr_m, text="Set Voltage", command=lambda: self.set_voltage(1,
                                                                                                     self.ch1_voltage.get()))
        self.ch1_set_btn.grid(row=0, column=2, padx=10, pady=10)

        self.ch1_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(1))
        self.ch1_toggle_btn.grid(row=0, column=3, padx=10, pady=10)

        # CHANNEL 2 CONTROLS
        self.ch2_label = tk.Label(fr_m, text="Channel 2")
        self.ch2_label.grid(row=1, column=0, padx=10, pady=10)

        self.ch2_voltage = tk.Entry(fr_m)
        self.ch2_voltage.grid(row=1, column=1, padx=10, pady=10)

        self.ch2_set_btn = tk.Button(fr_m, text="Set Voltage", command=lambda: self.set_voltage(2,
                                                                                                     self.ch2_voltage.get()))
        self.ch2_set_btn.grid(row=1, column=2, padx=10, pady=10)

        self.ch2_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(2))
        self.ch2_toggle_btn.grid(row=1, column=3, padx=10, pady=10)

        # Status display
        self.status_label = tk.Label(fr_m, text="Status:")
        self.status_label.grid(row=2, column=0, columnspan=4, padx=10, pady=10)


    # NOTE: this function is quite similar to the relay one in tab 1
    def gui_refresh_channel_state(self):
        if self.ps is not None:
            status_decode = self.ps.check_status()
        else:
            return

        if status_decode["ch1_state"] == "ON":
            self.ch1_toggle_btn.config(bg="green")
        else:
            self.ch1_toggle_btn.config(bg="red")

        if status_decode["ch2_state"] == "ON":
            self.ch2_toggle_btn.config(bg="green")
        else:
            self.ch2_toggle_btn.config(bg="red")

    #################################
    #### ACTION FUNCTIONS  ##########
    #################################

    def toggle_channel(self, channel):
        if channel == 1:
            if self.ch1_on is True:
                self.ps.output_off(channel)
                self.ch1_on = False
            else:
                self.ps.output_on(channel)
                self.ch1_on = True
        elif channel == 2:
            if self.ch2_on is True:
                self.ps.output_off(channel)
                self.ch2_on = False
            else:
                self.ps.output_on(channel)
                self.ch2_on = True
        else:
            raise Exception("Wrong channel input")

        self.gui_refresh_channel_state()

    def set_voltage(self, channel, voltage_str):
        if self.ps is not None:
            # have to format input text box into float
            voltage = float(voltage_str)
            self.ps.set_voltage(channel, voltage)
        else:
            guih.alert_user("Can't set voltage", "No PS connection!", "alert")


    #################################
    #### SERIAL (COM)  ##############
    #################################

# TODO: same thing with these functions. Standardize the "connection" variables for each tab
    def connect_pyvisa(self, event=None):
        self.prompt.print("Connect to PYVISA resource!")
        port = self.fr_port.get_port()

        self.ps = SPD3303X.SPD3303X(port)
        self.id = self.ps.test_conn()
        if self.id is not False:
            self.prompt.print(f"Connected to PS with id: {self.id}")
            self.cc.set_ps(self.ps)
            # self.labelId.config(text=self.id)
            self.ser_status = True
            self.fr_port.set_status(self.ser_status)
            self.ps.output_off(1)
            self.ps.output_off(2)
            self.ch1_on = 0
            self.ch2_on = 0
            self.gui_refresh_channel_state()

        else: # BAD ID received
        # if self.id == '' or len(self.id) < 3:
            self.ps = None
            self.ser_status = False
            self.fr_port.set_status(self.ser_status)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")


    def disconnect_pyvisa(self):
        self.prompt.print(f"Close PYVISA resource!")
        self.ps.close()
        self.ser_status = False
        self.fr_port.set_status(self.ser_status)

