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
from datetime import datetime

# import user defined modules
from common.SerialReader import SerialReader
from gui import gui_helper as guih
from gui import gui_class as guic


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
        self.fr_prompt1.grid(row=10, column=0, columnspan=4, padx=30, pady=12)
        self.prompt1 = guic.Prompt(self.fr_prompt1, "Debug serial", "black", height=14, width=140)
        self.fr_prompt2 = tk.Frame(self.frame, bg="purple")
        self.fr_prompt2.grid(row=0, column=2, rowspan=5, columnspan=1, padx=12, pady=12)
        self.prompt2 = guic.Prompt(self.fr_prompt2, "Serial output", "black", height=30, width=100)

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
        self.output_file_name = None  # fr_state
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
            self.com_drop = guih.generate_drop_down(
                self.fr_serial,
                [port.device for port in list_ports.comports()]
            )
            self.com_drop[0].grid(row=1, column=1, columnspan=1, padx=3, pady=10)

        # Button to refresh the list of COM ports
        refresh_button = tk.Button(self.fr_serial, text="Refresh Ports",
                                   command=refresh_ports,
                                   bg="green", fg="white")
        refresh_button.grid(row=1, column=2, columnspan=1, pady=1)

        # Initial port list
        refresh_ports()

        # place CONNECT button and STATUS indicator
        self.canvas1.grid(row=4, column=2, padx=15, pady=3)
        # Button to refresh the list of COM ports
        # TARGET - BUTTON/STATUS
        btn_connect_serial = Button(self.fr_serial, text="Connect to COM",
                                    command=self.connect_serial,
                                    bg="green", fg="white", height=1, width=15)
        btn_connect_serial.grid(row=2, column=1, padx=15, pady=1)
        btn_disconnect_serial = Button(self.fr_serial, text="Disconnect COM",
                                       command=self.serial_close,
                                       bg="orange", fg="black", height=1, width=15)
        btn_disconnect_serial.grid(row=3, column=1, padx=15, pady=3)

        # SERIAL - PROCESS CONTROL
        btn_stop_process = Button(self.fr_serial, text="No action",
                                  command=None,
                                  bg="purple", fg="white", height=2, width=15)
        btn_stop_process.grid(row=5, column=1, padx=15, pady=3)

    def init_fr_state(self):
        # TARGET - BUTTON/STATUS
        btn_act_test = Button(self.fr_state, text="Activate test mode",
                              command=self.activate_test_mode,
                              bg="green", fg="white", height=2, width=15)
        btn_act_test.grid(row=1, column=2, padx=15, pady=22)
        self.canvas2.grid(row=1, column=3, padx=15, pady=22)

        # TOGGLE
        btn_toggle_target = Button(self.fr_state, text="Set test type",
                                   command=self.set_test_type,
                                   bg="orange", fg="black", height=2, width=15)
        btn_toggle_target.grid(row=2, column=2, padx=15, pady=22)
        self.test_drop = guih.generate_drop_down(
            self.fr_state,
            ["flash-read",
             "flash-read-all",
             "flash-erase",
             "imu_graph",
             "clock-test"]
        )
        self.test_drop[0].grid(row=2, column=3, padx=15, pady=15)

        var2 = tk.IntVar()
        c1 = tk.Checkbutton(self.fr_state, text='Record?', variable=var2, onvalue=1, offvalue=0, command=None)
        c1.grid(row=2, column=4, padx=2)

        # add output file name box
        Label(self.fr_state, text="Output file name").grid(row=3, column=1, padx=5, pady=5)
        self.output_file_name = Text(self.fr_state, height=2, width=20)
        self.output_file_name.grid(row=3, column=3)

    ##############################################################################
    ####      BUTTON ACTION FUNCTIONS        #####################################
    ##############################################################################

    def connect_serial(self):
        error_flag = 0
        serial_port = self.com_drop[1].get()
        error_flag |= self.serial_init(serial_port)

        if self.ser_status:
            self.prompt1.print(f"Starting print threading")
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
        self.prompt1.print(f"INFO: issuing command {command} ...")
        if self.ser_status:
            # send the TEST MODE command for ACTIVATION
            self.ser_obj.send_data(command)
            self.prompt1.print(f"INFO: issued command!\n")
            self.canvas2.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.prompt1.print("ERROR: can't issue command, no serial connection\n")
            self.canvas2.itemconfig(my_oval, fill="red")  # Fill the circle with RED

    def set_test_type(self):
        test_type_command = self.test_drop[1].get()
        self.prompt1.print(f"INFO: test type {test_type_command} ...")
        if test_type_command == "flash-read":
            command = "FR91"
        elif test_type_command == "flash-read-all":
            command = "FR01"
        elif test_type_command == "flash-erase":
            command = "FE42"
        elif test_type_command == "imu-graph":
            command = "IG85"
        elif test_type_command == "clock-test":
            self.start_process("clock_data", "clock_test", ["timestamp", "ms", "temp"])
            command = "CR81"
        else:
            print("Fuck man no known test command")
            return False

        self.prompt1.print(f"INFO: issuing command {command} ...")
        if self.ser_status:
            self.ser_obj.send_data(command)
            self.prompt1.print(f"INFO: issued command!\n")
            return True
        else:
            self.prompt1.print("ERROR: can't issue command, no serial connection\n")
            return False

    #################################
    #### THREADS SHIT    ############
    #################################

    def gui_refresh(self):
        while True:
            if self.ser_obj.serStatus is False:
                # serial connection
                my_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
                self.canvas1.itemconfig(my_oval, fill="red")  # Fill the circle with RED

                # test mode
                my_oval = self.canvas2.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
                self.canvas2.itemconfig(my_oval, fill="red")  # Fill the circle with RED

    def thread_print_display(self):
        print("Thread print!")
        self.prompt2.clear()
        # threading.Thread(target=lambda: self.gui_refresh()).start()
        threading.Thread(target=lambda: self.ser_obj.process_data(self.basefilepath, None, "raw")).start()
        threading.Thread(target=lambda: self.ser_obj.get_data(printmode=False)).start()
        return True

    #################################
    #### SERIAL (COM)  ##############
    #################################

    def serial_init(self, serial_port):
        self.prompt1.print(f"Init with port: {serial_port}")
        try:
            self.ser_obj = SerialReader(serial_port, 115200)
        except serial.serialutil.SerialException as e:
            self.prompt1.print(f"ERROR: {e}")
            self.prompt1.print(f"Can't init with port\n")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        self.prompt1.print("Init successful!\n")
        self.ser_status = True
        return True

    def serial_close(self):
        self.prompt1.print(f"Serial close!")
        self.ser_obj.close()
        self.ser_status = False
        my_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        self.canvas1.itemconfig(my_oval, fill="red")  # Fill the circle with RED

    def start_process(self, data_subfolder, file_ext, parameters):
        self.stop_process()

        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("_%H%M%S")
        file_str_ext = self.output_file_name.get("1.0", "end").strip(
            "\n")  # I THINK THIS CATEGORY NAME IS GETTING STRIPPED WRONG
        # if file_str_ext == "":
        #     self.prompt1.print("Detected blank file name, going to use default")
        #     file_str_ext = None

        threading.Thread(target=lambda: self.ser_obj.process_data(self.basefilepath,
                                                                  f"{formatted_datetime}_{file_ext}_{file_str_ext}",
                                                                  "data", # data MODE {raw, timestamp, data}
                                                                  parameters=parameters)
                         ).start()

    def stop_process(self):
        self.ser_obj.stop_process()
