
# import needed packages
import tkinter as tk
from tkinter import *
from tkinter import ttk


# import user defined modules
from EEequipment.usbrelay import usbrelay_controller
from gui import gui_class as guic


class tabMainDashboard:
    def __init__(self, master, class_controller, basefilepath):
        self.master = master
        self.cc = class_controller
        self.frame = tk.Frame(self.master)
        self.frame.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text
        l1 = ttk.Label(self.frame, text="Welcome to the WWD program!!!!", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0, columnspan=2)

        # add some other variables
        self.relay_status = self.cc.relay.status # TODO: audit actual usage of relay_status variable.... could push it all to the AutoConnFrame?
        self.relay_btns = []

        # init frames within tab
        self.fr_main_status = guic.AutoConnFrame(self.frame, "Relay", self.relay_autoconnect, None, bg="#00bcd4")
        self.fr_main_status.grid(row=1, column=0, padx=30, pady=12)
        self.fr_main_status.status = self.cc.relay.status
        self.fr_relay_control = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_relay_control.grid(row=2, column=0, padx=30, pady=12)

        # add some other GUI variables
        self.canvas1 = tk.Canvas(self.fr_main_status, width=50, height=50)
        # Define styles for buttons
        style = ttk.Style(self.frame)
        style.configure("TButtonOn.TButton", background="green")
        style.configure("TButtonOff.TButton", background="red")

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 1 main dashboard")
        self.init_fr_main_status()
        self.init_fr_relay_control()

    def init_fr_main_status(self):
        self.fr_main_status.init_fr()


    def init_fr_relay_control(self):
        fr_m = self.fr_relay_control

        # add button for GUI refresh of relay states
        btn2 = Button(fr_m, bg="orange", text=f"Refresh states", command=lambda: self.gui_refresh_relay_state())
        btn2.grid(row=0, column=1, padx=10, pady=10)

        # Create and place individual relay control buttons
        for i in range(4): # TODO: this integer should come from the `config.ini` number (
            name = self.cc.relay.get_relay_mapping(i+1)
            btn = tk.Button(fr_m, text=f"{name}", command=lambda i=i: self.toggle_relay(i+1))
            btn.grid(row=i // 4 + 1, column=i % 4, padx=10, pady=10)
            self.relay_btns.append(btn)

        self.gui_refresh_relay_state()


    def toggle_relay(self, relay_num):
        # print(f"Now toggling relay {relay_num} from GUI")
        self.cc.relay.toggle_state(relay_num)
        self.gui_refresh_relay_state()


    def gui_refresh_relay_state(self):
        if self.relay_status:
            for i, btn in enumerate(self.relay_btns):
                if self.cc.relay.get_state_state(i+1):
                    print(f"Configuring button {i} with state ON")
                    # btn.config(style="TButtonOn.TButton")
                    btn.config(bg="green")
                else:
                    # print(f"Configuring button {i} with state OFF")
                    # btn.config(style="TButtonOff.TButton")
                    btn.config(bg="red")
            # print("DONE refresh of relay state")
        else:
            print("Can't refresh relay state with inactive relay!!!")


    def relay_autoconnect(self):
        usb_dev = usbrelay_controller.find()
        print(usb_dev)
        print("Found above for USB device")
        self.cc.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        if usb_dev is not None:
            self.relay_status = True
            self.init_fr_main_status()
