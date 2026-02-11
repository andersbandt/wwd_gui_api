"""USB serial communication tab."""

# import needed packages
import tkinter as tk
from tkinter import *
from tkinter import ttk
import threading
import serial
from datetime import datetime
import configparser
import os

# import user defined modules
from common.serial_helper import SerialProcessor
from gui import gui_helper as guih
from gui import gui_class as guic


class TabUSB(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # serial Object (SerialProcessor)
        self.ser_obj = None

        # init frames within tab
        self.fr_state = tk.Frame(self, bg=self.theme_config["light_4"])
        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                   "Debug serial",
                                  height=self.theme_config["size"]["h_prompt"]*2.75,
                                  width=self.theme_config["size"]["w_prompt"])
        self.fr_port = guic.SerialConnFrame(self, self.theme_config, self.cc, "USB_serial", self.port_init, lambda: self.port_close(),
                                                  status_cmd=lambda: self.ser_obj.serStatus if self.ser_obj else False)
        if autoconnect:
            self.fr_port.connect_previous_port()


        # initialize threads (actual init is in thread_print) or something
        self.t1 = None
        self.t2 = None
        self.t3 = None

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_port.grid(row=1, column=0, padx=30, pady=12)
        self.fr_state.grid(row=2, column=0, padx=30, pady=12)
        self.prompt.grid(row=1, column=1, rowspan=2, padx=30, pady=12, sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)


    def initTabContent(self):
        print("Initializing tab 4 (USB) content")

        # add tab header information
        l1 = ttk.Label(self, text="USB (COM) connection", style="BW.TLabel", font=("Arial", 16))
        l1.grid(row=0, column=0, columnspan=2)

        self.init_fr_state()

    def init_fr_state(self):
        # TARGET - BUTTON/STATUS
        btn_act_test = Button(self.fr_state, text="Activate test mode",
                              command=self.activate_test_mode,
                              fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                              height=2, width=15)
        btn_act_test.grid(row=1, column=2, padx=15, pady=22)

        self.test_status_circ = guic.ColorCircle(self.fr_state, 50, 50, self.theme_config["bg_dark"])
        self.test_status_circ.grid(row=1, column=3, padx=15, pady=22)

        # TOGGLE
        btn_toggle_target = Button(self.fr_state, text="Set test type",
                                   command=self.set_test_type,
                                   fg=self.theme_config["fg_dark"], bg=self.theme_config["light_6"],
                                   height=2, width=15)
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

        # add output mode selector
        Label(self.fr_state, text="Output Mode").grid(row=3, column=1, padx=5, pady=5)
        self.output_mode_drop = guih.generate_drop_down(
            self.fr_state,
            ["Display on Screen", "Log to File (Raw)", "Log to File (Timestamp)"]
        )
        self.output_mode_drop[0].grid(row=3, column=3, padx=15, pady=5)

        # add output file name box
        Label(self.fr_state, text="Output file name").grid(row=4, column=1, padx=5, pady=5)
        self.output_file_name = Text(self.fr_state, height=2, width=20)
        self.output_file_name.grid(row=4, column=3)

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()
        self.fr_port.gui_refresh()


    ##############################################################################
    ####      BUTTON ACTION FUNCTIONS        #####################################
    ##############################################################################

    def activate_test_mode(self):
        command = "DAGA"  # tag:HARDCODE
        self.prompt.print(f"INFO: issuing command {command} ...")
        if self.ser_obj is not None:
            if self.ser_obj.serStatus:
                # send the TEST MODE command for ACTIVATION
                self.ser_obj.send_data(command)
                self.prompt.print(f"Issued command!\n")
                self.test_status_circ.set_color(self.theme_config["success"])
        else:
            self.prompt.print("ERROR: can't issue command, no serial connection\n", print_type="error")
            self.test_status_circ.set_color(self.theme_config["error"])
            self.test_status_circ.set_color(self.theme_config["error"])

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
            print(f"ERROR: Unknown test command: {test_type_command}")
            self.prompt.print(f"ERROR: Unknown test command: {test_type_command}", "error")
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
    #### THREADS    #################
    #################################

    def display_serial_data(self, timestamp, data):
        """
        Callback for displaying serial data on GUI prompt.
        Called from SerialProcessor thread, uses tkinter's after() for thread safety.

        Args:
            timestamp: Timestamp string from serial data
            data: Serial data string (may contain multiple newline-delimited lines)
        """
        # Split multi-line chunks so each line gets its own timestamp
        lines = data.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line:
                self.after(0, lambda l=line: self.prompt.print(l, timestamp=True))

    def thread_print_display(self):
        self.t1 = guic.StoppableThread(
            target=self.ser_obj.get_data,
            kwargs={'printmode': False})
        self.t1.start()

        # Get selected output mode from dropdown
        output_mode = self.output_mode_drop[1].get()

        if output_mode == "Display on Screen":
            # GUI display mode
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(None, None, None, None),
                kwargs={'gui_callback': self.display_serial_data}
            )
        elif output_mode == "Log to File (Raw)":
            # File logging - raw mode
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, os.path.join("data", "text_data"), "raw") # tag:HARDCODE
            )
        elif output_mode == "Log to File (Timestamp)":
            # File logging - timestamp mode
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, os.path.join("data", "text_data"), "timestamp") # tag:HARDCODE
            )
        else:
            self.prompt.print(f"ERROR: Unknown output mode: {output_mode}", "error")
            return False

        self.t2.start()
        return True

    #################################
    #### SERIAL (COM)  ##############
    #################################

    def get_baud_rate(self):
        """
        Read baud rate from master.ini config file.

        Returns:
            int: Baud rate from config, defaults to 9600 if not found
        """
        config_file_path = "config/master.ini"
        default_baud = 9600

        if not os.path.exists(config_file_path):
            print(f"Config file not found. Using default baud rate: {default_baud}")
            return default_baud

        config = configparser.ConfigParser()
        config.read(config_file_path)

        if "USB" not in config:
            print(f"[USB] section not found in config. Using default baud rate: {default_baud}")
            return default_baud

        try:
            baud_rate = config["USB"].getint("baud_rate", default_baud)
            print(f"Using baud rate from config: {baud_rate}")
            return baud_rate
        except ValueError:
            print(f"Invalid baud rate in config. Using default: {default_baud}")
            return default_baud

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()
        baud_rate = self.get_baud_rate()

        self.prompt.print(f"Init with port: {port} @ {baud_rate} baud")
        try:
            self.ser_obj = SerialProcessor(port, baud_rate)
        except serial.serialutil.SerialException as e:
            self.prompt.print(f"ERROR: {e}")
            self.prompt.print(f"Can't init with port\n")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        threading.Thread(target=self.thread_print_display).start()
        self.prompt.print("Init successful!\n")
        return True

    def port_close(self):
        if self.ser_obj is not None:
            self.t1.stop()
            self.t2.stop()
            self.prompt.print("Serial close!")
            num_lines = self.ser_obj.stop_process()
            self.prompt.print(f"Port closed: {num_lines} lines wrote\n")
            self.ser_obj = None
        self.fr_port.set_status(False)

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

