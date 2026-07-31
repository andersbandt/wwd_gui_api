"""USB serial communication tab."""

# import needed packages
import logging
import os
import threading
import time
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import serial

# import user defined modules
from common.serial_api import SerialProcessor
from common.path_helper import get_data_dir
from common.logger import build_log_name
from common import device_protocol
from common.device_protocol import DeviceProtocol, ProtocolError, ConnectionLostError
from common.dump_decoder import (decode_dump, summarize, plot_dump, format_header, export_datastream,
                                  DumpViewConfig, load_imu_processor)
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

        # DeviceProtocol object (binary command channel, cdc_acm_uart1 on the
        # firmware side — a second, independent ttyACM interface from the
        # console/log port above)
        self.dp_obj = None
        self._protocol_busy = False
        self._protocol_conn_watch_id = None

        # View Dump display/processing options, set via "Configure View..."
        self.dump_view_config = DumpViewConfig()

        # init frames within tab
        self.fr_port = guic.SerialConnFrame(self, self.theme_config, self.cc, "USB_serial", self.port_init, lambda: self.port_close(),
                                                  status_cmd=lambda: self.ser_obj.serStatus if self.ser_obj else False)
        self.fr_state = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_test = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_protocol_port = guic.SerialConnFrame(self, self.theme_config, self.cc, "USB_cmd_protocol", self.protocol_port_init, lambda: self.protocol_port_close(),
                                                  status_cmd=lambda: self.dp_obj.serStatus if self.dp_obj else False)
        self.fr_protocol_actions = tk.Frame(self, bg=self.theme_config["light_4"])
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
        self.fr_protocol_port.grid(row=4, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="n")
        self.fr_protocol_actions.grid(row=5, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="n")
        self.prompt.grid(row=1, column=1, rowspan=5, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="nswe")

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
        self.init_fr_protocol_actions()

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

    def init_fr_protocol_actions(self):
        lbl = ttk.Label(self.fr_protocol_actions, text="Device Protocol", style="TSpunkLabel.TLabel")
        lbl.grid(row=0, column=1, columnspan=2, pady=2)

        btn_ping = Button(self.fr_protocol_actions, text="Ping",
                          command=self.on_ping,
                          fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                          height=1, width=15)
        btn_ping.grid(row=1, column=1, padx=5, pady=5)

        self.btn_dump = Button(self.fr_protocol_actions, text="Dump to File",
                               command=self.on_dump,
                               fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                               height=1, width=15)
        self.btn_dump.grid(row=2, column=1, padx=5, pady=5)

        lbl_postfix = Label(self.fr_protocol_actions, text="Dump filename postfix")
        lbl_postfix.grid(row=2, column=2, padx=(15, 5), pady=5, sticky="w")
        self.dump_postfix_entry = Entry(self.fr_protocol_actions, width=18)
        self.dump_postfix_entry.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        guic.Tooltip(lbl_postfix, "Optional text appended to the dump filename, e.g.\n"
                                   "\"shaky_end\" -> DUMP_20260726120000_shaky_end.bin")

        btn_view_dump = Button(self.fr_protocol_actions, text="View Dump...",
                               command=self.on_view_dump,
                               fg=self.theme_config["fg_dark"], bg=self.theme_config["light_6"],
                               height=1, width=15)
        btn_view_dump.grid(row=2, column=4, padx=5, pady=5)
        guic.Tooltip(btn_view_dump, "Decode a .bin dump file, plot accel/gyro/temperature, and write\n"
                                     "companion _header.txt (time anchors, counts, sample rate) and\n"
                                     "_data.txt (full decoded record stream) files next to it.\n"
                                     "Does not need a live connection.")

        btn_view_dump_config = Button(self.fr_protocol_actions, text="Configure View...",
                                      command=self.open_dump_view_config_dialog,
                                      fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"],
                                      height=1, width=15)
        btn_view_dump_config.grid(row=2, column=5, padx=5, pady=5)
        guic.Tooltip(btn_view_dump_config, "Configure temperature units and optional IMU data\n"
                                            "processing (e.g. a filtering script) for View Dump.")

        self.btn_erase = Button(self.fr_protocol_actions, text="Erase Flash",
                           command=self.on_erase,
                           fg=self.theme_config["error"], bg=self.theme_config["light_3"],
                           height=1, width=15)
        self.btn_erase.grid(row=3, column=1, padx=5, pady=5)

        btn_set_rate = Button(self.fr_protocol_actions, text="Set Data Rates...",
                              command=self.on_set_rate,
                              fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
                              height=1, width=15)
        btn_set_rate.grid(row=4, column=1, padx=5, pady=5)

        guic.Tooltip(self.btn_erase, "Erases the entire on-device flash log. Irreversible.")
        guic.Tooltip(btn_set_rate, "View/change the IMU sample rate and temperature logging interval.")

    def gui_refresh(self, event):
        if not self.fr_port.status:
            self.fr_port.refresh_ports()
        self.fr_port.gui_refresh()
        if not self.fr_protocol_port.status:
            self.fr_protocol_port.refresh_ports()
        self.fr_protocol_port.gui_refresh()


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
            self.start_process(get_data_dir("serial_data"), "data", parameters, logname, show_timestamp,
                               progress_callback=self._log_progress_cb)
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
                kwargs={'logname': logname, 'show_timestamp': show_timestamp,
                        'progress_callback': self._log_progress_cb}
            )
            self.t2.start()
        elif output_mode == "Log to File (Timestamp)":
            logname = self._build_logname("TEXT", "log", date_strf='%Y%m%d')
            self.t2 = guic.StoppableThread(
                target=self.ser_obj.process_data,
                args=(self.basefilepath, get_data_dir("text_data"), "timestamp"),
                kwargs={'logname': logname, 'show_timestamp': show_timestamp,
                        'progress_callback': self._log_progress_cb}
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

    def _start_protocol_connection_watch(self):
        self._protocol_conn_watch_id = self.after(self._CONN_WATCH_MS, self._watch_protocol_connection)

    def _stop_protocol_connection_watch(self):
        if self._protocol_conn_watch_id is not None:
            self.after_cancel(self._protocol_conn_watch_id)
            self._protocol_conn_watch_id = None

    def _watch_protocol_connection(self):
        """Same idea as _watch_connection() but for the command channel.
        Skips the check while a dump/erase/etc. is in flight — that worker
        thread will notice the failure itself via ConnectionLostError and
        call protocol_port_close(), and polling serStatus/os.path.exists()
        concurrently with an active read/write isn't harmful but is just
        redundant noise."""
        if self.dp_obj is None:
            return
        if self._protocol_busy:
            self._protocol_conn_watch_id = self.after(self._CONN_WATCH_MS, self._watch_protocol_connection)
            return
        port = self.dp_obj.port
        port_gone = not self.dp_obj.serStatus or not os.path.exists(port)
        if port_gone:
            self.prompt.print(f"ERROR: command channel connection lost on {port}", "error")
            self.protocol_port_close()
            guih.alert_user("Command channel lost", f"Connection on {port} dropped unexpectedly.\nThe device may have re-enumerated at a different tty path.", "error")
            return
        self._protocol_conn_watch_id = self.after(self._CONN_WATCH_MS, self._watch_protocol_connection)

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
            port = self.ser_obj.port
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
            # Also needed on the unexpected-disconnect path (_watch_connection
            # calls port_close() directly, bypassing SerialConnFrame.disconnect()
            # which is the only other place this gets cleared) — otherwise the
            # port stays marked active and the next connect() attempt refuses
            # with "already in use".
            self.cc.remove_active_connection(port)
        self._recording = False
        self.btn_record.config(text="Start Recording", bg=self.theme_config["light_3"])
        self.fr_port.set_status(False)

    def _log_progress_cb(self, n):
        """Called from the logger thread every 200 lines; posts to GUI thread via after()."""
        self.after(0, lambda: self.prompt.print(f"Logged {n} lines to file..."))

    def start_process(self, data_subfolder, data_mode, parameters, logname, show_timestamp,
                      progress_callback=None):
        if self.t3 is not None:
            self.t3.stop()

        self.t3 = guic.StoppableThread(
            target=lambda: self.ser_obj.process_data(self.basefilepath,
                                                     data_subfolder,
                                                     data_mode,
                                                     parameters=parameters,
                                                     logname=logname,
                                                     show_timestamp=show_timestamp,
                                                     progress_callback=progress_callback)
        )
        self.t3.start()

    #################################
    #### DEVICE PROTOCOL (cdc_acm_uart1) ###
    #################################

    # NOTE: this is called by fr_protocol_port (a SerialConnFrame). Must return True/False.
    def protocol_port_init(self):
        port = self.fr_protocol_port.get_port()

        self.prompt.print(f"Protocol: connecting to {port} @ 115200 baud")
        try:
            self.dp_obj = DeviceProtocol(port, baud_rate=115200)
        except (serial.serialutil.SerialException, OSError, ConnectionLostError) as e:
            self.dp_obj = None
            self.prompt.print(f"ERROR: {e}", "error")
            guih.alert_user("Can't start command channel", str(e), "error")
            return False

        self.prompt.print("Protocol: connected")
        self._start_protocol_connection_watch()
        return True

    def protocol_port_close(self):
        self._stop_protocol_connection_watch()
        if self.dp_obj is not None:
            port = self.dp_obj.port
            self.dp_obj.close()
            self.dp_obj = None
            # Same "already in use" fix as port_close(): both the unexpected-
            # disconnect watcher and _handle_protocol_exception() call this
            # directly rather than through SerialConnFrame.disconnect().
            self.cc.remove_active_connection(port)
        self.fr_protocol_port.set_status(False)
        self._protocol_busy = False

    def _protocol_connected(self):
        if self.dp_obj is None or not self.dp_obj.serStatus:
            self.prompt.print("ERROR: command channel not connected", "error")
            return False
        return True

    def _handle_protocol_exception(self, e, action):
        """Shared error handling for every Device Protocol command. Must only
        be called from the GUI (main) thread — worker threads should route
        through self.after(0, lambda: self._handle_protocol_exception(...)).

        Reports the failure to the prompt and, for a lost connection
        specifically, tears down the (now-stale) DeviceProtocol and updates
        the connection indicator so the UI doesn't keep claiming to be
        connected. Also catches anything NOT already a ProtocolError/
        TimeoutError — a background-thread exception that nobody catches is
        silently swallowed by Tkinter (no crash, no GUI feedback, just a
        traceback in the terminal), which is worse than an ugly message here.
        """
        if isinstance(e, ConnectionLostError):
            self.prompt.print(f"{action} failed: {e}", "error")
            self.prompt.print("Command channel connection lost — disconnecting.", "error")
            self.protocol_port_close()
        elif isinstance(e, (ProtocolError, TimeoutError)):
            self.prompt.print(f"{action} failed: {e}", "error")
        else:
            self.prompt.print(f"{action} failed: unexpected {type(e).__name__}: {e}", "error")
            logger.exception(f"{action} raised an unexpected exception")

    def on_ping(self):
        if not self._protocol_connected():
            return
        try:
            ok = self.dp_obj.ping()
            self.prompt.print("PING -> OK" if ok else "PING -> unexpected response", "error" if not ok else None)
        except Exception as e:
            self._handle_protocol_exception(e, "PING")

    def on_erase(self):
        if not self._protocol_connected():
            return
        if self._protocol_busy:
            self.prompt.print("ERROR: another protocol operation is in progress, wait for it to finish", "error")
            return
        if not guih.promptYesNo("Erase flash", "Erase the entire on-device flash log? This cannot be undone."):
            return

        self._protocol_busy = True
        self.btn_erase.config(text="Erasing...", state="disabled")
        self.prompt.print("ERASE: requesting chip erase (several seconds)...")

        def worker():
            try:
                self.dp_obj.erase()
                self.after(0, lambda: self.prompt.print("ERASE -> OK, flash log cleared"))
            except Exception as e:
                err = e
                self.after(0, lambda: self._handle_protocol_exception(err, "ERASE"))
            finally:
                def reset_btn():
                    self._protocol_busy = False
                    self.btn_erase.config(text="Erase Flash", state="normal")
                self.after(0, reset_btn)

        threading.Thread(target=worker, daemon=True).start()

    def on_set_rate(self):
        if not self._protocol_connected():
            return
        if self._protocol_busy:
            self.prompt.print("ERROR: another protocol operation is in progress", "error")
            return

        try:
            cur_odr, cur_temp = self.dp_obj.get_rate()
        except Exception as e:
            self._handle_protocol_exception(e, "GET_RATE")
            return

        dlg = Toplevel(self)
        dlg.title("Set Data Rates")
        dlg.configure(bg=self.theme_config["light_4"])
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        Label(dlg, text="IMU sample rate (Hz)").grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        odr_var = tk.StringVar(value=str(cur_odr))
        odr_drop = ttk.Combobox(dlg, textvariable=odr_var, state="readonly", width=10,
                                values=[str(h) for h in device_protocol.VALID_IMU_ODR_HZ])
        odr_drop.grid(row=0, column=1, padx=10, pady=(10, 5))

        Label(dlg, text="Temperature interval (s)").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        temp_entry = Entry(dlg, width=12)
        temp_entry.insert(0, str(cur_temp))
        temp_entry.grid(row=1, column=1, padx=10, pady=5)

        status_lbl = Label(dlg, text="", fg=self.theme_config["error"], bg=self.theme_config["light_4"])
        status_lbl.grid(row=2, column=0, columnspan=2, padx=10)

        def apply():
            try:
                new_odr = int(odr_var.get())
                new_temp = int(temp_entry.get())
            except ValueError:
                status_lbl.config(text="Both fields must be integers")
                return

            try:
                applied_odr, applied_temp = self.dp_obj.set_rate(new_odr, new_temp)
            except Exception as e:
                if isinstance(e, ConnectionLostError):
                    self._handle_protocol_exception(e, "SET_RATE")
                    dlg.destroy()
                else:
                    status_lbl.config(text=str(e))
                return

            self.prompt.print(f"SET_RATE -> IMU {applied_odr} Hz, temperature every {applied_temp} s")
            dlg.destroy()

        btn_frame = Frame(dlg, bg=self.theme_config["light_4"])
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        Button(btn_frame, text="Apply", command=apply,
              fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"], width=10).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Cancel", command=dlg.destroy,
              fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"], width=10).grid(row=0, column=1, padx=5)

    def on_dump(self):
        if not self._protocol_connected():
            return
        if self._protocol_busy:
            self.prompt.print("ERROR: another protocol operation is in progress", "error")
            return

        self._protocol_busy = True
        self.btn_dump.config(text="Dumping...", state="disabled")
        self.prompt.print("DUMP: requesting flash dump (this can take over a minute)...")

        # Read the postfix entry here (main/GUI thread) — the worker thread
        # below must not touch Tkinter widgets directly.
        postfix = self.dump_postfix_entry.get().strip() or None

        t0 = time.time()

        def progress_cb(received, total):
            if received % (64 * 2176) == 0:  # ~every 64 pages
                if total:
                    pct = 100.0 * received / total
                    self.after(0, lambda r=received, t=total, p=pct: self.prompt.print(
                        f"  ...{r}/{t} bytes ({p:.0f}%)"))
                else:
                    self.after(0, lambda r=received: self.prompt.print(f"  ...{r} bytes received"))

        received_so_far = [0]  # mutable box so progress_cb's closure can update it

        def progress_cb_wrapped(received, total):
            received_so_far[0] = received
            progress_cb(received, total)

        def worker():
            try:
                data, device_crc = self.dp_obj.dump(progress_callback=progress_cb_wrapped)
                logname = build_log_name("DUMP", postfix, "bin")
                outdir = get_data_dir("flash_dumps")
                outpath = os.path.join(outdir, logname)
                with open(outpath, "wb") as f:
                    f.write(data)
                elapsed = time.time() - t0
                self.after(0, lambda: self.prompt.print(
                    f"DUMP complete: {len(data)} bytes in {elapsed:.1f}s, crc32=0x{device_crc:08x} -> {outpath}"))
            except Exception as e:
                err = e
                def report():
                    self._handle_protocol_exception(err, "DUMP")
                    if received_so_far[0]:
                        self.prompt.print(
                            f"  ({received_so_far[0]} bytes were received before the failure — not saved)",
                            "error")
                self.after(0, report)
            finally:
                def reset_btn():
                    self._protocol_busy = False
                    self.btn_dump.config(text="Dump to File", state="normal")
                self.after(0, reset_btn)

        threading.Thread(target=worker, daemon=True).start()

    def on_view_dump(self):
        """Decode and plot a .bin dump file. Works on any previously-saved
        dump — doesn't need a live device connection."""
        outdir = get_data_dir("flash_dumps")
        filepath = filedialog.askopenfilename(
            title="Select a flash dump",
            initialdir=outdir,
            filetypes=[("Flash dump", "*.bin"), ("All files", "*.*")])
        if not filepath:
            return

        try:
            with open(filepath, "rb") as f:
                data = f.read()
        except OSError as e:
            self.prompt.print(f"ERROR: couldn't read {filepath}: {e}", "error")
            return

        self.prompt.print(f"Decoding {filepath} ({len(data)} bytes)...")
        try:
            df = decode_dump(data)
        except Exception as e:
            self.prompt.print(f"ERROR: decode failed: {e}", "error")
            logger.exception("dump decode failed")
            return

        for line in summarize(df).splitlines():
            self.prompt.print(line)

        base, _ = os.path.splitext(filepath)
        header_path = base + "_header.txt"
        data_path = base + "_data.txt"
        try:
            with open(header_path, "w") as f:
                f.write(format_header(df, size_bytes=len(data)))
            export_datastream(df, data_path)
            self.prompt.print(f"Wrote {os.path.basename(header_path)} and {os.path.basename(data_path)}")
        except OSError as e:
            self.prompt.print(f"ERROR: couldn't write text export: {e}", "error")

        imu_processor = None
        cfg = self.dump_view_config
        if cfg.imu_processing_enabled and cfg.imu_script_path:
            try:
                imu_processor = load_imu_processor(cfg.imu_script_path, cfg.imu_func_name)
            except Exception as e:
                self.prompt.print(f"ERROR: couldn't load IMU processing script: {e}", "error")
                logger.exception("IMU processor load failed")
                return

        try:
            plot_dump(df, title=os.path.basename(filepath), temp_unit=cfg.temp_unit, imu_processor=imu_processor)
        except Exception as e:
            self.prompt.print(f"ERROR: {e}", "error")
            logger.exception("plot_dump failed")

    def open_dump_view_config_dialog(self):
        """Modal popup to configure View Dump's display/processing options
        (temperature unit, optional IMU processing script). Mirrors the
        Logger tab's "Configure OSC..." dialog pattern."""
        cfg = self.dump_view_config

        dialog = tk.Toplevel(self)
        dialog.title("View Dump Configuration")
        dialog.configure(bg=self.theme_config["bg_light"])
        dialog.grab_set()

        ttk.Label(dialog, text="View Dump Options", style="TPinkLabel.TLabel",
                  font=(self.theme_config["font"]["family"], 12, "bold")).grid(
            row=0, column=0, columnspan=3, pady=10, padx=10)

        # -- Temperature unit --
        ttk.Label(dialog, text="Temperature unit:", style="TLabel").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        temp_unit_var = tk.StringVar(value=cfg.temp_unit)
        fr_temp = tk.Frame(dialog, bg=self.theme_config["bg_light"])
        fr_temp.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(fr_temp, text="Celsius", variable=temp_unit_var, value="C").pack(side="left", padx=5)
        ttk.Radiobutton(fr_temp, text="Fahrenheit", variable=temp_unit_var, value="F").pack(side="left", padx=5)

        # -- IMU processing --
        ttk.Label(dialog, text="IMU processing", style="TPinkLabel.TLabel",
                  font=(self.theme_config["font"]["family"], 11, "bold")).grid(
            row=2, column=0, columnspan=3, pady=(15, 5), padx=10, sticky="w")

        imu_enabled_var = tk.IntVar(value=1 if cfg.imu_processing_enabled else 0)
        ttk.Checkbutton(dialog, text="Apply a Python function to IMU data before plotting",
                         variable=imu_enabled_var, onvalue=1, offvalue=0).grid(
            row=3, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        ttk.Label(dialog, text="Script:", style="TLabel").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        script_var = tk.StringVar(value=cfg.imu_script_path)
        script_entry = ttk.Entry(dialog, textvariable=script_var, width=40)
        script_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        def browse_script():
            path = filedialog.askopenfilename(
                title="Select IMU processing script",
                filetypes=[("Python files", "*.py"), ("All files", "*.*")])
            if path:
                script_var.set(path)

        tk.Button(dialog, text="Browse...", command=browse_script,
                  fg=self.theme_config["fg_dark"], bg=self.theme_config["light_1"]).grid(
            row=4, column=2, padx=5, pady=5)

        ttk.Label(dialog, text="Function name:", style="TLabel").grid(
            row=5, column=0, padx=10, pady=5, sticky="w")
        func_name_var = tk.StringVar(value=cfg.imu_func_name)
        ttk.Entry(dialog, textvariable=func_name_var, width=20).grid(
            row=5, column=1, padx=5, pady=5, sticky="w")

        guic.Tooltip(script_entry, "A .py file defining a top-level function that takes and\n"
                                    "returns a DataFrame of IMU_FIFO rows (accel_x/y/z, gyro_x/y/z,\n"
                                    "imu_timestamp, seconds_since_boot, ...), e.g. a filter.")

        # -- OK / Cancel --
        def on_ok():
            cfg.temp_unit = temp_unit_var.get()
            cfg.imu_processing_enabled = bool(imu_enabled_var.get())
            cfg.imu_script_path = script_var.get().strip()
            cfg.imu_func_name = func_name_var.get().strip() or "process"
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=self.theme_config["bg_light"])
        btn_frame.grid(row=6, column=0, columnspan=3, pady=10)
        tk.Button(btn_frame, text="OK", width=10, command=on_ok,
                  bg=self.theme_config["success"], fg=self.theme_config["fg_light"]).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Cancel", width=10, command=dialog.destroy,
                  bg=self.theme_config["error"], fg=self.theme_config["fg_light"]).pack(side="left", padx=10)

