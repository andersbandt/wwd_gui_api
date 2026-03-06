"""USB serial communication tab."""

# import needed packages
import logging
import tkinter as tk
from tkinter import *
from tkinter import ttk
import serial

# import user defined modules
from common.serial_api import SerialProcessor
from common.path_helper import get_data_dir
from gui import gui_helper as guih
from gui import gui_class as guic

logger = logging.getLogger(__name__)

# Target serial commands
ACTIVATE_TEST_CMD = "DAGA"
TEST_TYPE_COMMANDS = {
    "flash-read":     "FR91",
    "flash-read-all": "FR01",
    "flash-erase":    "FE42",
    "specific-graph":      "IG85",
    "clock-test":     "CR81",
}


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
        self.prompt = guic.Prompt(self, self.theme_config, "Debug serial")
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
        self.fr_port.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_state.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="n")
        self.prompt.grid(row=1, column=1, rowspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nswe")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    def initTabContent(self):
        logger.debug("Initializing tab 4 (USB) content")

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
            list(TEST_TYPE_COMMANDS.keys())
        )
        self.test_drop[0].grid(row=2, column=3, padx=15, pady=15)

        # add output mode selector
        Label(self.fr_state, text="Output Mode").grid(row=3, column=1, padx=5, pady=5)
        self.output_mode_drop = guih.generate_drop_down(
            self.fr_state,
            ["Display on Screen", "Log to File (Raw)", "Log to File (Timestamp)", "Log to File (CSV)", "None"]
        )
        self.output_mode_drop[0].grid(row=3, column=3, padx=15, pady=5)

        self.var_show_timestamp = tk.IntVar(value=1)
        ttk.Checkbutton(self.fr_state, text="Show timestamps",
                        variable=self.var_show_timestamp,
                        onvalue=1, offvalue=0).grid(row=3, column=4, padx=5, pady=5, sticky='w')

        # add output file name box
        Label(self.fr_state, text="Output file name").grid(row=4, column=1, padx=5, pady=5)
        self.output_file_name = Text(self.fr_state, height=2, width=20)
        self.output_file_name.grid(row=4, column=3)

        # CSV headers (used when output mode is "Log to File (CSV)")
        Label(self.fr_state, text="CSV Headers").grid(row=5, column=1, padx=5, pady=5)
        self.csv_headers = Text(self.fr_state, height=2, width=20)
        self.csv_headers.grid(row=5, column=3)
        Label(self.fr_state, text="comma-separated, e.g. timestamp,val1,val2",
              fg="gray").grid(row=6, column=3, padx=5, sticky='w')

        self._recording = False
        self.btn_record = Button(self.fr_state, text="Start Recording",
                                 command=self._toggle_recording,
                                 fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                                 height=2, width=14)
        self.btn_record.grid(row=4, column=4, padx=5, pady=5)

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()
        self.fr_port.gui_refresh()


    ##############################################################################
    ####      BUTTON ACTION FUNCTIONS        #####################################
    ##############################################################################

    def activate_test_mode(self):
        command = ACTIVATE_TEST_CMD
        self.prompt.print(f"INFO: issuing command {command} ...")
        if self.ser_obj is not None:
            if self.ser_obj.serStatus:
                # send the TEST MODE command for ACTIVATION
                self.ser_obj.send_data(command)
                self.prompt.print(f"Issued command!")
                self.test_status_circ.set_color(self.theme_config["success"])
        else:
            self.prompt.print("ERROR: can't issue command, no serial connection", print_type="error")
            self.test_status_circ.set_color(self.theme_config["error"])

    def set_test_type(self):
        test_type_command = self.test_drop[1].get()
        self.prompt.print(f"INFO: test type {test_type_command} ...")

        command = TEST_TYPE_COMMANDS.get(test_type_command)
        if command is None:
            logger.error(f"Unknown test command: {test_type_command}")
            self.prompt.print(f"ERROR: Unknown test command: {test_type_command}", "error")
            return False

        self.prompt.print(f"INFO: issuing command {command} ...")
        if self.ser_obj is not None:
            if self.ser_obj.serStatus:
                self.ser_obj.send_data(command)
                self.prompt.print(f"INFO: issued command!")
                return True
            self.prompt.print("ERROR: can't issue command, no serial connection")
            return False
        else:
            self.prompt.print("ERROR: can't issue command, no serial connection")
            return False

    #################################
    #### THREADS    #################
    #################################

    def display_serial_data(self, timestamp, data):
        """
        Callback for displaying serial data on GUI prompt.
        Called from SerialProcessor thread, uses tkinter's after() for thread safety.

        Args:
            timestamp: Unused — provided by SerialProcessor callback contract
            data: Serial data string (may contain multiple newline-delimited lines)
        """
        show_ts = bool(self.var_show_timestamp.get())
        # Split multi-line chunks so each line gets its own timestamp
        lines = data.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line:
                self.after(0, lambda l=line: self.prompt.print(l, timestamp=show_ts))

    def _toggle_recording(self):
        if self._recording:
            if self.ser_obj:
                self.ser_obj.procStatus = False
            if self.t2 is not None:
                self.t2.stop()
                self.t2 = None
            if self.t3 is not None:
                self.t3.stop()
                self.t3 = None
            self._recording = False
            self.btn_record.config(text="Start Recording", bg=self.theme_config["light_3"])
            self.prompt.print("Recording stopped.")
            return

        if self.ser_obj is None or not self.ser_obj.serStatus:
            self.prompt.print("ERROR: not connected, can't start recording", "error")
            return

        output_mode = self.output_mode_drop[1].get()
        if output_mode == "None":
            self.prompt.print("ERROR: select an output mode first", "error")
            return

        if output_mode == "Log to File (CSV)":
            headers_raw = self.csv_headers.get("1.0", "end").strip("\n").strip()
            parameters = [h.strip() for h in headers_raw.split(",") if h.strip()]
            self.start_process("serial_data", parameters)
        elif output_mode == "Display on Screen":
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(None, None, None, None),
                kwargs={'gui_callback': self.display_serial_data}
            )
            self.t2.start()
        elif output_mode == "Log to File (Raw)":
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, get_data_dir("text_data"), "raw")
            )
            self.t2.start()
        elif output_mode == "Log to File (Timestamp)":
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, get_data_dir("text_data"), "timestamp")
            )
            self.t2.start()
        else:
            self.prompt.print(f"ERROR: Unknown output mode: {output_mode}", "error")
            return

        self._recording = True
        self.btn_record.config(text="Stop Recording", bg=self.theme_config["error"])
        self.prompt.print(f"Recording started ({output_mode}).")

    def thread_print_display(self):
        """Start serial reader (t1) on connect. Recording is started separately via the record button."""
        self.t1 = guic.StoppableThread(
            target=self.ser_obj.get_data,
            kwargs={'printmode': False})
        self.t1.start()

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        port = self.fr_port.get_port()
        baud_rate = self.cc.config_svc.get_baud_rate()

        self.prompt.print(f"Init with port: {port} @ {baud_rate} baud")
        try:
            self.ser_obj = SerialProcessor(port, baud_rate)
        except serial.serialutil.SerialException as e:
            self.prompt.print(f"ERROR: {e}")
            self.prompt.print(f"Can't init with port")
            guih.alert_user("Can't start COM port", e, "error")
            return False

        self.cc.set_ser(self.ser_obj)
        self.thread_print_display()  # starts t1 (serial reader)
        self.prompt.print("Init successful!")
        return True

    def port_close(self):
        if self.ser_obj is not None:
            if self.t1 is not None:
                self.t1.stop()
            if self.t2 is not None:
                self.t2.stop()
            if self.t3 is not None:
                self.t3.stop()
                self.t3 = None
            self.prompt.print("Serial close!")
            num_lines = self.ser_obj.stop_process()
            self.prompt.print(f"Port closed: {num_lines} lines wrote")
            self.ser_obj = None
            self.cc.set_ser(None)
        self._recording = False
        self.btn_record.config(text="Start Recording", bg=self.theme_config["light_3"])
        self.fr_port.set_status(False)

    def start_process(self, data_subfolder, parameters):
        if self.t3 is not None:
            self.t3.stop()

        filename = self.output_file_name.get("1.0", "end").strip().strip("\n")
        if not filename:
            filename = None

        self.t3 = guic.StoppableThread(
            target=lambda: self.ser_obj.process_data(self.basefilepath,
                                                     data_subfolder,
                                                     "data",
                                                     parameters=parameters,
                                                     filename=filename)
        )
        self.t3.start()

