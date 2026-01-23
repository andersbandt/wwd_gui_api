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
import time
from datetime import datetime


# import user defined modules
from common import plotter
from analysis.csv_helper import CSVHelper
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle


# TODO: large (can I have it import a script to execute. For example how do I make my thermopile ramp saveable and repeatable


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

        # set up recording / data information
        self.recName = False
        self.data_dir = "data/ps_data/"

        # set up prompt
        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                   "PS Console Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_info.grid(row=0, column=0, pady=15, padx=15)
        self.fr_control.grid(row=1, column=0, pady=15, padx=15)
        self.fr_status.grid(row=1, column=1, pady=15, padx=15)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "PS_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3)
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

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("ps")
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

        self.ch1_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(1))
        self.ch1_label.grid(row=0, column=0, padx=10, pady=10)
        self.ch1_voltage.grid(row=0, column=1, padx=10, pady=10)
        self.ch1_set_btn.grid(row=0, column=2, padx=10, pady=10)
        self.ch1_toggle_btn.grid(row=0, column=3, padx=10, pady=10)

        # CHANNEL 2 CONTROLS
        self.ch2_label = ttk.Label(fr_m, text="Channel 2", style="TLabel")
        self.ch2_voltage = tk.Entry(fr_m)
        self.ch2_set_btn = tk.Button(fr_m, text="Set Voltage",
                                      command=lambda: self.set_voltage(2, self.ch2_voltage.get())
                                      )
        self.ch2_toggle_btn = tk.Button(fr_m, text="Toggle", command=lambda: self.toggle_channel(2))
        if self.channel_count == 2:
            self.ch2_label.grid(row=1, column=0, padx=10, pady=10)
            self.ch2_voltage.grid(row=1, column=1, padx=10, pady=10)
            self.ch2_set_btn.grid(row=1, column=2, padx=10, pady=10)
            self.ch2_toggle_btn.grid(row=1, column=3, padx=10, pady=10)

        # MISC CONTROL
        self.channelRecord_drop = guih.generate_drop_down(
            fr_m,
            [1, 2],
        )
        self.plot_current_btn = tk.Button(fr_m, text="Live Plot current",
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

    # NOTE: this function is quite similar to the relay one in tab 1
    def gui_refresh_channel_state(self):
        # TODO: I think I need a timeout on these
        if self.cc.get_ps_status():
            status_decode = self.cc.ps.check_status()
        else:
            return

        try:
            if status_decode["ch1_state"] == "ON":
                self.ch1_toggle_btn.config(bg=self.theme_config["success"])
            else:
                self.ch1_toggle_btn.config(bg=self.theme_config["error"])

            if status_decode["ch1_mode"] == "CV":
                self.ch1_mode.set_color("green")
            else:
                self.ch1_mode.set_color("red")

            # if we have 2-channel PS
            if self.channel_count > 1:
                if status_decode["ch2_state"] == "ON":
                    self.ch2_toggle_btn.config(bg=self.theme_config["success"])
                else:
                    self.ch2_toggle_btn.config(bg=self.theme_config["error"])

                if status_decode["ch2_mode"] == "CV":
                    self.ch2_mode.set_color("green")
                else:
                    self.ch2_mode.set_color("red")

        except KeyError as e:
            guih.alert_user("Can't set channel CC/CV states", f"KeyError:{e}", "error")
            self.ch1_mode.set_color("black")
            self.ch2_mode.set_color("black")

    def gui_refresh(self, event):
        print("gui_refresh for PS ...")
        if event == "auto":
            self.fr_port.refresh_ports()
        self.gui_refresh_info()
        self.gui_refresh_channel_state()
        print("end of gui_refresh for PS!")

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
        if self.cc.get_ps_status():
            # have to format input text_data box into float
            voltage = float(voltage_str)
            self.cc.ps.set_voltage(voltage)
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
                reading = self.cc.ps.get_current(int(self.channelRecord_drop[1].get()))
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

        ate_temp = self.registry[self.ate_drop[1].get()]
        self.cc.set_ps(ate_temp(self.fr_port.get_port()))

        try:
            self.id = self.cc.ps.test_conn()
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't connect to PS", e, "warning")
            self.fr_port.set_status(False)
            return False

        if self.id:  # CONNECTION SUCCESS
            # re-initialize channel count dependent frames
            self.init_fr_info()
            self.init_fr_control()
            self.init_fr_status()

            # start doing stuff
            self.prompt.print(f"Connected to PS with id: {self.id}")
            self.labelIDValue.config(text=self.id)
            self.labelTimeConnectedValue.config(text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
            self.fr_port.set_status(True)
            self.channel_count = self.cc.ps.channel_count

            # turn channels off and set voltages
            self.cc.ps.output_off(1)
            self.cc.ps.output_off(2)
            self.ch1_on = 0
            self.ch2_on = 0

            # gui_refresh
            self.gui_refresh_channel_state()
            return True
        else:  # BAD ID received
            self.cc.set_ps(None)
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False

    def port_close(self):
        self.prompt.print(f"Closing PYVISA resource!")
        self.cc.ps.disconnect()
        self.fr_port.set_status(False)
        self.cc.set_ps(None)
        self.prompt.print(f"Connection is closed.")
