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
import pyvisa.errors
from sympy.physics.units import current

# import user defined modules
from common import plotter
from EEequipment.spd3303x import SPD3303X

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle
from gui.guiTab_parent import ThemedFrame


# TODO: add some console output when I turn on/off a supply

# TODO: there is lots of thematic red/green updates to be made here

# TODO: I have a suspicion that calls to PyVISA refresh ports are very slow in here .... longer startup time ...

class tabPS(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file):
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

        # set up prompt
        self.prompt = guic.Prompt(self, "PSConsole Output", height=18, width=140)

        # place everything in grid
        # self.fr_port is placed in `init_fr_port`
        self.fr_info.grid(row=0, column=0, pady=15, padx=15)
        self.fr_control.grid(row=1, column=0, pady=15, padx=15)
        self.fr_status.grid(row=1, column=1, pady=15, padx=15)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 6 (PS) content")
        self.init_fr_info()
        self.init_fr_control()
        self.init_fr_status()
        self.init_fr_port()

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
        self.labelV1 = ttk.Label(self.fr_info, width=10, text='Voltage 1', style="TLabel", anchor='w')
        self.labelI1 = ttk.Label(self.fr_info, width=9, text='Current 1', style="TLabel", anchor='w')
        self.labelV2 = ttk.Label(self.fr_info, width=9, text='Voltage 2', style="TLabel", anchor='w')
        self.labelI2 = ttk.Label(self.fr_info, width=10, text='Current 2', style="TLabel", anchor='w')

        # Position the range and measurement labels
        self.labelV1.grid(row=3, column=0, sticky='W', padx=5, pady=2)
        self.labelI1.grid(row=4, column=0, sticky='W', padx=5, pady=2)
        self.labelV2.grid(row=5, column=0, sticky='W', padx=5, pady=2)
        self.labelI2.grid(row=6, column=0, sticky='W', padx=5, pady=2)

        # Add value labels for range and measurements
        self.valueV1 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueI1 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueV2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')
        self.valueI2 = tk.Label(self.fr_info, width=10, text='', relief='sunken', anchor='w')

        # Position the value labels
        self.valueV1.grid(row=3, column=1, sticky='E', padx=5, pady=2)
        self.valueI1.grid(row=4, column=1, sticky='E', padx=5, pady=2)
        self.valueV2.grid(row=5, column=1, sticky='E', padx=5, pady=2)
        self.valueI2.grid(row=6, column=1, sticky='E', padx=5, pady=2)

    def init_fr_port(self):
        self.fr_port = guic.SerialConnFrame(self,
                                            self.cc,
                                            "PS_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3,
                                            bg="#00bcd4")
        self.fr_port.initialize_fr()
        self.fr_port.connect_previous_port()
        self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, padx=15, pady=15)

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
        self.plot_current_btn = ttk.Button(fr_m, text="Live Plot current", style="TButton",
                                           command=lambda: self.plot_current(),
                                           )
        self.plot_current_btn.grid(row=2, column=0, padx=10, pady=10)

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

    # NOTE: this function is quite similar to the relay one in tab 1
    def gui_refresh_channel_state(self):
        if self.ps is not None:
            try:
                status_decode = self.ps.check_status()
            except pyvisa.errors.VisaIOError:  # TODO: this except shouldn't be here !
                return
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

    def gui_refresh_channel_mode(self):
        if self.ps is not None:
            status_decode = self.ps.check_status()
        else:
            return

        if status_decode["ch1_mode"] == "CV":
            self.ch1_mode.set_color("green")
        else:
            self.ch1_mode.set_color("red")

        if status_decode["ch2_mode"] == "CV":
            self.ch2_mode.set_color("green")
        else:
            self.ch2_mode.set_color("red")

    def gui_refresh(self):
        self.gui_refresh_channel_mode()
        self.gui_refresh_channel_state()

    #################################
    #### ACTION FUNCTIONS  ##########
    #################################

    def toggle_channel(self, channel):
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

        time.sleep(0.5)
        self.gui_refresh()

    def set_voltage(self, channel, voltage_str):
        if self.ps is not None:
            # have to format input text_data box into float
            voltage = float(voltage_str)
            self.ps.set_voltage(channel, voltage)
        else:
            guih.alert_user("Can't set voltage", "No PS connection!", "alert")

    def plot_current(self):
        currentLivePlot = plotter.LivePlot()

        def animate(i):
            for j in range(0, 10):
                # Retrieve the current reading and the timestamp
                reading = self.ps.get_current(1)
                currentLivePlot.xs.append(len(currentLivePlot.xs))  # or a timestamp
                currentLivePlot.ys.append(reading)

            # Clear and plot again, but avoid clearing the entire plot for better visual
            currentLivePlot.ax.clear()
            currentLivePlot.ax.plot(currentLivePlot.xs[-2000:], currentLivePlot.ys[-2000:], label="Current (A)")

        # Start the animation with a 200 ms interval
        currentLivePlot.show_animation(animate, interval=200)

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PYVISA resource!")
        port = self.fr_port.get_port()

        try:
            self.ps = SPD3303X.SPD3303X(port)
        except ValueError:
            self.ps = None

        try:
            self.id = self.ps.test_conn()
        except AttributeError:
            guih.alert_user("Can't connect to VISA", "Best guess is the port is not active", "warning")
            self.fr_port.set_status(False)
            return False
        except pyvisa.errors.VisaIOError:
            guih.alert_user("Can't connect to VISA", "Visa connect error (likely timeout)", "error")
            self.fr_port.set_status(False)
        if self.id is not False:
            self.prompt.print(f"Connected to PS with id: {self.id}")
            self.cc.set_ps(self.ps)
            self.labelIDValue.config(text=self.id)
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.ser_status = True
            self.fr_port.set_status(self.ser_status)
            self.ps.output_off(1)
            self.ps.output_off(2)
            self.ch1_on = 0
            self.ch2_on = 0
            self.gui_refresh_channel_state()
            return True
        else:  # BAD ID received
            # if self.id == '' or len(self.id) < 3:
            self.ps = None
            self.ser_status = False
            self.fr_port.set_status(self.ser_status)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False

    def port_close(self):
        self.prompt.print(f"Close PYVISA resource!")
        self.ps.close()
        self.ser_status = False
        self.fr_port.set_status(self.ser_status)
