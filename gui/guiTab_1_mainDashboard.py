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
import os

# import user defined modules
from EEequipment.usbrelay import usbrelay_controller
from common.SerialReader import SerialReader

# import GUI modules
from gui import gui_class as guic
from gui import gui_helper as guih
from gui.guiTab_parent import ThemedFrame


# TODO: I don't think this connects properly AFTER program startup (program is started up, USB connected, try to connect?)
#   actually seems like I can connect but there is no status update



class tabMainDashboard(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file, autoconnect):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text_data
        l1 = ttk.Label(self, text="Welcome to the WWD program!!!!", style="BW.TLabel",
                       font=(self.theme_config["font"]["family"], 16))
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

        # setup prompt
        self.prompt1 = guic.Prompt(self, "Debug serial", height=14, width=140)
        self.prompt1.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

        # init serial port
        self.ser_obj = None
        self.fr_port = guic.SerialConnFrame(self, self.cc, "ATE_serial", self.port_init, self.port_close)
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
                         command=lambda: self.gui_refresh("call"))
        btn2.grid(row=0, column=1, padx=10, pady=12)

        # Create and place individual relay control buttons
        for i in range(self.cc.relay.num_relays):
            name = self.cc.relay.get_relay_mapping(i + 1)
            btn = ttk.Button(fr_m, text=f"{name}", command=lambda i=i: self.toggle_relay(i + 1))
            btn.grid(row=i // 4 + 1, column=i % 4, padx=10, pady=5)
            self.relay_btns.append(btn)

        # add some text with user information
        note = tk.Label(fr_m,text="User note: go to `EEequipment/usbrelay` and edit the `config.ini` file to adjust the naming of these")
        note.grid(row=5, column=0, padx=10, pady=10, columnspan=4)
        btn3 = tk.Button(fr_m, text=f"Open `config.ini`", bg=self.theme_config["dark_3"],
                         command=lambda: self.open_config_ini())
        btn3.grid(row=6, column=1, padx=10, pady=5)

    def init_fr_control(self):
        fr_m = self.fr_control

        self.label_control = tk.Label(fr_m,
                                      text="Focus this frame and type something",
                                      bg="lightgrey",
                                      font=("Arial", 14))

        btn1 = tk.Button(fr_m, text=f"Button 1", bg=self.theme_config["dark_1"],
                         command=lambda: self.send_command("a"))
        btn2 = tk.Button(fr_m, text=f"Button 2", bg=self.theme_config["dark_2"],
                         command=lambda: self.send_command("b"))
        btn3 = tk.Button(fr_m, text=f"Both buttons", bg=self.theme_config["dark_3"],
                         command=lambda: self.send_command("c"))

        self.label_control.grid(row=0, column=0, columnspan=3, pady=10, padx=10)
        btn1.grid(row=1, column=0, padx=10, pady=10)
        btn2.grid(row=1, column=2, padx=10, pady=10)
        btn3.grid(row=2, column=1, padx=10, pady=10)


        # set up some specific focus / keystroke stuff to enable keyboard usage
        fr_m.bind("<FocusIn>", self.fr_control_on_focus)
        fr_m.bind("<FocusOut>", self.fr_control_on_focus_lost)

        # Bind key press events to the frame
        fr_m.bind("<KeyPress>", self.on_key_press)

        # Ensure focus is restored when clicking inside the frame or buttons
        fr_m.bind("<Button-1>", lambda event: fr_m.focus_set())
        for widget in (btn1, btn2, btn3):
            widget.bind("<Button-1>", lambda event: fr_m.focus_set())  # Restore focus on button click

        # Set focus
        fr_m.focus_set()

    def gui_refresh(self, event):
        if self.fr_main_status.status:
            for i, btn in enumerate(self.relay_btns):
                if self.cc.relay.get_state_state(i + 1):
                    btn.config(style="TButtonOn.TButton")
                else:
                    btn.config(style="TButtonOff.TButton")
        else:
            if event == "call":
                self.prompt1.print("Can't refresh relay state with disconnected relay", "error")
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
        self.cc.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        if usb_dev is not None:
            self.prompt1.print("Autoconnect success")
            self.fr_main_status.set_status(True)
            self.init_fr_main_status()
        else:
            self.fr_main_status.set_status(False)
            guih.alert_user("Can't autoconnect to relay", f"Only found USB devices: {usb_dev}", "error")

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
                    self.prompt1.print("ERROR: self.ser_obj is defined but status is FALSE", "error")
                    guih.alert_user("Can't send serial data", "Really can't send any shit. Probably I/O error?", "error")
                self.prompt1.print(f"INFO: issued command {command} ...")
            else:
                self.prompt1.print(f"ERROR: self.ser_obj exists but serStatus is false", "error")

        except AttributeError:
            self.prompt1.print("ERROR: probably self.ser_obj is None", "error")

    def open_config_ini(self):
        file_path = os.getcwd() + "/EEequipment/usbrelay/config.ini"  #tag:HARDCODE
        if os.path.exists(file_path):
            os.startfile(file_path)  # Opens the file with the default associated application # TODO: might not work on Linux. Module "os" has no attribute `startfile`
        else:
            guih.alert_user("Can't edit config file", f"{file_path} doesn't exist", "error")

    ##############################################################################
    ####      GUI KEYSTROKE / FOCUS FUNCTIONS        #############################
    ##############################################################################

    def fr_control_on_focus(self, event):
        self.label_control.config(text="Type keys here (frame has focus)")

    def fr_control_on_focus_lost(self, event):
        self.label_control.config(text="Click to refocus the frame")

    def on_key_press(self, event):
        # print(f"HEY here is your keystroke: ({event.char},{event.keysym},{event.keycode}")
        if event.keysym == "Left":
            self.send_command('a')
        elif event.keysym == "Right":
            self.send_command('b')
        elif event.keysym == "Up":
            self.send_command('c')
        elif event.keysym == "Down":
            self.send_command('c')

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()

        self.prompt1.print(f"Init with port: {port}")
        try:
            self.ser_obj = SerialReader(port,
                                        9600)
        except serial.serialutil.SerialException as e:
            self.prompt1.print(f"Can't init with port: {e}", "error")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        self.prompt1.print("Init successful!\n")
        return True


    def port_close(self):
        self.prompt1.print("Serial close!")
        try:
            self.ser_obj.stop_process()
        except AttributeError:
            pass
        self.fr_port.set_status(False)
