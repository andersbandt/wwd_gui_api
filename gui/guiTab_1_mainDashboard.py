"""Main dashboard tab with overview status and system controls."""

# import needed packages
import logging
import tkinter as tk
from tkinter import ttk
import serial
import os
import platform
import subprocess

# import user defined modules
from EEequipment.usbrelay import usbrelay_controller
from common.serial_api import SerialProcessor
from common.path_helper import get_config_path, resolve_path

# import GUI modules
from gui import gui_class as guic
from gui import gui_helper as guih

logger = logging.getLogger(__name__)


def open_file_cross_platform(file_path):
    """
    Opens a file with the default application in a cross-platform way.
    Works on Windows, Linux, and macOS.

    Args:
        file_path: Path to the file to open

    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        return False

    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(file_path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", file_path], check=True)
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", file_path], check=True)
        return True
    except Exception as e:
        logger.error(f"Error opening file: {e}")
        return False


class TabMainDashboard(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # add some other variables
        self.relay_btns = []

        # init frames within tab
        self.fr_control = tk.Frame(self, bg=self.theme_config["dark_1"])
        self.fr_relay_control = tk.Frame(self, bg=self.theme_config["light_3"])

        self.fr_main_status = guic.AutoConnFrame(self, self.theme_config, "Relay", self.relay_autoconnect, None,
                                                        status_cmd=lambda: self.cc.get_relay_status())





        # add some variables for AutoConn frame
        self.fr_main_status.status = self.cc.relay.status

        # setup prompt
        self.prompt = guic.Prompt(self, self.theme_config, "Main")


        # initialize tab content
        self.initTabContent()

        # init serial port
        self.ser_obj = None
        self.fr_port = guic.SerialConnFrame(self, self.theme_config, self.cc, "ATE_serial", self.port_init, self.port_close,
                                                  status_cmd=lambda: self.ser_obj.serStatus if self.ser_obj else False)
        if autoconnect:
            self.fr_port.connect_previous_port()

        # place everything on the grid
        self.fr_main_status.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_control.grid(row=2, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_relay_control.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_port.grid(row=1, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.prompt.grid(row=10, column=0, columnspan=4, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nsew")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(10, weight=1)

        # refresh the relay state
        self.gui_refresh("auto")

    def initTabContent(self):
        logger.debug("Initializing tab 1 main dashboard")
        self.create_tab_header("Welcome to the WWD program!!!!", columnspan=2)
        self.init_fr_main_status()
        self.init_fr_relay_control()
        self.init_fr_control()

    def init_fr_main_status(self):
        self.fr_main_status.init_fr()

    def init_fr_relay_control(self):
        fr_m = self.fr_relay_control

        # add button for GUI refresh of relay states
        btn2 = tk.Button(fr_m, text=f"Refresh states", fg=self.theme_config["fg_light"], bg=self.theme_config["dark_2"],
                         command=lambda: self.gui_refresh("call"))
        btn2.grid(row=0, column=1, padx=10, pady=12)

        # Create and place individual relay control buttons
        for i in range(self.cc.relay.num_relays):
            name = self.cc.relay.get_relay_mapping(i + 1)
            btn = tk.Button(fr_m, text=f"{name}", fg=self.theme_config["fg_dark"], bg=self.theme_config["dark_2"],
                           command=lambda i=i: self.toggle_relay(i + 1))
            btn.grid(row=i // 4 + 1, column=i % 4, padx=10, pady=5)
            self.relay_btns.append(btn)

        # add some text with user information
        note = tk.Label(fr_m, text="User note: go to `EEequipment/usbrelay` and edit the `config.ini` file to adjust the naming of these")
        note.grid(row=5, column=0, padx=10, pady=10, columnspan=4)
        btn3 = tk.Button(fr_m, text=f"Open `config.ini`", fg=self.theme_config["fg_dark"], bg=self.theme_config["light_5"],
                         command=lambda: self.open_config_ini())
        btn3.grid(row=6, column=0, padx=10, pady=5)
        btn4 = tk.Button(fr_m, text=f"Open `master.ini`", fg=self.theme_config["fg_dark"], bg=self.theme_config["light_6"],
                         command=lambda: self.open_master_ini())
        btn4.grid(row=6, column=2, padx=10, pady=5)

    def init_fr_control(self):
        fr_m = self.fr_control

        self.label_control = ttk.Label(fr_m, style="TPinkLabel.TLabel")

        btn1 = tk.Button(fr_m, text=f"BUTTON 1",fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"],
                         command=lambda: self.send_command("a"))
        btn2 = tk.Button(fr_m, text=f"BUTTON 2",fg=self.theme_config["fg_dark"],  bg=self.theme_config["light_2"],
                         command=lambda: self.send_command("b"))
        btn3 = tk.Button(fr_m, text=f"BOTH BUTTON",fg=self.theme_config["fg_dark"],  bg=self.theme_config["light_3"],
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
                    btn.config(bg=self.theme_config["success"], fg=self.theme_config["fg_dark"])
                else:
                    btn.config(bg=self.theme_config["error"], fg=self.theme_config["fg_dark"])
        else:
            if event == "call":
                self.prompt.print("Can't refresh relay state with disconnected relay", "error")
                guih.alert_user("Can't refresh relay!", "Relay is not connected", "error")

        # update serial status
        if not self.fr_port.status:
            self.fr_port.refresh_ports()
        self.fr_port.gui_refresh()

    def relay_autoconnect(self):
        usb_dev = usbrelay_controller.find()
        self.cc.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        if usb_dev is not None:
            self.prompt.print("Autoconnect success")
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
                    self.prompt.print("ERROR: self.ser_obj is defined but status is FALSE", "error")
                    guih.alert_user("Can't send serial data", "Really can't send any shit. Probably I/O error?", "error")
                self.prompt.print(f"INFO: issued command {command} ...")
            else:
                self.prompt.print(f"ERROR: self.ser_obj exists but serStatus is false", "error")

        except AttributeError:
            self.prompt.print("ERROR: probably self.ser_obj is None", "error")

    def open_config_ini(self):
        file_path = resolve_path("EEequipment", "usbrelay", "config.ini")
        if not open_file_cross_platform(file_path):
            guih.alert_user("Can't edit config file", f"{file_path} doesn't exist or couldn't be opened", "error")

    def open_master_ini(self):
        file_path = get_config_path()
        if not open_file_cross_platform(file_path):
            guih.alert_user("Can't edit config file", f"{file_path} doesn't exist or couldn't be opened", "error")

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

        self.prompt.print(f"Init with port: {port}")
        try:
            self.ser_obj = SerialProcessor(port,9600)
        except serial.serialutil.SerialException as e:
            self.prompt.print(f"Can't init with port: {e}", "error")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        self.prompt.print("Init successful!\n")
        return True

    def port_close(self):
        self.prompt.print("Serial close!")
        try:
            self.ser_obj.stop_process()
        except AttributeError:
            pass
        self.fr_port.set_status(False)
