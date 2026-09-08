"""Oscilloscope control tab."""

# import needed GUI packages
import logging
import tkinter as tk
from tkinter import ttk, filedialog

# import needed packages
import os
import subprocess
import sys
import threading
from datetime import datetime

# import user defined modules
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS
from common import capture_naming
from common import path_helper

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic

logger = logging.getLogger(__name__)



class TabOSC(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        self.fr_port = None
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_channel = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_tb_trig = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_capture = tk.Frame(self, bg=self.theme_config["light_4"])

        # oscilloscope state
        self.id = None
        self.channel_count = 4
        self.chan_on = [False, False, False, False]

        # 1-2-5 timebase sequence (seconds/div)
        self.tb_steps = [
            5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9,
            1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6,
            1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3,
            1.0, 2.0, 5.0, 10.0, 20.0, 50.0,
        ]
        self.tb_index = 14  # default ~200us
        self.tb_label = None

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "OSC Console Output")

        # initialize tab content
        self.initTabContent()

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "OSC_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3,
                                            status_cmd=lambda: self.cc.get_osc_status())
        if autoconnect:
            self.fr_port.connect_previous_port()

        # place everything in grid
        self.fr_info.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.fr_port.grid(row=1, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="N")
        self.fr_control.grid(row=1, column=2, rowspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.fr_capture.grid(row=3, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.fr_channel.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.fr_tb_trig.grid(row=2, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.prompt.grid(row=3, column=0, columnspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)


    def initTabContent(self):
        logger.debug("Initializing tab 10 (OSC) content")
        self.create_tab_header("OSC Control", columnspan=3)
        self.init_fr_info()
        self.init_fr_channel()
        self.init_fr_tb_trig()
        self.init_fr_control()
        self.init_fr_capture()

    # =========================================================================
    # fr_info — Device Info
    # =========================================================================
    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Oscilloscope Info', style="TPinkLabel.TLabel", width=20)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # equipment selector dropdown
        self.registry = equipment_manager.get_instruments("osc")
        self.cc.osc_service.set_registry(self.registry)
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

        # Load previous model if available
        previous_model = self.cc.get_used_model("OSC_PyVISA")
        if previous_model and previous_model in self.registry:
            self.ate_drop[1].set(previous_model)
            logger.info(f"Restored previous OSC model: {previous_model}")

        # Device ID
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=25, height=2, relief='sunken', anchor='w', wraplength=170, justify='left')

        # Connected timestamp
        self.labelTimeConnected = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        self.labelID.grid(row=1, column=0, sticky='W', padx=5, pady=2)
        self.labelIDValue.grid(row=1, column=1, sticky='W', padx=5, pady=2)
        self.labelTimeConnected.grid(row=2, column=0, sticky='W', padx=5, pady=2)
        self.labelTimeConnectedValue.grid(row=2, column=1, sticky='W', padx=5, pady=2)

        # UPDATE button
        self.btn_update = tk.Button(self.fr_info, text='UPDATE OSC', command=self.update_osc)
        self.btn_update.grid(row=3, column=2, pady=5, padx=3, sticky='W')

    # =========================================================================
    # fr_channel — Per-Channel Controls (4 channels)
    # =========================================================================
    def init_fr_channel(self):
        fr = self.fr_channel

        # clear existing widgets
        for w in fr.winfo_children():
            w.destroy()

        ttk.Label(fr, text="Channel Controls", style="TPinkLabel.TLabel").grid(
            row=0, column=0, columnspan=6, pady=5)

        # Header row
        headers = ["CH", "Enable", "V/div", "", "Coupling", "Offset", ""]
        for c, h in enumerate(headers):
            ttk.Label(fr, text=h, style="TLabel").grid(row=1, column=c, padx=3, pady=2)

        self.chan_toggle_btns = []
        self.chan_scale_entries = []
        self.chan_coupling_drops = []
        self.chan_offset_entries = []

        for i in range(self.channel_count):
            ch = i + 1
            row = i + 2

            # Channel label
            ttk.Label(fr, text=f"{ch}", style="TLabel").grid(row=row, column=0, padx=5, pady=3)

            # Enable toggle button
            btn = tk.Button(fr, text="OFF", width=5, bg=self.theme_config["error"],
                            command=lambda c=ch: self.toggle_channel(c))
            btn.grid(row=row, column=1, padx=3, pady=3)
            self.chan_toggle_btns.append(btn)

            # Scale entry + set button
            scale_entry = tk.Entry(fr, width=8)
            scale_entry.grid(row=row, column=2, padx=3, pady=3)
            self.chan_scale_entries.append(scale_entry)

            tk.Button(fr, text="Set", width=4,
                      command=lambda c=ch, e=scale_entry: self.set_channel_scale(c, e.get())
                      ).grid(row=row, column=3, padx=3, pady=3)

            # Coupling dropdown
            coup_drop = guih.generate_drop_down(fr, ["DC", "AC"])
            coup_drop[1].set("DC")
            coup_drop[0].grid(row=row, column=4, padx=3, pady=3)
            self.chan_coupling_drops.append(coup_drop)

            tk.Button(fr, text="Set", width=4,
                      command=lambda c=ch, d=coup_drop: self.set_channel_coupling(c, d[1].get())
                      ).grid(row=row, column=4, padx=3, pady=3, sticky="E")

            # Offset entry + set button
            off_entry = tk.Entry(fr, width=8)
            off_entry.grid(row=row, column=5, padx=3, pady=3)
            self.chan_offset_entries.append(off_entry)

            tk.Button(fr, text="Set", width=4,
                      command=lambda c=ch, e=off_entry: self.set_channel_offset(c, e.get())
                      ).grid(row=row, column=6, padx=3, pady=3)

    # =========================================================================
    # fr_control — Acquisition (run/stop + type), Save/Recall, Measure
    # =========================================================================
    def init_fr_control(self):
        fr = self.fr_control

        # clear existing widgets
        for w in fr.winfo_children():
            w.destroy()

        cur_row = 0

        # --- Acquisition Controls ---
        ttk.Label(fr, text="Acquisition", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=5)
        cur_row += 1

        tk.Button(fr, text="Run", width=8, command=self.acq_run).grid(
            row=cur_row, column=0, padx=5, pady=3)
        tk.Button(fr, text="Stop", width=8, command=self.acq_stop).grid(
            row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Single", width=8, command=self.acq_single).grid(
            row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        # --- Acquisition Type ---
        lbl_acq_type = ttk.Label(fr, text="Type", style="TLabel")
        lbl_acq_type.grid(row=cur_row, column=0, padx=5, pady=3, sticky="w")
        guic.Tooltip(lbl_acq_type,
                     "Acquisition type (:ACQuire:TYPE)\n\n"
                     "NORMal      — standard sample mode\n"
                     "AVERage     — averages N waveforms (N = Avg Count, 1–65536)\n"
                     "              not available in segmented memory mode\n"
                     "HRESolution — smoothing; averages oversampled points per\n"
                     "              display point; useful at slow sweep speeds\n"
                     "              to reduce noise\n"
                     "PEAK        — peak detect; Avg Count has no meaning\n\n"
                     "AVERage and HRESolution yield extra vertical resolution;\n"
                     "use WORD or ASCii waveform format when reading data.")
        self.acq_type_drop = guih.generate_drop_down(fr, ["NORMal", "AVERage", "HRESolution", "PEAK"])
        self.acq_type_drop[1].set("NORMal")
        self.acq_type_drop[0].grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_acq_type(self.acq_type_drop[1].get())
                  ).grid(row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        # Avg Count (only meaningful for AVERage mode)
        lbl_acq_count = ttk.Label(fr, text="Avg Count", style="TLabel")
        lbl_acq_count.grid(row=cur_row, column=0, padx=5, pady=3, sticky="w")
        guic.Tooltip(lbl_acq_count, "Number of waveforms to average (1–65536).\nOnly applies in AVERage mode.")
        self.acq_count_entry = tk.Entry(fr, width=10)
        self.acq_count_entry.insert(0, "4")
        self.acq_count_entry.grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_acq_count(self.acq_count_entry.get())
                  ).grid(row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        # --- Save / Recall ---
        ttk.Label(fr, text="Save / Recall", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=(10, 5))
        cur_row += 1

        self.save_filename_entry = tk.Entry(fr, width=18)
        self.save_filename_entry.grid(row=cur_row, column=0, columnspan=2, padx=5, pady=3, sticky="W")
        cur_row += 1

        tk.Button(fr, text="Screenshot", width=10, command=self.save_screenshot).grid(
            row=cur_row, column=0, padx=5, pady=3)
        tk.Button(fr, text="Save Setup", width=10, command=self.save_setup).grid(
            row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Recall Setup", width=10, command=self.recall_setup).grid(
            row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        # --- Autoscale ---
        tk.Button(fr, text="Autoscale", width=10, command=self.autoscale).grid(
            row=cur_row, column=0, padx=5, pady=(10, 3))
        cur_row += 1

        # --- Quick Measurements ---
        ttk.Label(fr, text="Measurements", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=(10, 5))
        cur_row += 1

        ttk.Label(fr, text="Channel", style="TLabel").grid(row=cur_row, column=0, padx=5, pady=3)
        self.meas_ch_drop = guih.generate_drop_down(fr, ["1", "2", "3", "4"])
        self.meas_ch_drop[1].set("1")
        self.meas_ch_drop[0].grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Measure All", width=10, command=self.measure_all).grid(
            row=cur_row, column=2, padx=5, pady=3)

    # =========================================================================
    # fr_tb_trig — Timebase + Trigger
    # =========================================================================
    def init_fr_tb_trig(self):
        fr = self.fr_tb_trig
        px = self.theme_config["pad"]["xpad_l"]
        py = self.theme_config["pad"]["xpad_s"]

        # clear existing widgets
        for w in fr.winfo_children():
            w.destroy()

        cur_row = 0

        # --- Timebase Controls ---
        ttk.Label(fr, text="Timebase", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=py)
        cur_row += 1

        self.tb_label = ttk.Label(fr, text=self._format_timebase(self.tb_steps[self.tb_index]),
                                   style="TLabel", width=12, anchor="center")
        self.tb_label.grid(row=cur_row, column=1, padx=px, pady=py)
        tk.Button(fr, text="\u25C0", width=4, command=self.timebase_down).grid(
            row=cur_row, column=0, padx=px, pady=py, sticky="e")
        tk.Button(fr, text="\u25B6", width=4, command=self.timebase_up).grid(
            row=cur_row, column=2, padx=px, pady=py, sticky="w")
        cur_row += 1

        ttk.Label(fr, text="Position (s)", style="TLabel").grid(row=cur_row, column=0, padx=px, pady=py)
        self.tb_pos_entry = tk.Entry(fr, width=10)
        self.tb_pos_entry.grid(row=cur_row, column=1, padx=px, pady=py)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_timebase_position(self.tb_pos_entry.get())
                  ).grid(row=cur_row, column=2, padx=px, pady=py)
        cur_row += 1

        # --- Trigger Controls ---
        ttk.Label(fr, text="Trigger", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=(px, py))
        cur_row += 1

        ttk.Label(fr, text="Source", style="TLabel").grid(row=cur_row, column=0, padx=px, pady=py)
        self.trig_source_drop = guih.generate_drop_down(fr, ["CHANnel1", "CHANnel2", "CHANnel3", "CHANnel4"])
        self.trig_source_drop[1].set("CHANnel1")
        self.trig_source_drop[0].grid(row=cur_row, column=1, padx=px, pady=py)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_trigger_source(self.trig_source_drop[1].get())
                  ).grid(row=cur_row, column=2, padx=px, pady=py)
        cur_row += 1

        ttk.Label(fr, text="Level (V)", style="TLabel").grid(row=cur_row, column=0, padx=px, pady=py)
        self.trig_level_entry = tk.Entry(fr, width=10)
        self.trig_level_entry.grid(row=cur_row, column=1, padx=px, pady=py)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_trigger_level(self.trig_level_entry.get())
                  ).grid(row=cur_row, column=2, padx=px, pady=py)
        cur_row += 1

        ttk.Label(fr, text="Slope", style="TLabel").grid(row=cur_row, column=0, padx=px, pady=py)
        self.trig_slope_drop = guih.generate_drop_down(fr, ["POSitive", "NEGative", "EITHer"])
        self.trig_slope_drop[1].set("POSitive")
        self.trig_slope_drop[0].grid(row=cur_row, column=1, padx=px, pady=py)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_trigger_slope(self.trig_slope_drop[1].get())
                  ).grid(row=cur_row, column=2, padx=px, pady=py)

    # =========================================================================
    # gui_refresh
    # =========================================================================
    def update_osc(self):
        """Read back current scope state and update info labels."""
        if not self.cc.get_osc_status():
            guih.alert_user("Can't update OSC", "No OSC connection!", "error")
            return

        try:
            # Update channel enable states
            for i in range(self.channel_count):
                ch = i + 1
                disp = self.cc.osc.get_channel_display(ch).strip()
                self.chan_on[i] = (disp == "1")
                if self.chan_on[i]:
                    self.chan_toggle_btns[i].config(text="ON", bg=self.theme_config["success"])
                else:
                    self.chan_toggle_btns[i].config(text="OFF", bg=self.theme_config["error"])
            # Sync timebase index to current scope setting
            current_tb = self.cc.osc.get_timebase_scale()
            self.tb_index = min(range(len(self.tb_steps)),
                                key=lambda i: abs(self.tb_steps[i] - current_tb))
            if self.tb_label:
                self.tb_label.config(text=self._format_timebase(self.tb_steps[self.tb_index]))

            self.prompt.print("OSC state updated")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't update OSC", str(e), "warning")

    def gui_refresh(self, event):
        if event == "auto" and not self.fr_port.status:
            self.fr_port.refresh_ports()
        if self.fr_port.status:
            self.update_osc()

    # =========================================================================
    # Channel Actions
    # =========================================================================
    def toggle_channel(self, channel):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't toggle channel", "No OSC connection!", "error")
            return

        idx = channel - 1
        try:
            if self.chan_on[idx]:
                self.cc.osc.channel_off(channel)
                self.chan_on[idx] = False
                self.chan_toggle_btns[idx].config(text="OFF", bg=self.theme_config["error"])
                self.prompt.print(f"Channel {channel} OFF")
            else:
                self.cc.osc.channel_on(channel)
                self.chan_on[idx] = True
                self.chan_toggle_btns[idx].config(text="ON", bg=self.theme_config["success"])
                self.prompt.print(f"Channel {channel} ON")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't toggle channel", str(e), "error")

    @staticmethod
    def _parse_si(value_str):
        """Parse a numeric string with an optional SI suffix (e.g. '750m' → 0.75)."""
        suffixes = {"n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6}
        s = value_str.strip()
        if s and s[-1] in suffixes:
            return float(s[:-1]) * suffixes[s[-1]]
        return float(s)

    def set_channel_scale(self, channel, value_str):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set scale", "No OSC connection!", "error")
            return
        try:
            scale = self._parse_si(value_str)
            self.cc.osc.set_scale(channel, scale)
            self.prompt.print(f"CH{channel} scale set to {scale} V/div")
        except ValueError:
            guih.alert_user("Invalid Input", "Scale must be a number (e.g. 0.5 or 750m)", "error")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set scale", str(e), "error")

    def set_channel_coupling(self, channel, coupling):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set coupling", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.set_coupling(channel, coupling)
            self.prompt.print(f"CH{channel} coupling set to {coupling}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set coupling", str(e), "error")

    def set_channel_offset(self, channel, value_str):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set offset", "No OSC connection!", "error")
            return
        try:
            offset = float(value_str)
            self.cc.osc.set_offset(channel, offset)
            self.prompt.print(f"CH{channel} offset set to {offset} V")
        except ValueError:
            guih.alert_user("Invalid Input", "Offset must be a number", "error")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set offset", str(e), "error")

    # =========================================================================
    # Acquisition Actions
    # =========================================================================
    def set_acq_type(self, acq_type):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set acq type", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.set_acq_type(acq_type)
            self.prompt.print(f"Acquisition type: {acq_type}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set acquisition type", str(e), "error")

    def set_acq_count(self, count_str):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set acq count", "No OSC connection!", "error")
            return
        try:
            count = int(count_str)
            if not (1 <= count <= 65536):
                guih.alert_user("Invalid Input", "Count must be between 1 and 65536", "error")
                return
            self.cc.osc.set_acq_count(count)
            self.prompt.print(f"Acquisition count: {count}")
        except ValueError:
            guih.alert_user("Invalid Input", "Count must be an integer", "error")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set acquisition count", str(e), "error")

    def acq_run(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't run", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.run()
            self.prompt.print("Acquisition: RUN")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't run", str(e), "error")

    def acq_stop(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't stop", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.stop()
            self.prompt.print("Acquisition: STOP")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't stop", str(e), "error")

    def acq_single(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't single", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.single()
            self.prompt.print("Acquisition: SINGLE")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't single", str(e), "error")

    # =========================================================================
    # Timebase Actions
    # =========================================================================
    @staticmethod
    def _format_timebase(val):
        """Format a timebase value into a human-readable string."""
        if val < 1e-6:
            return f"{val * 1e9:.0f} ns/div"
        elif val < 1e-3:
            return f"{val * 1e6:.0f} us/div"
        elif val < 1.0:
            return f"{val * 1e3:.0f} ms/div"
        else:
            return f"{val:.0f} s/div"

    def _apply_timebase(self):
        """Send current tb_index value to scope and update the label."""
        scale = self.tb_steps[self.tb_index]
        self.cc.osc.set_timebase_scale(scale)
        if self.tb_label:
            self.tb_label.config(text=self._format_timebase(scale))
        self.prompt.print(f"Timebase: {self._format_timebase(scale)}")

    def timebase_up(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set timebase", "No OSC connection!", "error")
            return
        if self.tb_index >= len(self.tb_steps) - 1:
            return
        self.tb_index += 1
        try:
            self._apply_timebase()
        except COMMUNICATION_ERRORS as e:
            self.tb_index -= 1
            guih.alert_user("Can't set timebase scale", str(e), "error")

    def timebase_down(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set timebase", "No OSC connection!", "error")
            return
        if self.tb_index <= 0:
            return
        self.tb_index -= 1
        try:
            self._apply_timebase()
        except COMMUNICATION_ERRORS as e:
            self.tb_index += 1
            guih.alert_user("Can't set timebase scale", str(e), "error")

    def set_timebase_position(self, value_str):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set position", "No OSC connection!", "error")
            return
        try:
            position = float(value_str)
            self.cc.osc.set_timebase_position(position)
            self.prompt.print(f"Timebase position set to {position} s")
        except ValueError:
            guih.alert_user("Invalid Input", "Position must be a number", "error")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set timebase position", str(e), "error")

    # =========================================================================
    # Trigger Actions
    # =========================================================================
    def set_trigger_source(self, source):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set trigger source", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.set_trigger_source(source)
            self.prompt.print(f"Trigger source set to {source}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set trigger source", str(e), "error")

    def set_trigger_level(self, value_str):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set trigger level", "No OSC connection!", "error")
            return
        try:
            level = float(value_str)
            # derive channel number from current trigger source dropdown
            src = self.trig_source_drop[1].get()
            ch = int(src[-1])  # "CHANnel1" -> 1
            self.cc.osc.set_trigger_level(ch, level)
            self.prompt.print(f"Trigger level set to {level} V on CH{ch}")
        except ValueError:
            guih.alert_user("Invalid Input", "Trigger level must be a number", "error")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set trigger level", str(e), "error")

    def set_trigger_slope(self, slope):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set trigger slope", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.set_trigger_slope(slope)
            self.prompt.print(f"Trigger slope set to {slope}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't set trigger slope", str(e), "error")

    # =========================================================================
    # Save / Recall Actions
    # =========================================================================
    def save_screenshot(self):
        """One-off screenshot onto *this* machine, outside the capture flow.

        Save/Recall Setup below still work on the scope's own filesystem --
        setups are only useful there -- but an image is wanted on the host,
        so this writes into the capture run folder.
        """
        if not self.cc.get_osc_status():
            guih.alert_user("Can't save screenshot", "No OSC connection!", "error")
            return
        filename = self.save_filename_entry.get().strip()
        if not filename:
            filename = "screen_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename.lower().endswith(".png"):
            filename += ".png"

        run_dir = self.capture_dir_var.get().strip() or self._default_run_dir()
        try:
            os.makedirs(run_dir, exist_ok=True)
            path = self.cc.osc.screenshot_to_file(
                capture_naming.unique_path(os.path.join(run_dir, filename)))
            self.prompt.print(f"Screenshot saved: {path}")
        except COMMUNICATION_ERRORS + (NotImplementedError, ValueError, OSError) as e:
            guih.alert_user("Can't save screenshot", str(e), "error")

    def save_setup(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't save setup", "No OSC connection!", "error")
            return
        filename = self.save_filename_entry.get().strip()
        if not filename:
            guih.alert_user("Missing filename", "Enter a filename first", "error")
            return
        try:
            self.cc.osc.save_setup(filename)
            self.prompt.print(f"Setup saved: {filename}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't save setup", str(e), "error")

    def recall_setup(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't recall setup", "No OSC connection!", "error")
            return
        filename = self.save_filename_entry.get().strip()
        if not filename:
            guih.alert_user("Missing filename", "Enter a filename first", "error")
            return
        try:
            self.cc.osc.recall_setup(filename)
            self.prompt.print(f"Setup recalled: {filename}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't recall setup", str(e), "error")

    # =========================================================================
    # Autoscale
    # =========================================================================
    def autoscale(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't autoscale", "No OSC connection!", "error")
            return
        try:
            self.cc.osc.autoscale()
            self.prompt.print("Autoscale executed")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't autoscale", str(e), "error")

    # =========================================================================
    # Measurements
    # =========================================================================
    def measure_all(self):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't measure", "No OSC connection!", "error")
            return
        try:
            ch = int(self.meas_ch_drop[1].get())
            results = self.cc.osc.measure_all(ch)
            self.prompt.print(f"--- Measurements CH{ch} ---")
            for key, val in results.items():
                if val is None:
                    self.prompt.print(f"  {key}: N/A")
                else:
                    self.prompt.print(f"  {key}: {val:.6g}")
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't measure", str(e), "error")

    # =========================================================================
    # fr_capture — Save captures to the host filesystem
    # =========================================================================
    def init_fr_capture(self):
        """Build the capture panel.

        Deliberately not rebuilt on connect (unlike the other frames): the run
        folder, template and field values are the tech's working state for a
        whole sweep and must survive a reconnect.
        """
        fr = self.fr_capture
        px = self.theme_config["pad"]["xpad_l"]
        py = self.theme_config["pad"]["xpad_s"]

        for w in fr.winfo_children():
            w.destroy()

        cur_row = 0
        ttk.Label(fr, text="Capture", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=(5, 5))
        cur_row += 1

        # --- run folder ---
        ttk.Label(fr, text="Run folder", style="TLabel").grid(
            row=cur_row, column=0, padx=px, pady=py, sticky="w")
        self.capture_dir_var = tk.StringVar(value=self._default_run_dir())
        tk.Entry(fr, textvariable=self.capture_dir_var, width=26).grid(
            row=cur_row, column=1, padx=px, pady=py, sticky="w")
        tk.Button(fr, text="...", width=3, command=self.browse_run_dir).grid(
            row=cur_row, column=2, padx=px, pady=py, sticky="w")
        cur_row += 1

        # --- filename template ---
        lbl_template = ttk.Label(fr, text="Template", style="TLabel")
        lbl_template.grid(row=cur_row, column=0, padx=px, pady=py, sticky="w")
        guic.Tooltip(lbl_template,
                     "Filename template for each capture.\n\n" + capture_naming.TOKEN_HELP)
        self.capture_template_var = tk.StringVar(value=self._configured_template())
        tk.Entry(fr, textvariable=self.capture_template_var, width=26).grid(
            row=cur_row, column=1, columnspan=2, padx=px, pady=py, sticky="w")
        cur_row += 1

        # --- user fields (become both filename tokens and CSV columns) ---
        lbl_fields = ttk.Label(fr, text="Fields", style="TLabel")
        lbl_fields.grid(row=cur_row, column=0, padx=px, pady=py, sticky="nw")
        guic.Tooltip(lbl_fields,
                     "Name/value pairs describing this capture's conditions.\n"
                     "Each name is usable as a {token} in the template and is\n"
                     "written as a column in the run CSV, so the filename and\n"
                     "the data row always agree.\n\n"
                     "Retype just the value that changed between captures.")
        self.fr_fields = tk.Frame(fr, bg=self.theme_config["light_4"])
        self.fr_fields.grid(row=cur_row, column=1, columnspan=2, padx=px, pady=py, sticky="w")
        self.capture_fields = []
        cur_row += 1

        tk.Button(fr, text="+ Field", width=8, command=self.add_capture_field).grid(
            row=cur_row, column=1, padx=px, pady=py, sticky="w")
        cur_row += 1

        # --- what gets written ---
        self.var_save_image = tk.IntVar(value=1)
        ttk.Checkbutton(fr, text="Screenshot (PNG)", variable=self.var_save_image,
                        onvalue=1, offvalue=0, command=self._refresh_capture_preview
                        ).grid(row=cur_row, column=0, columnspan=2, padx=px, sticky="w")
        cur_row += 1

        self.var_save_meas = tk.IntVar(value=1)
        ttk.Checkbutton(fr, text="Measurements (CSV row)", variable=self.var_save_meas,
                        onvalue=1, offvalue=0).grid(
            row=cur_row, column=0, columnspan=2, padx=px, sticky="w")
        cur_row += 1

        # --- preview + action ---
        self.capture_preview = tk.Label(fr, text="", anchor="w", justify="left",
                                        wraplength=240, relief="sunken", width=34)
        self.capture_preview.grid(row=cur_row, column=0, columnspan=3,
                                  padx=px, pady=(py, 3), sticky="w")
        cur_row += 1

        self.btn_capture = tk.Button(fr, text="CAPTURE", width=12, command=self.do_capture)
        self.btn_capture.grid(row=cur_row, column=0, columnspan=2, padx=px, pady=py)
        tk.Button(fr, text="Open Folder", width=11, command=self.open_run_folder).grid(
            row=cur_row, column=2, padx=px, pady=py)

        # Seed the two fields nearly every sweep needs; prefix feeds the
        # default template, the second is the variable being swept.
        self.add_capture_field("prefix", "capture")
        self.add_capture_field("Vin", "")

        self.capture_dir_var.trace_add("write", self._refresh_capture_preview)
        self.capture_template_var.trace_add("write", self._refresh_capture_preview)
        self._refresh_capture_preview()

    def _configured_template(self):
        """Starting template from master.ini [OSC], with a safe fallback."""
        config_svc = getattr(self.cc, "config_svc", None)
        if config_svc is None:
            return capture_naming.DEFAULT_TEMPLATE
        return config_svc.get_osc_capture_template()

    def _default_run_dir(self):
        """A dated run folder under the configured capture directory."""
        config_svc = getattr(self.cc, "config_svc", None)
        subdir = config_svc.get_osc_capture_dir() if config_svc else "osc_data"
        root = path_helper.get_data_dir(subdir, create=False)
        return os.path.join(root, datetime.now().strftime("%Y-%m-%d") + "_run")

    def add_capture_field(self, name="", value=""):
        """Append one name/value row to the fields table."""
        row = len(self.capture_fields)
        name_var = tk.StringVar(value=name)
        value_var = tk.StringVar(value=value)

        name_entry = tk.Entry(self.fr_fields, textvariable=name_var, width=10)
        value_entry = tk.Entry(self.fr_fields, textvariable=value_var, width=12)
        name_entry.grid(row=row, column=0, padx=2, pady=1)
        value_entry.grid(row=row, column=1, padx=2, pady=1)

        entry = {"name": name_var, "value": value_var,
                 "widgets": [name_entry, value_entry]}
        remove_btn = tk.Button(self.fr_fields, text="x", width=2,
                               command=lambda e=entry: self.remove_capture_field(e))
        remove_btn.grid(row=row, column=2, padx=2, pady=1)
        entry["widgets"].append(remove_btn)

        self.capture_fields.append(entry)
        name_var.trace_add("write", self._refresh_capture_preview)
        value_var.trace_add("write", self._refresh_capture_preview)
        self._refresh_capture_preview()

    def remove_capture_field(self, entry):
        """Drop a field row and re-pack the ones below it."""
        for widget in entry["widgets"]:
            widget.destroy()
        self.capture_fields.remove(entry)
        for row, remaining in enumerate(self.capture_fields):
            for column, widget in enumerate(remaining["widgets"]):
                widget.grid(row=row, column=column, padx=2, pady=1)
        self._refresh_capture_preview()

    def _collect_fields(self):
        """Fields as a {name: value} dict, skipping unnamed rows."""
        fields = {}
        for entry in self.capture_fields:
            name = entry["name"].get().strip()
            if name:
                fields[name] = entry["value"].get().strip()
        return fields

    def _capture_model(self):
        """Model name for the {model} token — the live one if connected."""
        if self.cc.get_osc_status() and self.cc.osc is not None:
            return self.cc.osc.model
        return self.ate_drop[1].get()

    def _refresh_capture_preview(self, *_):
        """Show the name the next capture would get, or why it can't be built."""
        try:
            name = self.cc.osc_service.preview_capture_name(
                self.capture_template_var.get(),
                self._collect_fields(),
                self.capture_dir_var.get().strip(),
                model=self._capture_model())
        except capture_naming.TemplateError as e:
            self.capture_preview.config(text=f"Template error: {e}",
                                        fg=self.theme_config["error"])
            return

        suffix = ".png" if self.var_save_image.get() else ""
        self.capture_preview.config(text=f"Next: {name}{suffix}",
                                    fg=self.theme_config["fg_light"])

    def browse_run_dir(self):
        chosen = filedialog.askdirectory(title="Capture run folder",
                                         initialdir=os.path.dirname(self.capture_dir_var.get()))
        if chosen:
            self.capture_dir_var.set(chosen)

    def open_run_folder(self):
        run_dir = self.capture_dir_var.get().strip()
        if not os.path.isdir(run_dir):
            guih.alert_user("No such folder", f"{run_dir} does not exist yet", "warning")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(run_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", run_dir])
            else:
                subprocess.Popen(["xdg-open", run_dir])
        except OSError as e:
            guih.alert_user("Can't open folder", str(e), "error")

    def do_capture(self):
        """Validate on the GUI thread, then do the instrument I/O off it."""
        if not self.cc.get_osc_status():
            guih.alert_user("Can't capture", "No OSC connection!", "error")
            return

        fields = self._collect_fields()
        for name in fields:
            if not capture_naming.is_valid_field_name(name):
                guih.alert_user("Invalid field name",
                                f"'{name}' can't be a template token. Use letters, "
                                f"digits and underscores, starting with a letter.",
                                "error")
                return

        if not self.var_save_image.get() and not self.var_save_meas.get():
            guih.alert_user("Nothing to capture",
                            "Enable the screenshot, the measurements, or both.",
                            "warning")
            return

        run_dir = self.capture_dir_var.get().strip()
        if not run_dir:
            guih.alert_user("Missing run folder", "Choose a run folder first", "error")
            return

        self.btn_capture.config(state="disabled")
        self.prompt.print("Capturing...")
        threading.Thread(
            target=self._capture_worker,
            args=(run_dir, self.capture_template_var.get(), fields,
                  bool(self.var_save_image.get()), bool(self.var_save_meas.get())),
            daemon=True).start()

    def _capture_worker(self, run_dir, template, fields, save_image, save_meas):
        """Runs off the GUI thread; a capture is dozens of round trips.

        Tkinter drops exceptions raised in background threads, so anything
        unexpected is caught here and reported through the prompt rather than
        disappearing with a traceback on stderr.
        """
        try:
            result = self.cc.osc_service.capture(
                run_dir, template, fields,
                save_image=save_image, save_measurements=save_meas)
        except Exception as e:
            logger.exception("Unhandled error during OSC capture")
            self.after(0, lambda err=e: self._capture_failed(str(err)))
            return
        self.after(0, lambda: self._capture_done(result))

    def _capture_failed(self, message):
        self.btn_capture.config(state="normal")
        self.prompt.print(f"Capture failed: {message}", "error")
        guih.alert_user("Capture failed", message, "error")

    def _capture_done(self, result):
        self.btn_capture.config(state="normal")

        for warning in result.warnings:
            self.prompt.print(f"Warning: {warning}", "warning")

        if not result.success:
            self._capture_failed(result.error)
            return

        self.prompt.print(f"Capture {result.index}: {result.name}")
        if result.image_path:
            self.prompt.print(f"  image: {result.image_path}")
        if result.csv_path:
            self.prompt.print(f"  row appended to {result.csv_path}")
        self._refresh_capture_preview()

    # =========================================================================
    # Connection (port_init / port_close)
    # =========================================================================
    def port_init(self):
        self.prompt.print("Connect to PyVISA resource!")
        port = self.fr_port.get_port()
        model_name = self.ate_drop[1].get()
        result = self.cc.osc_service.connect(port, model_name)

        if not result.success:
            self.prompt.print(result.error, "error")
            guih.alert_user("Can't connect to OSC", result.error, "warning")
            self.fr_port.set_status(False)
            return False

        self.channel_count = self.cc.osc.channel_count
        self.chan_on = [False] * self.channel_count
        self.init_fr_info()
        self.init_fr_channel()
        self.init_fr_tb_trig()
        self.init_fr_control()

        self.prompt.print(f"Connected to OSC with id: {result.device_id}")
        self.labelIDValue.config(text=result.device_id)
        self.labelTimeConnectedValue.config(text=result.timestamp)
        self.fr_port.status = True
        self.fr_port.set_status(True)
        self.gui_refresh("connect")
        self._refresh_capture_preview()

        if result.error:
            self.prompt.print(f"Warning: {result.error}", "warning")
        return True

    def port_close(self):
        self.prompt.print("Closing OSC resource!")
        result = self.cc.osc_service.disconnect()
        if not result.success:
            guih.alert_user("Can't disconnect OSC", result.error, "warning")
        self.fr_port.set_status(False)
