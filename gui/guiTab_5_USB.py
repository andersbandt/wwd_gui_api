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
# import asyncio
import serial
import time
from datetime import datetime

# import user defined modules
from common.SerialReader import SerialReader
from gui import gui_helper as guih
from gui import gui_class as guic


class TabUSB(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # serial Object
        self.ser_obj = None

        # print welcome text_data
        l1 = ttk.Label(self, text="USB (COM) connection", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(row=0, column=0, columnspan=2)

        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                   "Debug serial",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # init frames within tab
        self.fr_port = guic.SerialConnFrame(self, self.theme_config, self.cc, "USB_serial", self.port_init, lambda: self.port_close)
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=1, column=0, padx=30, pady=12)

        # init state frame
        self.fr_state = tk.Frame(self, bg="#00bcd4")
        self.fr_state.grid(row=1, column=1, padx=30, pady=12)
        self.canvas2 = tk.Canvas(self.fr_state, width=50, height=50)  # create a Canvas widget
        self.test_drop = None  # fr_state
        self.output_file_name = None  # fr_state

        # initialize threads (actual init is in thread_print) or something
        self.t1 = None
        self.t2 = None
        self.t3 = None

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 5 (USB) content")
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
        c1 = tk.Checkbutton(self.fr_state, text='Record?', variable=var2, onvalue=1, offvalue=0)
        c1.grid(row=2, column=4, padx=2)

        # add output file name box
        Label(self.fr_state, text="Output file name").grid(row=3, column=1, padx=5, pady=5)
        self.output_file_name = Text(self.fr_state, height=2, width=20)
        self.output_file_name.grid(row=3, column=3)

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()

        if self.ser_obj is not None:
            if self.ser_obj.serStatus is False:
                # TODO: here is where I can add back that printout to the log that like "USB DISCONNECTED"
                self.ser_obj.stop_process()
                self.fr_port.set_status(False)
                self.t1.stop()
        else:
            self.fr_port.set_status(True)

    ##############################################################################
    ####      BUTTON ACTION FUNCTIONS        #####################################
    ##############################################################################

    def activate_test_mode(self):
        command = "DAGA"  # tag:HARDCODE
        my_oval = self.canvas2.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        self.prompt.print(f"INFO: issuing command {command} ...")
        if self.ser_obj.serStatus:
            # send the TEST MODE command for ACTIVATION
            self.ser_obj.send_data(command)
            self.prompt.print(f"INFO: issued command!\n")
            self.canvas2.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.prompt.print("ERROR: can't issue command, no serial connection\n")
            self.canvas2.itemconfig(my_oval, fill="red")  # Fill the circle with RED

    def set_test_type(self):
        test_type_command = self.test_drop[1].get()
        self.prompt.print(f"INFO: test type {test_type_command} ...")
        if test_type_command == "flash-read":
            command = "FR91"
        elif test_type_command == "flash-read-all":
            command = "FR01"
        elif test_type_command == "flash-erase":
            command = "FE42"
        elif test_type_command == "imu-graph":
            command = "IG85"
        elif test_type_command == "clock-test":
            command = "CR81"
            self.start_process("clock_data", "clock_test", ["timestamp", "ms", "temp"])
        else:
            print("Fuck man no known test command")
            return False

        self.prompt.print(f"INFO: issuing command {command} ...")
        if self.ser_obj.serStatus:
            self.ser_obj.send_data(command)
            self.prompt.print(f"INFO: issued command!\n")
            return True
        else:
            self.prompt.print("ERROR: can't issue command, no serial connection\n")
            return False

    #################################
    #### THREADS SHIT    ############
    #################################

    # NOTE: autoconnect attempt. Problem right now is probably the performance hit with threading
    # def manage_connection(self):
    #     status = True
    #     while status:
    #         if self.ser_obj.serStatus is False:
    #             print("Attempt to reopen serial ...")
    #             self.ser_obj.reopen()
    #             time.sleep(3)

    def thread_print_display(self):
        # TODO ATE: get "RunTimeError: main thread is not in main loop error"
        #       also not needed if my detection of closed serial connection isn't auto working
        # self.t1 = guic.StoppableThread(
        #     target=lambda: self.gui_refresh,
        #     args={"auto"})
        # self.t1.start()

        self.t2 = guic.StoppableThread(
            target=self.ser_obj.get_data,
            kwargs={'printmode': False})
        self.t2.start()

        self.t3 = guic.StoppableThread(
            target=self.ser_obj.process_data,
            args=(self.basefilepath, None, "raw", "text_data")
        )
        self.t3.start()

        return True

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()

        self.prompt.print(f"Init with port: {port}")
        try:
            self.ser_obj = SerialReader(port, 115200)
        except serial.serialutil.SerialException as e:
            self.prompt.print(f"ERROR: {e}")
            self.prompt.print(f"Can't init with port\n")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        threading.Thread(target=self.thread_print_display).start()
        # threading.Timer(1.0, self.thread_print_display).start() # NOTE: I possiblyy had this 1 second delayyy in there for a reason?
        self.prompt.print("Init successful!\n")
        return True

    def port_close(self):
        self.prompt.print("Serial close!")
        self.ser_obj.stop_process()
        self.fr_port.set_status(False)
        self.t2.stop()
        self.t3.stop()

    def start_process(self, data_subfolder, file_ext, parameters):
        self.t3.stop()

        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("_%H%M%S")
        file_str_ext = self.output_file_name.get("1.0", "end").strip(
            "\n")  # I THINK THIS CATEGORY NAME IS GETTING STRIPPED WRONG
        # if file_str_ext == "":
        #     self.prompt1.print("Detected blank file name, going to use default")
        #     file_str_ext = None

        threading.Thread(target=lambda: self.ser_obj.process_data(self.basefilepath,
                                                                  f"{formatted_datetime}_{file_ext}_{file_str_ext}",
                                                                  "data",
                                                                  data_subfolder,
                                                                  parameters=parameters)
                         ).start()

    def stop_process(self):
        self.ser_obj.stop_process()
