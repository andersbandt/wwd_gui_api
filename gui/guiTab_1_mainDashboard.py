"""
@file     guiTab_1_mainDashboard.py
@author   Anders Bandt
@date
@brief    main dashboard for ATE control
"""

# import needed packages
import tkinter as tk
from tkinter import ttk
import serial

# import user defined modules
from EEequipment.usbrelay import usbrelay_controller
from common.SerialReader import SerialReader

# import GUI modules
from gui import gui_class as guic
from gui import gui_helper as guih
from gui.guiTab_parent import ThemedFrame


# TODO: make a subclass of ThemedFrame if there is a serial port for the tab? Can handle the `autoconnect` variable more elegantly?

# TODO: this might be a stretch ... but when I click into the Arduino Button page can I have the keystrokes on the arrow keys be mapped to the button options ?????

class tabMainDashboard(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file, autoconnect):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text_data
        l1 = ttk.Label(self, text="Welcome to the WWD program!!!!", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0, columnspan=2)

        # add some other variables
        self.relay_btns = []

        # init frames within tab
        self.fr_main_status = guic.AutoConnFrame(self, "Relay", self.relay_autoconnect, None)
        self.fr_main_status.grid(row=1, column=0, padx=30, pady=12)
        self.fr_main_status.status = self.cc.relay.status
        self.fr_control = tk.Frame(self, bg="#00bcd4")
        self.fr_control.grid(row=2, column=1, padx=30, pady=12)
        self.fr_relay_control = tk.Frame(self, bg=self.theme_config["light_3"])
        self.fr_relay_control.grid(row=2, column=0, padx=30, pady=12)

        # add some other GUI variables
        self.canvas1 = tk.Canvas(self.fr_main_status, width=50, height=50)

        # Define styles for buttons
        # TODO: either delete this or implement everywhere?
        style = ttk.Style(self)
        style.configure("TButtonOn.TButton", background="green")
        style.configure("TButtonOff.TButton", background="red")

        # setup prompt
        self.prompt1 = guic.Prompt(self, "Debug serial", height=14, width=140)
        self.prompt1.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

        # init serial port
        # TODO: standardize this stuff in the serial frame parent class
        self.ser_obj = None
        self.fr_port = guic.SerialConnFrame(self, self.cc, "ATE_serial", self.port_init, self.port_close,
                                            bg="#00bcd4")
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=1, column=1, padx=30, pady=12)

        # refresh the relay state
        self.gui_refresh("auto")

    def initTabContent(self):
        print("Initializing tab 1 main dashboard")
        self.init_fr_main_status()
        self.init_fr_relay_control()
        self.init_fr_control()

    def init_fr_main_status(self):
        self.fr_main_status.init_fr()

    def init_fr_relay_control(self):
        fr_m = self.fr_relay_control

        # add button for GUI refresh of relay states
        btn2 = tk.Button(fr_m, text=f"Refresh states", bg=self.theme_config["dark_2"],
                         command=lambda: self.gui_refresh_relay_state("call"))
        btn2.grid(row=0, column=1, padx=10, pady=10)

        # Create and place individual relay control buttons
        for i in range(self.cc.relay.num_relays):
            name = self.cc.relay.get_relay_mapping(i + 1)
            btn = ttk.Button(fr_m, text=f"{name}", command=lambda i=i: self.toggle_relay(i + 1))
            btn.grid(row=i // 4 + 1, column=i % 4, padx=10, pady=10)
            self.relay_btns.append(btn)

        # add some text with user information
        note = tk.Label(fr_m,
                        text="User note: go to `EEequipment/usbrelay` and edit the `config.ini` file to adjust the naming of these")
        # TODO: add a "edit this file" button here to open config.ini
        note.grid(row=5, column=0, padx=10, pady=10, columnspan=4)

    def init_fr_control(self):
        fr_m = self.fr_control

        btn1 = tk.Button(fr_m, text=f"Button 1", bg=self.theme_config["dark_1"],
                         command=lambda: self.send_command("a"))
        btn2 = tk.Button(fr_m, text=f"Button 2", bg=self.theme_config["dark_2"],
                         command=lambda: self.send_command("b"))
        btn3 = tk.Button(fr_m, text=f"Both buttons", bg=self.theme_config["dark_3"],
                         command=lambda: self.send_command("c"))

        btn1.grid(row=0, column=0, padx=10, pady=10)
        btn2.grid(row=0, column=1, padx=10, pady=10)
        btn3.grid(row=0, column=2, padx=10, pady=10)

    # TODO: ensure all the other tabs have a `gui_refresh` modeled of this with the "event"
    def gui_refresh(self, event):
        if self.fr_main_status.status:
            for i, btn in enumerate(self.relay_btns):
                if self.cc.relay.get_state_state(i + 1):
                    btn.config(style="TButtonOn.TButton")
                else:
                    btn.config(style="TButtonOff.TButton")
        else:
            print("Can't refresh relay state with inactive relay!!!")
            if event == "call":
                guih.alert_user("Can't refresh relay!", "Relay is not connected", "error")

        # update serial status
        if self.ser_obj is not None:
            if self.ser_obj.serStatus is False:
                self.ser_obj.stop_process()
                self.fr_port.set_status(False)
            else:
                self.fr_port.set_status(True)

    def relay_autoconnect(self):
        usb_dev = usbrelay_controller.find()
        print(usb_dev)
        print("Found above for USB device")
        self.cc.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        if usb_dev is not None:
            self.fr_main_status.set_status(True)
            self.init_fr_main_status()

    ##############################################################################
    ####      BUTTON ACTION FUNCTIONS        #####################################
    ##############################################################################

    def toggle_relay(self, relay_num):
        if self.cc.relay is not None:
            self.cc.relay.toggle_state(relay_num)
            self.gui_refresh("call")
        else:
            guih.alert_user("Can't toggle relay", "Relay not connected!", "error")

    def send_command(self, command):
        try:
            if self.ser_obj.serStatus:
                try:
                    self.ser_obj.send_data(command)
                except serial.serialutil.SerialException:
                    self.prompt1.print("ERROR: self.ser_obj is defined but status is FALSE\n")
                    guih.alert_user("Can't send serial data", "Really can't send any shit. Probably I/O error?", "error")
                self.prompt1.print(f"INFO: issued command {command} ...")
            else:
                self.prompt1.print(f"ERROR: self.ser_obj exists but serStatus is false")

        except AttributeError:
            self.prompt1.print("ERROR: probably self.ser_obj is None\n")

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()

        self.prompt1.print(f"Init with port: {port}")
        try:
            self.ser_obj = SerialReader(port,
                                        9600)  # TODO: make this a drop down in the seriaal frame. Also save it with my autconnect preferences???
        except serial.serialutil.SerialException as e:
            self.prompt1.print(f"ERROR: {e}")
            self.prompt1.print(f"Can't init with port\n")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        self.prompt1.print("Init successful!\n")
        return True

    # TODO: I don't think this printout is working
    def port_close(self):
        self.prompt1.print("Serial close!")
        self.ser_obj.stop_process()
        self.fr_port.set_status(False)
