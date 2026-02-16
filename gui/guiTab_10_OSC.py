"""Oscilloscope control tab."""

# import needed GUI packages
import tkinter as tk
from tkinter import ttk

# import needed packages
from datetime import datetime

# import user defined modules
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic



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
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])

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
        self.fr_info.grid(row=0, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.fr_port.grid(row=0, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="N")
        self.fr_control.grid(row=0, column=2, rowspan=3, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.fr_channel.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NW")
        self.prompt.grid(row=2, column=0, columnspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)


    def initTabContent(self):
        print("Initializing tab 10 (OSC) content")
        self.init_fr_info()
        self.init_fr_channel()
        self.init_fr_control()

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
            print(f"Restored previous OSC model: {previous_model}")

        # Device ID
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=40, relief='sunken', anchor='w')

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
    # fr_control — Acquisition, Timebase, Trigger, Save/Recall, Measure
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

        # --- Timebase Controls ---
        ttk.Label(fr, text="Timebase", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=(10, 5))
        cur_row += 1

        self.tb_label = ttk.Label(fr, text=self._format_timebase(self.tb_steps[self.tb_index]),
                                   style="TLabel", width=12, anchor="center")
        self.tb_label.grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="\u25C0", width=4, command=self.timebase_down).grid(
            row=cur_row, column=0, padx=5, pady=3, sticky="e")
        tk.Button(fr, text="\u25B6", width=4, command=self.timebase_up).grid(
            row=cur_row, column=2, padx=5, pady=3, sticky="w")
        cur_row += 1

        ttk.Label(fr, text="Position (s)", style="TLabel").grid(row=cur_row, column=0, padx=5, pady=3)
        self.tb_pos_entry = tk.Entry(fr, width=10)
        self.tb_pos_entry.grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_timebase_position(self.tb_pos_entry.get())
                  ).grid(row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        # --- Trigger Controls ---
        ttk.Label(fr, text="Trigger", style="TPinkLabel.TLabel").grid(
            row=cur_row, column=0, columnspan=3, pady=(10, 5))
        cur_row += 1

        ttk.Label(fr, text="Source", style="TLabel").grid(row=cur_row, column=0, padx=5, pady=3)
        self.trig_source_drop = guih.generate_drop_down(fr, ["CHANnel1", "CHANnel2", "CHANnel3", "CHANnel4"])
        self.trig_source_drop[1].set("CHANnel1")
        self.trig_source_drop[0].grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_trigger_source(self.trig_source_drop[1].get())
                  ).grid(row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        ttk.Label(fr, text="Level (V)", style="TLabel").grid(row=cur_row, column=0, padx=5, pady=3)
        self.trig_level_entry = tk.Entry(fr, width=10)
        self.trig_level_entry.grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_trigger_level(self.trig_level_entry.get())
                  ).grid(row=cur_row, column=2, padx=5, pady=3)
        cur_row += 1

        ttk.Label(fr, text="Slope", style="TLabel").grid(row=cur_row, column=0, padx=5, pady=3)
        self.trig_slope_drop = guih.generate_drop_down(fr, ["POSitive", "NEGative", "EITHer"])
        self.trig_slope_drop[1].set("POSitive")
        self.trig_slope_drop[0].grid(row=cur_row, column=1, padx=5, pady=3)
        tk.Button(fr, text="Set", width=6,
                  command=lambda: self.set_trigger_slope(self.trig_slope_drop[1].get())
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
        if event == "auto":
            self.fr_port.refresh_ports()

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

    def set_channel_scale(self, channel, value_str):
        if not self.cc.get_osc_status():
            guih.alert_user("Can't set scale", "No OSC connection!", "error")
            return
        try:
            scale = float(value_str)
            self.cc.osc.set_scale(channel, scale)
            self.prompt.print(f"CH{channel} scale set to {scale} V/div")
        except ValueError:
            guih.alert_user("Invalid Input", "Scale must be a number", "error")
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
        if not self.cc.get_osc_status():
            guih.alert_user("Can't save screenshot", "No OSC connection!", "error")
            return
        filename = self.save_filename_entry.get().strip()
        if not filename:
            filename = "screen_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            self.cc.osc.save_image(filename)
            self.prompt.print(f"Screenshot saved: {filename}")
        except COMMUNICATION_ERRORS as e:
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
        self.init_fr_info()
        self.init_fr_channel()
        self.init_fr_control()

        self.prompt.print(f"Connected to OSC with id: {result.device_id}")
        self.labelIDValue.config(text=result.device_id)
        self.labelTimeConnectedValue.config(text=result.timestamp)
        self.fr_port.set_status(True)
        self.update_osc()

        if result.error:
            self.prompt.print(f"Warning: {result.error}", "warning")
        return True

    def port_close(self):
        self.prompt.print("Closing OSC resource!")
        result = self.cc.osc_service.disconnect()
        if not result.success:
            guih.alert_user("Can't disconnect OSC", result.error, "warning")
        self.fr_port.set_status(False)
