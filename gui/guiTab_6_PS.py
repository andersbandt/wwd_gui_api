"""
@file     guiTab_6_PS.py
@author   Anders Bandt
@date     May 2024
@brief    control power supply test equipment
"""

# import needed GUI packages
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb

# import needed packages
import logging
import time
from datetime import datetime
import pyvisa.errors

import EEequipment.E3640A.E3640A
from analysis.csv_helper import CSVHelper
import configparser
import os

# import user defined modules
from common import plotter
from EEequipment.SPD3303X import SPD3303X

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle
from gui.guiTab_parent import ThemedFrame


class TabPS(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file, autoconnect):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        self.fr_port = None
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_status = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up serial / PS variables
        self.ps = None
        self.id = None
        self.ch1_on = False
        self.ch2_on = False
        self.ps_v1s = "?"
        self.ps_v2s = "?"
        self.ps_v1r = 0
        self.ps_v2r = 0
        self.ps_i1 = 0
        self.ps_i2 = 0

        # set up recording / data information
        self.recName = False
        self.data_dir = "data/ps_data/"

        # set up prompt
        self.prompt = guic.Prompt(self, "PSConsole Output", height=18, width=140)

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_info.grid(row=0, column=0, pady=15, padx=15)
        self.fr_control.grid(row=1, column=0, pady=15, padx=15)
        self.fr_status.grid(row=1, column=1, pady=15, padx=15)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.cc,
                                            "PS_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3)
        self.fr_port.initialize_fr()
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, padx=15, pady=15)

    def initTabContent(self):
        print("Initializing tab 6 (PS) content")
        self.init_fr_info()
        self.init_fr_control()
        self.init_fr_status()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Power Supply Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

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

        # Position the value labels
        self.valueV1_s.grid(row=3, column=1, sticky='E', padx=5, pady=2)
        self.valueV1_r.grid(row=4, column=1, sticky='E', padx=5, pady=2)
        self.valueI1.grid(row=5, column=1, sticky='E', padx=5, pady=2)
        self.valueV2_s.grid(row=6, column=1, sticky='E', padx=5, pady=2)
        self.valueV2_r.grid(row=7, column=1, sticky='E', padx=5, pady=2)
        self.valueI2.grid(row=8, column=1, sticky='E', padx=5, pady=2)

        # ADD A REFRESH
        self.btn_update = ttk.Button(self.fr_info, text='UPDATE PS', command=lambda: self.update_PS(kind="full"))
        self.btn_update.grid(row=9, column=2, pady=5, padx=3, sticky='W')

    def init_fr_control(self):
        fr_m = self.fr_control

        # CHANNEL 1 CONTROLS
        self.ch1_label = ttk.Label(fr_m, text="Channel 1", style="TLabel")
        self.ch1_voltage = tk.Entry(fr_m)
        self.ch1_set_btn = ttk.Button(fr_m, text="Set Voltage", style="TButton",
                                      command=lambda: self.set_voltage(1, self.ch1_voltage.get())
                                      )

        self.ch1_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(1))
        self.ch1_label.grid(row=0, column=0, padx=10, pady=10)
        self.ch1_voltage.grid(row=0, column=1, padx=10, pady=10)
        self.ch1_set_btn.grid(row=0, column=2, padx=10, pady=10)
        self.ch1_toggle_btn.grid(row=0, column=3, padx=10, pady=10)

        # CHANNEL 2 CONTROLS
        self.ch2_label = ttk.Label(fr_m, text="Channel 2", style="TLabel")
        self.ch2_voltage = tk.Entry(fr_m)
        self.ch2_set_btn = ttk.Button(fr_m, text="Set Voltage", style="TButton",
                                      command=lambda: self.set_voltage(2, self.ch2_voltage.get())
                                      )
        self.ch2_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(2))
        self.ch2_label.grid(row=1, column=0, padx=10, pady=10)
        self.ch2_voltage.grid(row=1, column=1, padx=10, pady=10)
        self.ch2_set_btn.grid(row=1, column=2, padx=10, pady=10)
        self.ch2_toggle_btn.grid(row=1, column=3, padx=10, pady=10)

        # MISC CONTROL
        self.channelRecord_drop = guih.generate_drop_down(
            fr_m,
            [1, 2],
        )
        self.plot_current_btn = ttk.Button(fr_m, text="Live Plot current", style="TButton",
                                           command=lambda: self.plot_current(),
                                           )
        self.var_record = tk.IntVar()
        ttk.Checkbutton(fr_m,
                        text="Record current",
                        variable=self.var_record,
                        onvalue=1,
                        offvalue=0).grid(row=2, column=1)
        self.plot_current_btn.grid(row=2, column=3, padx=10, pady=10)
        self.channelRecord_drop[0].grid(row=2, column=0)

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
        self.labelCh2Mode.grid(row=0, column=1, pady=15, padx=15)
        self.ch2_mode.grid(row=1, column=1, pady=15, padx=15)

    def gui_refresh_info(self, event):
        # refresh DMM information
        if self.fr_port.status:
            if event == "auto":
                self.update_PS("full")

        # update Label
        if self.fr_port.status:
            self.valueV1_s.config(text='{:8s}'.format(str(self.ps_v1s)))
            self.valueV1_r.config(text='{:8s}'.format(str(self.ps_v1r)))
            self.valueI1.config(text='{:8s}'.format(str(self.ps_i1)))
            self.valueV2_s.config(text='{:8s}'.format(str(self.ps_v2s)))
            self.valueV2_r.config(text='{:8s}'.format(str(self.ps_v2r)))
            self.valueI2.config(text='{:8s}'.format(str(self.ps_i2)))

    # NOTE: this function is quite similar to the relay one in tab 1
    def gui_refresh_channel_state(self):
        if self.ps is not None:
            status_decode = self.ps.check_status()
        else:
            return

        if status_decode["ch1_state"] == "ON":
            self.ch1_toggle_btn.config(bg=self.theme_config["success"])
        else:
            self.ch1_toggle_btn.config(bg=self.theme_config["error"])

        # TODO: elegantly handle multi-channel power supplies here
        # if status_decode["ch2_state"] == "ON":
        #     self.ch2_toggle_btn.config(bg=self.theme_config["success"])
        # else:
        #     self.ch2_toggle_btn.config(bg=self.theme_config["error"])

    def gui_refresh_channel_mode(self):
        if self.ps is not None:
            try:
                status_decode = self.ps.check_status()
            except ValueError:
                self.ps = None
                return
        else:
            return

        try:
            if status_decode["ch1_mode"] == "CV":
                self.ch1_mode.set_color("green")
            else:
                self.ch1_mode.set_color("red")

            if status_decode["ch2_mode"] == "CV":
                self.ch2_mode.set_color("green")
            else:
                self.ch2_mode.set_color("red")
        # TODO: need more elegant way to handle the status_decode key errors here
        except KeyError:
            logging.error("Can't set channel CC and CV states because of KeyError")
            self.ch1_mode.set_color("black")
            self.ch2_mode.set_color("black")

    def gui_refresh(self, event):
        self.gui_refresh_info(event)
        self.gui_refresh_channel_mode()
        self.gui_refresh_channel_state()

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def update_PS(self, kind="partial"):
        print(f"Updating ({kind}) ps ...")
        if self.fr_port.status:
            # self.ps_v1s = self.ps.get_set_voltage(1)
            # self.ps_v2s = self.ps.get_set_voltage(2)
            self.ps_v1r = self.ps.get_voltage(1)
            self.ps_v2r = self.ps.get_voltage(2)
            self.ps_i1 = self.ps.get_current(1)
            self.ps_i2 = self.ps.get_current(2)

        print("... done updating, now calling `gui_refresh`")
        self.gui_refresh("call")

    def toggle_channel(self, channel):
        if self.ps is None:
            guih.alert_user("Can't toggle channel", "No PS connection!", "error")
            return False

        try:
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
                raise ValueError("Wrong channel input")
        except ValueError as e:
            guih.alert_user("Can't toggle channel", "Error: {e}", "error")
        else:
            state = None
            if channel == 1:
                state = self.ch1_on
            elif channel == 2:
                state = self.ch2_on
            self.prompt.print(f"Toggled channel {channel} to state {state}")

        time.sleep(0.5)
        self.gui_refresh("call")

    def set_voltage(self, channel, voltage_str):
        if self.ps is not None:
            # have to format input text_data box into float
            voltage = float(voltage_str)
            self.ps.set_voltage(voltage)
            self.prompt.print(f"Set voltage on channel {channel} to {voltage} V")
            if channel == 1:
                self.ps_v1s = voltage
            elif channel == 2:
                self.ps_v2s = voltage
        else:
            guih.alert_user("Can't set voltage", "No PS connection!", "error")

    # plot_current: starts a live plot and (optionally) records data to .csv
    def plot_current(self):
        # set up .csv recording
        recording = self.var_record.get()
        if recording:
            self.recName = 'AREC_' + time.strftime('%Y%m%d%H%M%S', time.localtime()) + '.csv'
            self.csvh = CSVHelper(self.data_dir + self.recName)
            self.csvh.initialize_file(["Sample", "Time", "Current"])

        self.prompt.print("Starting live current plot ...")
        currentLivePlot = plotter.LivePlot()

        def animate(i):
            for j in range(0, 10):
                # Retrieve the current reading and the timestamp
                reading = self.ps.get_current(int(self.channelRecord_drop[1].get()))
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                currentLivePlot.xs.append(len(currentLivePlot.xs))  # or a timestamp
                currentLivePlot.ys.append(reading)

                # add row to data file
                if recording:
                    self.csvh.add_row([i,timestamp, reading])

            # Clear and plot again, but avoid clearing the entire plot for better visual
            currentLivePlot.ax.clear()
            currentLivePlot.ax.plot(currentLivePlot.xs[-2000:], currentLivePlot.ys[-2000:], label="Current (A)")

        currentLivePlot.show_animation(animate, interval=200)

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PYVISA resource!")
        port = self.fr_port.get_port()

        # self.ps = SPD3303X.SPD3303X(port)
        self.ps = EEequipment.E3640A.E3640A.E3640A(port)

        try:
            self.id = self.ps.test_conn()
        except AttributeError as e:
            guih.alert_user("Can't connect to VISA", e, "warning")
            self.fr_port.set_status(False)
            return False
        except pyvisa.errors.VisaIOError as e:
            guih.alert_user("Can't connect to VISA", e, "error")
            self.fr_port.set_status(False)

        if self.id:  # CONNECTION SUCCESS
            self.prompt.print(f"Connected to PS with id: {self.id}")
            self.cc.set_ps(self.ps)
            self.labelIDValue.config(text=self.id)
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.fr_port.set_status(True)

            # turn channels off and set voltages
            self.ps.output_off(1)
            self.ps.output_off(2)
            self.ch1_on = 0
            self.ch2_on = 0

            # gui refresh
            self.gui_refresh_channel_state()
            return True
        else:  # BAD ID received
            self.ps = None
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False

    def port_close(self):
        self.prompt.print(f"Closing PYVISA resource!")
        self.ps.disconnect()
        self.fr_port.set_status(False)
        self.cc.set_ps(None)
        self.prompt.print(f"Connection is closed.")
