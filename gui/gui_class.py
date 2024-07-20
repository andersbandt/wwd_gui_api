"""
@file     gui_class.py
@author   Anders Bandt
@date     July 2024
@brief    contains Class objects for the Tkinter GUI
"""


# import modules
import tkinter as tk
from tkinter import *
from tkinter import Text, INSERT, Label

import threading

# import user created modules
from gui import gui_helper as guih
from common import serial_api


# TODO: let's take all the hex color codes down below and all them to be input as some sort of template
class Prompt(tk.Frame):
    def __init__(self, master, title, height, width):
        super().__init__(master, height=height, width=width, bg="#6272a4")
        self.height = height
        self.width = width

        # set up text box for user communication
        Label(self, text=title, bg="#ff79c6", fg="#282a36").grid(row=0, column=0, pady=3)
        clear_button = tk.Button(self, text="Clear console", command=self.clear, bg="#f1fa8c", fg="#282a36")
        clear_button.grid(row=0, column=1, padx=7, pady=4, sticky="ew")
        self.prompt = Text(self,
                           height=height,
                           width=width,
                           bg="#282a36",
                           fg="#f8f8f2",
                           borderwidth=10)
        self.prompt.grid(row=1, column=0, columnspan=2, padx=5, pady=3)

    # gui_print: prints a message on a Tkinter frame
    def print(self, message, print_type=None):
        if print_type == "error":
            fg_color = "red"
        else:
            fg_color = "white"  # Default color

        message = ">>>" + message
        self.prompt.configure(fg=fg_color)  # Configure text color
        self.prompt.insert(INSERT, message + "\n")
        self.prompt.see("end")  # auto-scroll to the end
        return True

    def clear(self):
        self.prompt.delete("1.0", "end")  # basically line index from


class ConnFrame(tk.Frame):
    def __init__(self, master, name, connect_cmd, disconnect_cmd, bg=None):
        self.master = master
        super().__init__(self.master, bg=bg)
        self.name = name
        self.connect_cmd = connect_cmd
        self.disconnect_cmd = disconnect_cmd

        self.status = False
        self.canvas1 = tk.Canvas(self, width=50, height=50)  # create a Canvas widget
        self.status_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        self.init_base_fr()

    def init_base_fr(self):
        label = tk.Label(self, text=self.name)
        label.grid(row=0, column=0)

    def connect(self):
        self.status = self.connect_cmd()
        self.gui_refresh()

    def disconnect(self):
        self.status = self.disconnect_cmd
        self.status = False
        self.gui_refresh()

    def set_status(self, status):
        if status:
            self.canvas1.itemconfig(self.status_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.canvas1.itemconfig(self.status_oval, fill="red")  # Fill the circle with RED

    def gui_refresh(self):
        if self.status:
            self.canvas1.itemconfig(self.status_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.canvas1.itemconfig(self.status_oval, fill="red")  # Fill the circle with RED

    def set_color(self, color):
        self.canvas1.itemconfig(self.status_oval, fill=color)


# SerialConnFrame: just a basic serial connection frame
# TODO: can I make these talk among them selves to know when a connection is maintained to a serial port
#  (and underline the unavailable connnections or something)
class SerialConnFrame(ConnFrame):
    def __init__(self, master, name, connect_cmd, disconnect_cmd, port_func=2, bg=None):
        self.master = master
        super().__init__(self.master, name, connect_cmd, disconnect_cmd, bg=bg)

        self.port_func = port_func
        self.com_drop = None
        self.baud_drop = None

    def initialize_fr(self):
        # Button to refresh the list of COM ports
        refresh_button = tk.Button(self, text="Refresh Ports",
                                   command=self.refresh_ports,
                                   bg="green", fg="white")
        refresh_button.grid(row=1, column=2, columnspan=1, pady=1)

        # initialize port list
        self.com_drop = guih.generate_drop_down(
            self,
            serial_api.get_ports()
        )
        self.com_drop[0].grid(row=1, column=1, columnspan=1, padx=3, pady=10)

        # Initial port list
        self.refresh_ports()

        # place baud rate list
        # TODO: this baud rate does nothing. Because my `connect_serial` functions are ambigious, this may be hard to splice in?
        self.baud_drop = guih.generate_drop_down(
            self,
            ["115200", "9600"]
        )
        self.baud_drop[0].grid(row=2, column=1, padx=3, pady=10)

        # Button to refresh the list of COM ports
        # TARGET - BUTTON/STATUS
        btn_connect_serial = Button(self, text="Connect to COM",
                                    command=self.connect_cmd,
                                    bg="green", fg="white", height=1, width=15)
        btn_connect_serial.grid(row=3, column=1, padx=15, pady=1)
        btn_disconnect_serial = Button(self, text="Disconnect COM",
                                       command=self.disconnect_cmd,
                                       bg="orange", fg="black", height=1, width=15)
        btn_disconnect_serial.grid(row=4, column=1, padx=15, pady=3)

        # place CONNECT button and STATUS indicator
        self.canvas1.grid(row=5, column=2, padx=15, pady=3)

    def refresh_ports(self):
        menu = self.com_drop[0]["menu"]
        menu.delete(0, "end")

        # update port list
        ports = serial_api.get_ports(method=self.port_func)

        # add each port name to the drop down menu
        for string in ports:
            menu.add_command(label=string,
                             command=lambda value=string: self.com_drop[1].set(value))

    def get_port(self):
        return self.com_drop[1].get()


class AutoConnFrame(ConnFrame):
    def __init__(self, master, name, connect_cmd, disconnect_cmd, bg=None):
        self.master = master
        super().__init__(self.master, name, connect_cmd, disconnect_cmd, bg=bg)

    def init_fr(self):
        self.canvas1.grid(row=1, column=2, padx=15, pady=22)

        Button(
            self, text=f"Auto-connect", bg="purple", fg="black", command=self.connect_cmd
        ).grid(row=0, column=1, padx=5, pady=5)

        # RELAY STATUS INDICATOR
        Label(self, text=f"{self.name} status").grid(row=1, column=1, padx=5, pady=5)
        Label(self, text=f"{self.name} config").grid(row=2, column=1, padx=5, pady=5)

        self.gui_refresh()




class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
