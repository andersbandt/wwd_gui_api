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
import time
from datetime import datetime

# import user defined modules
from common.SerialReader import SerialReader
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.guiTab_parent import ThemedFrame

class tabUSB(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.frame.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # serial Object
        self.ser_obj = None
        self.ser_status = False

        # print welcome text
        l1 = ttk.Label(self.frame, text="USB (COM) connection", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(row=0, column=0, columnspan=2)

        self.prompt1 = guic.Prompt(self.frame, "Debug serial", height=14, width=140)
        self.prompt1.grid(row=10, column=0, columnspan=4, padx=30, pady=12)
        # self.fr_prompt2 = tk.Frame(self.frame, bg="purple")
        # self.fr_prompt2.grid(row=0, column=2, rowspan=5, columnspan=1, padx=12, pady=12)
        # self.prompt2 = guic.Prompt(self.fr_prompt2, "Serial output", "black", height=30, width=100)

        # init frames within tab
        self.fr_port = guic.SerialConnFrame(self.frame, "USB serial", self.connect_serial, lambda: self.serial_close(), bg="#00bcd4")
        self.fr_port.initialize_fr()
        self.fr_port.grid(row=1, column=0, padx=30, pady=12)

        # init state frame
        self.fr_state = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_state.grid(row=2, column=0, padx=30, pady=12)
        self.canvas2 = tk.Canvas(self.fr_state, width=50, height=50)  # create a Canvas widget
        self.test_drop = None  # fr_state
        self.output_file_name = None  # fr_state

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab XDS110 content")
        self.init_fr_state()

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
        serial_port = self.fr_port.get_port()
        error_flag |= self.serial_init(serial_port)

        if self.ser_status:
            self.prompt1.print(f"Starting print threading")
            # threading.Thread(target=self.thread_print_display).start()
            threading.Timer(1.0, self.thread_print_display).start()

        self.fr_port.set_status(self.ser_status)

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
                if self.ser_status:
                    self.ser_obj.stop_process()
                    self.ser_status = False
                    self.fr_port.set_status(self.ser_status)
                    my_oval = self.canvas2.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
                    self.canvas2.itemconfig(my_oval, fill="red")  # Fill the circle with RED
            else:
                self.fr_port.set_status(True)
            time.sleep(5)

    # TODO: try to flow flush this auto-reconnect thread. Problem right now is probably the performance hit with threading
    def manage_connection(self):
        status = True
        while status:
            if self.ser_obj.serStatus is False:
                print("Attempt to reopen serial ...")
                self.ser_obj.reopen()
                time.sleep(3)

            if self.ser_status is False:
                status = False

# TODO: performance of the application is unusable after a few "connect" and "disconnect" cycles. Need to improve handling of THREADS
    def thread_print_display(self):
        print("Thread print!")
        # self.prompt2.clear()

        print("Starting thread 1 (gui refresh)")
        t1 = threading.Thread(target=self.gui_refresh, daemon=True)
        t1.start()

        print("Starting thread 3 (get_data)")
        self.t3 = guic.StoppableThread(target=self.ser_obj.get_data, kwargs={'printmode': False})
        self.t3.start()

        print("Starting thread 2 (process_data)")
        self.t2 = guic.StoppableThread(
            target=self.ser_obj.process_data,
            args=(self.basefilepath, None, "raw")
        )
        self.t2.start()

        print("Done with thread creation! Successful exit hopefully!")
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
        self.ser_obj.stop_process()
        self.ser_status = False
        self.fr_port.set_status(self.ser_status)
        self.t2.stop()

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
                                                                  "data",  # data MODE {raw, timestamp, data}
                                                                  parameters=parameters)
                         ).start()

    def stop_process(self):
        self.ser_obj.stop_process()
