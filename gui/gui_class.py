
# import modules
import tkinter as tk
from tkinter import *
from tkinter import Text, INSERT, Label

# import user created modules
from gui import gui_helper as guih
from common import serial_api


class Prompt:
    def __init__(self, frame, title, bg_color, height, width):
        self.frame = frame
        self.height = height
        self.width = width
        self.bg_color = bg_color

        # set up text box for user communication
        Label(frame, text=title).grid(row=0, column=0, pady=3)
        clear_button = tk.Button(frame, text="Clear console", command=self.clear, bg="black", fg="white")
        clear_button.grid(row=0, column=1, padx=7, pady=3, sticky="ew")
        self.prompt = Text(frame,
                           height=height, width=width,
                           bg=bg_color, fg="white",
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


# TODO: add entry box for baud rate
class SerialConnFrame(tk.Frame):
    def __init__(self, master, connect_command, close_command, bg=None):
        self.master = master
        super().__init__(self.master, bg=bg)
        self.canvas1 = tk.Canvas(self, width=50, height=50)  # create a Canvas widget
        self.status_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        self.connect_serial = connect_command
        self.disconnect_serial = close_command
        self.com_drop = None


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

        # place CONNECT button and STATUS indicator
        self.canvas1.grid(row=4, column=2, padx=15, pady=3)
        # Button to refresh the list of COM ports
        # TARGET - BUTTON/STATUS
        btn_connect_serial = Button(self, text="Connect to COM",
                                    command=self.connect_serial,
                                    bg="green", fg="white", height=1, width=15)
        btn_connect_serial.grid(row=2, column=1, padx=15, pady=1)
        btn_disconnect_serial = Button(self, text="Disconnect COM",
                                       command=self.disconnect_serial,
                                       bg="orange", fg="black", height=1, width=15)
        btn_disconnect_serial.grid(row=3, column=1, padx=15, pady=3)

    def refresh_ports(self):
        menu = self.com_drop[0]["menu"]
        menu.delete(0, "end")

        # update port list
        ports = serial_api.get_ports()

        # add each port name to the drop down menu
        for string in ports:
            menu.add_command(label=string,
                             command=lambda value=string: self.com_drop[1].set(value))

    def get_port(self):
        return self.com_drop[1].get()

    def set_status(self, status):
        if status:
            self.canvas1.itemconfig(self.status_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.canvas1.itemconfig(self.status_oval, fill="red")  # Fill the circle with RED

