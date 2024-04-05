"""
@file     guiTab_5_USB.py
@author   Anders Bandt
@date     March 2024
@brief    control device through serial (COM) port
"""

# import needed packages
import tkinter as tk
from tkinter import *
from tkinter import ttk
import threading
import serial
from serial.tools import list_ports

# import user defined modules
from common import xds110_api as xds110
from common import subprocessor
from common.SerialReader import SerialReader
from gui import gui_helper


class tabUSB:
    def __init__(self, master, basefilepath):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.frame.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text
        l1 = ttk.Label(self.frame, text="XDS110 and target control", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0)

        self.fr_prompt1 = tk.Frame(self.frame, bg="gray")
        self.fr_prompt1.grid(row=10, column=0, columnspan=2, padx=30, pady=12)
        self.prompt1 = gui_helper.init_fr_prompt(self.fr_prompt1, self.clear_gui)
        self.fr_prompt2 = tk.Frame(self.frame, bg="gray")
        self.fr_prompt2.grid(row=10, column=2, columnspan=2, padx=30, pady=12)
        self.prompt2 = gui_helper.init_fr_prompt(self.fr_prompt2, self.clear_gui)

        # init frames within tab
        self.fr_serial = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_serial.grid(row=1, column=0, padx=30, pady=12)
        self.fr_state = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_state.grid(row=2, column=0, padx=30, pady=12)

        # add some other variables
        self.canvas1 = tk.Canvas(self.fr_serial, width=50, height=50)  # create a Canvas widget
        self.canvas2 = tk.Canvas(self.fr_state, width=50, height=50)  # create a Canvas widget
        self.com_drop = None  # fr_serial
        self.test_drop = None  # fr_state
        self.ser_obj = None
        self.ser_status = False

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab XDS110 content")
        self.init_fr_serial()
        self.init_fr_state()

    def init_fr_serial(self):
        # COM port selection
        def refresh_ports():
            com_ports = [port.device for port in list_ports.comports()]
            # ports_var.set(com_ports)
            # set up user inputs for statement (year and month)
            self.com_drop = gui_helper.generate_drop_down(
                self.fr_serial,
                [port.device for port in list_ports.comports()]
            )
            self.com_drop[0].grid(row=1, column=1, columnspan=1, padx=3, pady=10)

        # Button to refresh the list of COM ports
        refresh_button = tk.Button(self.fr_serial, text="Refresh Ports",
                                   command=refresh_ports,
                                   bg="green", fg="white")
        refresh_button.grid(row=1, column=2, columnspan=1, pady=10)

        # Initial port list
        refresh_ports()

        # place CONNECT button and STATUS indicator
        self.canvas1.grid(row=2, column=2, padx=15, pady=22)
        # Button to refresh the list of COM ports
        # TARGET - BUTTON/STATUS
        btn_connect_serial = Button(self.fr_serial, text="Connect to COM",
                                    command=lambda: threading.Thread(target=self.connect_serial).start(),
                                    bg="green", fg="white", height=2, width=15)
        btn_connect_serial.grid(row=2, column=1, padx=15, pady=22)

    def init_fr_state(self):
        # TARGET - BUTTON/STATUS
        btn_act_test = Button(self.fr_state, text="Activate test mode",
                              command=lambda: threading.Thread(target=self.activate_test_mode).start(),
                              bg="green", fg="white", height=2, width=15)
        btn_act_test.grid(row=1, column=2, padx=15, pady=22)
        self.canvas2.grid(row=1, column=3, padx=15, pady=22)

        # TOGGLE
        btn_toggle_target = Button(self.fr_state, text="Set test type",
                                   command=lambda: threading.Thread(target=self.set_test_type).start(),
                                   bg="orange", fg="black", height=2, width=15)
        btn_toggle_target.grid(row=2, column=2, padx=15, pady=22)
        self.test_drop = gui_helper.generate_drop_down(
            self.fr_state,
            ["flash-read",
             "flash-extract",
             "imu_graph"]
        )
        self.test_drop[0].grid(row=2, column=3, padx=15, pady=15)

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def connect_serial(self):
        error_flag = 0
        serial_port = self.com_drop[1].get()
        error_flag |= self.serial_init(serial_port)

        if self.ser_status:
            gui_helper.gui_print(self.prompt1, f"Starting print threading")
            # threading.Thread(target=self.thread_print_display).start()
            threading.Timer(1.0, self.thread_print_display).start()

        my_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        if self.ser_status:
            self.canvas1.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.canvas1.itemconfig(my_oval, fill="red")  # Fill the circle with RED

    def activate_test_mode(self):
        command = "DAGA"
        my_oval = self.canvas2.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        gui_helper.gui_print(self.prompt1, f"INFO: issuing command {command} ...")
        if self.ser_status:
            # send the TEST MODE command for ACTIVATION
            self.ser_obj.send_data(command)
            gui_helper.gui_print(self.prompt1, f"INFO: issued command!\n")
            self.canvas2.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
        else:
            gui_helper.gui_print(self.prompt1, "ERROR: can't issue command, no serial connection\n")
            self.canvas2.itemconfig(my_oval, fill="red")  # Fill the circle with RED

    def set_test_type(self):
        test_type_command = self.test_drop[1].get()
        gui_helper.gui_print(self.prompt1, f"INFO: test type {test_type_command} ...")
        if test_type_command == "flash-read":
            command = "FR91"
        elif test_type_command == "flash-erase":
            command = "FE42"
        elif test_type_command == "imu-graph":
            command = "IG85"
        else:
            print("Fuck man no known test command")
            return False

        gui_helper.gui_print(self.prompt1, f"INFO: issuing command {command} ...")
        if self.ser_status:
            self.ser_obj.send_data(command)
            gui_helper.gui_print(self.prompt1, f"INFO: issued command!\n")
            return True
        else:
            gui_helper.gui_print(self.prompt1, "ERROR: can't issue command, no serial connection\n")
            return False

    #################################
    #### HELPER SHIT    #############
    #################################

    def clear_gui(self):
        gui_helper.gui_clear(self.prompt2)

    def thread_print_display(self):
        print("Thread print!")
        self.clear_gui()
        status = True
        while status:
            # print("Fuck")
            try:
                if self.ser_obj.serObj.inWaiting() > 0:  # Wait here until there is data
                    data = self.ser_obj.get_data("raw")
                    gui_helper.gui_print(self.prompt2, data)
            except serial.serialutil.SerialException as e:
                print(e)
                status = False
            except UnicodeDecodeError as e:
                gui_helper.gui_print(self.prompt2, e.__repr__())
        self.ser_status = False
        my_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        self.canvas1.itemconfig(my_oval, fill="red")  # Fill the circle with RED
        return False

    #################################
    #### SERIAL (COM)  ##############
    #################################

    def serial_init(self, serial_port):
        gui_helper.gui_print(self.prompt1, f"Init with port: {serial_port}")
        try:
            self.ser_obj = SerialReader(serial_port)
        except serial.serialutil.SerialException as e:
            gui_helper.gui_print(self.prompt1, f"ERROR: {e}")
            gui_helper.gui_print(self.prompt1, f"Can't init with port\n")
            gui_helper.alert_user("Can't start COM port", e, "error")
            return False

        gui_helper.gui_print(self.prompt1, "Init successful!\n")
        self.ser_status = True
        return True

    def serial_close(self):
        self.ser_obj.close()
        self.ser_status = False
