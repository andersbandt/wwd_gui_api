"""USB serial communication tab."""

# import needed packages
import logging
import os
import tkinter as tk
from tkinter import *
from tkinter import ttk
import serial

# import user defined modules
from common.serial_api import SerialProcessor
from common.path_helper import get_data_dir
from common.logger import build_log_name
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

# TODO: on rate update I would like program to actual query DMM, instead of manually updating to "fast", or "slow", etc.

class TabUSB(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # serial Object (SerialProcessor)
        self.ser_obj = None
        self._recording = False
        self._conn_watch_id = None

        # init frames within tab
        self.fr_port = guic.SerialConnFrame(self, self.theme_config, self.cc, "USB_serial", self.port_init, lambda: self.port_close(),
                                                  status_cmd=lambda: self.ser_obj.serStatus if self.ser_obj else False)
        self.fr_state = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_test = tk.Frame(self, bg=self.theme_config["light_4"])
        self.prompt = guic.Prompt(self, self.theme_config, "Debug serial")

        # initialize threads (actual init is in thread_print) or something
        self.t1 = None
        self.t2 = None
        self.t3 = None

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_port.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_state.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="n")
        self.fr_test.grid(row=3, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="n")
        self.prompt.grid(row=1, column=1, rowspan=3, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nswe")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        if autoconnect:
            self.fr_port.connect_previous_port()

    def initTabContent(self):
        logger.debug("Initializing tab 4 (USB) content")

        self.create_tab_header("USB (COM) connection", columnspan=2)

        self.init_fr_state()
        self.init_fr_test()

    def init_fr_state(self):
        # add output mode selector
        lbl_mode = (Label(self.fr_state, text="Output Mode"))
        lbl_mode.grid(row=3, column=1, padx=5, pady=5)
        self.output_mode_drop = guih.generate_drop_down(
            self.fr_state,
            ["Display on Screen", "Log to File (Raw)", "Log to File (Timestamp)", "Log to File (CSV)", "None"]
        )
        self.output_mode_drop[0].grid(row=3, column=3, padx=15, pady=5)

        # show timestamps checkbox
        self.var_show_timestamp = tk.IntVar(value=1)
        ttk.Checkbutton(self.fr_state, text="Add timestamps",
                        variable=self.var_show_timestamp,
                        onvalue=1, offvalue=0).grid(row=3, column=4, padx=5, pady=5, sticky='w')

        # add output file name box (postfix when not overriding, full name when overriding)
        lbl_filename = Label(self.fr_state, text="Filename postfix")
        lbl_filename.grid(row=4, column=1, padx=5, pady=5)
        self.output_file_name = Text(self.fr_state, height=2, width=20)
        self.output_file_name.grid(row=4, column=3, padx=5, pady=5)

        # override prefix checkbox — when checked, the text box IS the full filename (no auto prefix)
        self.var_override_prefix = tk.IntVar(value=0)
        ttk.Checkbutton(self.fr_state, text="Override prefix",
                        variable=self.var_override_prefix,
                        onvalue=1, offvalue=0).grid(row=4, column=4, padx=5, pady=5, sticky='w')

        # CSV headers (used when output mode is "Log to File (CSV)")
        lbl_csv_headers = Label(self.fr_state, text="CSV Headers")
        lbl_csv_headers.grid(row=5, column=1, padx=5, pady=5)
        self.csv_headers = Text(self.fr_state, height=2, width=20)
        self.csv_headers.grid(row=5, column=3, padx=5, pady=5)

        self.btn_record = Button(self.fr_state, text="Start Recording",
                                 command=self._toggle_recording,
                                 fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                                 height=2, width=14)
        self.btn_record.grid(row=5, column=4, padx=5, pady=5)

        # ── Tooltips ─────────────────────────────────────
        guic.Tooltip(lbl_mode, "Display on Screen: show in console\n"
                               "Log to File (Raw): write bytes as-is\n"
                               "Log to File (Timestamp): text with optional timestamps\n"
                               "Log to File (CSV): comma-delimited data")
        guic.Tooltip(lbl_csv_headers, "comma-separated, e.g. val1,val2\n"
                                      "timestamp column is added automatically when checkbox is checked")
        guic.Tooltip(lbl_filename, "Optional text appended to the auto-generated filename.\n"
                                   "Files are saved to the data/ directory.\n"
                                   "Check 'Override prefix' to use this as the full filename instead.")

    def init_fr_test(self):
        btn_act_test = Button(self.fr_test, text="Activate test mode",
                              command=self.activate_test_mode,
                              fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                              height=2, width=15)
        btn_act_test.grid(row=1, column=2, padx=15, pady=22)

        self.test_status_circ = guic.ColorCircle(self.fr_test, 50, 50, self.theme_config["bg_dark"])
        self.test_status_circ.grid(row=1, column=3, padx=15, pady=22)

        btn_toggle_target = Button(self.fr_test, text="Set test type",
                                   command=self.set_test_type,
                                   fg=self.theme_config["fg_dark"], bg=self.theme_config["light_6"],
                                   height=2, width=15)
        btn_toggle_target.grid(row=2, column=2, padx=15, pady=22)
        self.test_drop = guih.generate_drop_down(
            self.fr_test,
            list(TEST_TYPE_COMMANDS.keys())
        )
        self.test_drop[0].grid(row=2, column=3, padx=15, pady=15)

    def gui_refresh(self, event):
        if not self.fr_port.status:
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

    def display_serial_data(self, timestamp, line):
        """
        Callback for displaying a single complete line on the GUI prompt.
        Called from SerialProcessor thread (line-buffered), uses tkinter's after() for thread safety.
        """
        show_ts = bool(self.var_show_timestamp.get())
        self.after(0, lambda l=line: self.prompt.print_ansi(l, timestamp=show_ts))

    def _build_logname(self, prefix, extension, date_strf='%Y%m%d%H%M%S'):
        """Build a log filename based on user input and override setting."""
        user_text = self.output_file_name.get("1.0", "end").strip().strip("\n")
        override = bool(self.var_override_prefix.get())
        if override and user_text:
            return user_text if user_text.endswith("." + extension) else user_text + "." + extension
        return build_log_name(prefix, user_text or None, extension, date_strf=date_strf)

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

        show_timestamp = bool(self.var_show_timestamp.get())

        if output_mode == "Log to File (CSV)":
            headers_raw = self.csv_headers.get("1.0", "end").strip("\n").strip()
            parameters = [h.strip() for h in headers_raw.split(",") if h.strip()]
            if show_timestamp:
                parameters.insert(0, "timestamp")
            logname = self._build_logname("DATA", "csv")
            self.start_process(get_data_dir("serial_data"), "data", parameters, logname, show_timestamp)
        elif output_mode == "Display on Screen":
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(None, None, None, None),
                kwargs={'gui_callback': self.display_serial_data}
            )
            self.t2.start()
        elif output_mode == "Log to File (Raw)":
            logname = self._build_logname("TEXT", "log", date_strf='%Y%m%d')
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, get_data_dir("text_data"), "raw"),
                kwargs={'logname': logname, 'show_timestamp': show_timestamp}
            )
            self.t2.start()
        elif output_mode == "Log to File (Timestamp)":
            logname = self._build_logname("TEXT", "log", date_strf='%Y%m%d')
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, get_data_dir("text_data"), "timestamp"),
                kwargs={'logname': logname, 'show_timestamp': show_timestamp}
            )
            self.t2.start()
        else:
            self.prompt.print(f"ERROR: Unknown output mode: {output_mode}", "error")
            return

        self._recording = True
        self.btn_record.config(text="Stop Recording", bg=self.theme_config["error"])
        self.prompt.print(f"Recording started ({output_mode}).")

    _CONN_WATCH_MS = 2000  # how often to poll for unexpected port loss

    def _start_connection_watch(self):
        self._conn_watch_id = self.after(self._CONN_WATCH_MS, self._watch_connection)

    def _stop_connection_watch(self):
        if self._conn_watch_id is not None:
            self.after_cancel(self._conn_watch_id)
            self._conn_watch_id = None

    def _watch_connection(self):
        """Periodic GUI-thread check for unexpected port loss.

        Two-pronged: serStatus catches the case where inWaiting() raises an
        OSError (common on Linux). os.path.exists() catches the case where the
        fd silently returns 0 bytes instead of raising — the /dev entry
        disappears immediately when the device re-enumerates at a new path.
        """
        if self.ser_obj is None:
            return
        port = self.ser_obj.port
        port_gone = not self.ser_obj.serStatus or not os.path.exists(port)
        if port_gone:
            self.prompt.print(f"ERROR: connection lost on {port} — device may have changed tty path", "error")
            self.port_close()
            guih.alert_user("Serial port lost", f"Connection on {port} dropped unexpectedly.\nThe device may have re-enumerated at a different tty path.", "error")
            return
        self._conn_watch_id = self.after(self._CONN_WATCH_MS, self._watch_connection)

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
        self._start_connection_watch()
        self.prompt.print("Init successful!")
        return True

    def port_close(self):
        self._stop_connection_watch()
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
            self.ser_obj.close()  # ensure port is closed even if recording was never started
            self.prompt.print(f"Port closed: {num_lines} lines wrote")
            self.ser_obj = None
            self.cc.set_ser(None)
        self._recording = False
        self.btn_record.config(text="Start Recording", bg=self.theme_config["light_3"])
        self.fr_port.set_status(False)

    def start_process(self, data_subfolder, data_mode, parameters, logname, show_timestamp):
        if self.t3 is not None:
            self.t3.stop()

        self.t3 = guic.StoppableThread(
            target=lambda: self.ser_obj.process_data(self.basefilepath,
                                                     data_subfolder,
                                                     data_mode,
                                                     parameters=parameters,
                                                     logname=logname,
                                                     show_timestamp=show_timestamp)
        )
        self.t3.start()

