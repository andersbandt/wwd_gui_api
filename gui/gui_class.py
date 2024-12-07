"""
@file     gui_class.py
@author   Anders Bandt
@date     July 2024
@brief    contains Class objects for the Tkinter GUI
"""

# import modules
import tkinter as tk
import xml.etree.ElementTree
from tkinter import ttk
from tkinter import Text, INSERT
from tkinter import scrolledtext

import threading
import xml.etree.ElementTree as ET

# import user created modules
from gui import gui_helper as guih
from gui.guiTab_parent import ThemedFrame
from common import serial_api


class ColorCircle(tk.Canvas):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.status_oval = self.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1

    def set_color(self, color):
        self.itemconfig(self.status_oval, fill=color)


##########################################
### FRAMES (VARIOUS)     #################
##########################################

class Prompt(ThemedFrame):
    def __init__(self, master, title, height, width):
        self.theme_file = "config/darcula.json"  #tag:hardcode
        super().__init__(master, self.theme_file, height=height, width=width)
        self.height = height
        self.width = width
        self.set_bg(self.theme_config["light_4"])

        ttk.Label(self, text=title, style="TPinkLabel.TLabel").grid(row=0, column=0, pady=5, padx=10)
        clear_button = ttk.Button(self, text="Clear console", style="TYellowButton.TButton", command=self.clear)
        clear_button.grid(row=0, column=1, padx=7, pady=4, sticky="ew")

        # set up text_data box for user communication
        self.prompt = scrolledtext.ScrolledText(self,
                                                font = (self.theme_config["font"]["family"], self.theme_config["font"]["size"]),
                                                height=height,
                                                width=width,
                                                bg=self.theme_config["light_2"],
                                                fg=self.theme_config["fg_light"],
                                                borderwidth=10)
        self.prompt.tag_configure("error", foreground="red")
        self.prompt.tag_configure("normal", foreground=self.theme_config["fg_light"])
        self.prompt.grid(row=1, column=0, columnspan=2, padx=5, pady=3)

    # gui_print: prints a message on a Tkinter frame
    def print(self, message, print_type=None):
        message = ">>>" + message + "\n"
        if print_type == "error":
            self.prompt.insert(INSERT, message, "error")  # Apply 'error' tag
        else:
            self.prompt.insert(INSERT, message, "normal")  # Apply 'normal' tag

        self.prompt.see("end")  # Auto-scroll to the end
        return True

    def clear(self):
        self.prompt.delete("1.0", "end")  # basically line index from


# TODO: add a class for an Equipment information frame (ID, connect time, etc)


##########################################
### CONNECTION FRAMES    #################
##########################################

class ConnFrame(ThemedFrame):
    def __init__(self, master, name, connect_cmd, disconnect_cmd):
        self.theme_file = "config/darcula.json"  #tag:hardcode
        super().__init__(master, self.theme_file)
        self.master = master
        self.name = name
        self.connect_cmd = connect_cmd
        self.disconnect_cmd = disconnect_cmd

        self.port = None

        self.status = False
        self.canvas1 = tk.Canvas(self, width=50, height=50, bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.status_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1

        self.set_bg(self.theme_config["light_4"])
        self.init_base_fr()

    def init_base_fr(self):
        label = ttk.Label(self, text=self.name, style="TPinkLabel.TLabel")
        label.grid(row=0, column=0, pady=15, padx=10)

    def connect(self):
        self.status = self.connect_cmd()
        print(f"Connect with {self.port} had status: {self.status} !\n")
        self.gui_refresh()
        return self.status

    def disconnect(self):
        self.disconnect_cmd()
        self.status = False
        self.gui_refresh()

    def set_status(self, status):
        if status:
            self.canvas1.itemconfig(self.status_oval, fill=self.theme_config["success"])
        else:
            self.canvas1.itemconfig(self.status_oval, fill=self.theme_config["error"])

    def gui_refresh(self):
        self.set_status(self.status)

    def set_color(self, color):
        self.canvas1.itemconfig(self.status_oval, fill=color)


# SerialConnFrame: just a basic serial connection frame
class SerialConnFrame(ConnFrame):
    def __init__(self, master, class_controller, name, connect_cmd, disconnect_cmd, port_func=None):
        super().__init__(master, name, connect_cmd, disconnect_cmd)
        self.cc = class_controller

        # NOTE: port_func is for tracking what method is used for populating array of ports
        self.port_func = port_func  # NONE defaults to OS detection method. 1=Windows, 2=Linux, 3=PyVISA
        self.com_drop = None
        self.baud_drop = None

        self.initialize_fr()

        # self.connect_previous_port()
        # TODO: figure out how to implement this in here. Main challenge is my `connect_cmd` typically requires frame to be fully initialized

    def initialize_fr(self):
        # Button to refresh the list of COM ports
        refresh_button = tk.Button(self, text="Refresh Ports",
                                   command=self.refresh_ports,
                                   bg=self.theme_config["dark_1"], fg=self.theme_config["fg_light"])
        refresh_button.grid(row=1, column=2, columnspan=1, pady=1)

        # initialize port list
        self.com_drop = guih.generate_drop_down(
            self,
            serial_api.get_ports(method=self.port_func)
        )
        self.com_drop[0].grid(row=1, column=1, columnspan=1, padx=3, pady=10)

        # Initial port list
        self.refresh_ports()

        # place baud rate list
        # TODO: this baud rate does nothing. Because my `connect_serial` functions are ambigious, this may be hard to splice in?
        # TODO: if I do get it working, let's save it with our autoconnect preferences?
        self.baud_drop = guih.generate_drop_down(
            self,
            ["115200", "9600"]
        )
        self.baud_drop[0].grid(row=2, column=1, padx=3, pady=10)

        # Button to refresh the list of COM ports
        # TARGET - BUTTON/STATUS
        btn_connect_serial = tk.Button(self, text="Connect to COM",
                                       command=self.connect,
                                       bg=self.theme_config["dark_2"], fg=self.theme_config["fg_dark"], height=1,
                                       width=15)
        btn_connect_serial.grid(row=3, column=1, padx=15, pady=1)
        btn_disconnect_serial = tk.Button(self, text="Disconnect COM",
                                          command=self.disconnect,
                                          bg=self.theme_config["dark_3"], fg=self.theme_config["fg_dark"], height=1,
                                          width=15)
        btn_disconnect_serial.grid(row=4, column=1, padx=15, pady=3)

        # place CONNECT button and STATUS indicator
        self.canvas1.grid(row=5, column=2, padx=15, pady=3)

    def connect(self, set_used_port=True):
        super().connect()
        if self.status and set_used_port:
            self.cc.set_used_port(self.port, self.name)

    def refresh_ports(self):
        menu = self.com_drop[0]["menu"]
        menu.delete(0, "end")

        # update port list
        ports = serial_api.get_ports(method=self.port_func)

        prev_port = self.get_previous_port()
        if prev_port in ports:
            pass

        # add each port name to the drop down menu
        for string in ports:
            menu.add_command(label=string,
                             command=lambda value=string: self.com_drop[1].set(value))

    def get_port(self):
        self.port = self.com_drop[1].get()
        return self.port

    def get_previous_port(self):
        # Create the root element
        root = ET.Element("PortsUsed")
        try:
            tree = ET.ElementTree(root, file="config/ports_used.xml")
        except xml.etree.ElementTree.ParseError:
            return False

        port_elem = tree.find(self.name)
        if port_elem is not False:
            if port_elem is not None:
                return port_elem.text
        else:
            return None

    def connect_previous_port(self):
        self.port = self.get_previous_port()
        self.com_drop[1].set(self.port)
        if self.port is not None:
            print(f"Connect to previous port for {self.name} @ {self.port}")
            self.connect(set_used_port=False)
        return self.status


class AutoConnFrame(ConnFrame):
    def __init__(self, master, name, connect_cmd, disconnect_cmd):
        self.master = master
        super().__init__(self.master, name, connect_cmd, disconnect_cmd)

    def init_fr(self):
        self.canvas1.grid(row=1, column=2, padx=15, pady=22)

        tk.Button(
            self, text=f"Auto-connect", fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
            command=self.connect_cmd
        ).grid(row=0, column=1, padx=5, pady=5)

        # RELAY STATUS INDICATOR
        ttk.Label(self, text=f"{self.name} status", style="TLabel").grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(self, text=f"{self.name} config", style="TLabel").grid(row=2, column=1, padx=5, pady=5)

        self.gui_refresh()


##########################################
### THREADS#######      ##################
##########################################

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.args = args
        self.kwargs = kwargs

    # def run(self):
    # while not self.stopped():
    # self.function(*self.args, **self.kwargs)
    # break  # If you want to run only once, remove this if you need continuous execution

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
