"""Automated test equipment sequencing tab."""

# import needed GUI packages
import logging
import os
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb

# import user GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic

# import user created modules
from common import plotter
from common.script_runner import ScriptRunner
from analysis import stats_analysis

# import needed packages
from datetime import datetime
import time
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS
from common import logger
import numpy as np

_logger = logging.getLogger(__name__)




class TabATE(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        self.fr_port = None
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_accuracy = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_script = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up serial / PS variables
        self.ate = None

        # Script runner
        self.scripts_dir = os.path.join("data", "scripts")
        self.script_runner = ScriptRunner(self.cc, self._script_log)

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "ATE Output")
        self.prompt.grid(row=10, column=0, columnspan=4, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_info.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_control.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_accuracy.grid(row=3, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_script.grid(row=4, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.prompt.grid(row=3, column=1, columnspan=4, rowspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "Generic_ATE",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3,
                                            status_cmd=lambda: self.ate.status if self.ate else False)
        self.fr_port.initialize_fr()
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=1, column=1, rowspan=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])

    def initTabContent(self):
        _logger.debug("Initializing tab 7 (ATE) content")
        self.create_tab_header("ATE", columnspan=5)
        self.init_fr_info()
        self.init_fr_control()
        self.init_fr_accuracy()
        self.init_fr_script()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Generic ATE Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("all")
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )

        # Load and set previous model if available
        previous_model = self.cc.get_used_model("Generic_ATE")
        if previous_model and previous_model in self.registry:
            self.ate_drop[1].set(previous_model)
            _logger.info(f"Restored previous ATE model: {previous_model}")

        # Add labels for device information
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=40, relief='sunken', anchor='w')

        self.labelTimeConnected = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        # Position the device information labels
        self.ate_drop[0].grid(row=1, column=1, columnspan=1, padx=3, pady=1)
        self.labelID.grid(row=2, column=0, sticky='W', padx=5, pady=1)
        self.labelIDValue.grid(row=2, column=1, sticky='W', padx=5, pady=1)
        self.labelTimeConnected.grid(row=3, column=0, sticky='W', padx=5, pady=1)
        self.labelTimeConnectedValue.grid(row=3, column=1, sticky='W', padx=5, pady=1)

        # Scan IDN button — queries *IDN? on all discovered PyVISA resources
        self.btn_scan_idn = tk.Button(self.fr_info, text='Scan IDN', command=self.scan_idn)
        self.btn_scan_idn.grid(row=4, column=0, columnspan=2, pady=5, padx=5, sticky='W')

    def init_fr_control(self):
        fr_m = self.fr_control

        self.labelInfo = ttk.Label(fr_m, text='ATE Control', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # GENERAL CONTROLS
        self.cmd_label = ttk.Label(fr_m, text="Command", style="TLabel")
        self.cmd_entry = tk.Entry(fr_m, width=15)
        self.cmd_button = tk.Button(fr_m, text="Send",
                                      command=lambda: self.ate_command(self.cmd_entry.get())
                                      )
        self.qry_button = tk.Button(fr_m, text="Query",
                                      command=lambda: self.ate_query(self.cmd_entry.get())
                                      )


        # BENCHMARK CONTROLS
        self.bench_method_drop = guih.generate_drop_down(fr_m, ["read_value", "test_conn"])
        self.bench_store_var = tk.BooleanVar()
        self.bench_store_check = tk.Checkbutton(fr_m, text="Store Values", variable=self.bench_store_var)
        self.benchmark = tk.Button(fr_m, text="Benchmark", command=self.ate_benchmark)

        # place everything on grid
        self.cmd_label.grid(row=1, column=0, padx=10, pady=10)
        self.cmd_entry.grid(row=1, column=1, padx=10, pady=10)
        self.cmd_button.grid(row=1, column=2, padx=10, pady=10)
        self.qry_button.grid(row=1, column=3, padx=10, pady=10)
        self.bench_method_drop[0].grid(row=2, column=0, padx=10, pady=10)
        self.bench_store_check.grid(row=2, column=1, padx=10, pady=10, sticky='w')
        self.benchmark.grid(row=2, column=2, padx=10, pady=10)

    def init_fr_accuracy(self):
        """Initialize the instrument accuracy testing frame"""
        fr_m = self.fr_accuracy

        # Title
        title_label = ttk.Label(fr_m, text='Instrument Accuracy Testing', style="TPinkLabel.TLabel", width=30)
        title_label.grid(row=0, column=0, columnspan=3, pady=5)

        # Info button
        info_button = tk.Button(fr_m, text="ℹ Info",
                                command=self.show_accuracy_info,
                                bg=self.theme_config["light_2"],
                                fg=self.theme_config["fg_dark"],
                                height=1, width=6)
        info_button.grid(row=0, column=3, padx=5, pady=5)

        # Description
        desc_label = ttk.Label(fr_m, text='Sweep PS voltage with DMM', style="TLabel")
        desc_label.grid(row=1, column=0, columnspan=4, pady=2)

        # Sweep configuration
        ttk.Label(fr_m, text="Start Voltage (V):", style="TLabel").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.acc_start_entry = tk.Entry(fr_m, width=10)
        self.acc_start_entry.insert(0, "0.1") # NOTE: starting at 0V causes issues on most power supplies. Start at 100mV instead
        self.acc_start_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(fr_m, text="Stop Voltage (V):", style="TLabel").grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.acc_stop_entry = tk.Entry(fr_m, width=10)
        self.acc_stop_entry.insert(0, "5")
        self.acc_stop_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(fr_m, text="Number of Steps:", style="TLabel").grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.acc_steps_entry = tk.Entry(fr_m, width=10)
        self.acc_steps_entry.insert(0, "11")
        self.acc_steps_entry.grid(row=4, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(fr_m, text="Settling Time (s):", style="TLabel").grid(row=5, column=0, sticky='e', padx=5, pady=5)
        self.acc_settling_entry = tk.Entry(fr_m, width=10)
        self.acc_settling_entry.insert(0, "1.5")
        self.acc_settling_entry.grid(row=5, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(fr_m, text="PS Channel:", style="TLabel").grid(row=6, column=0, sticky='e', padx=5, pady=5)
        self.acc_channel_entry = tk.Entry(fr_m, width=10)
        self.acc_channel_entry.insert(0, "1")
        self.acc_channel_entry.grid(row=6, column=1, sticky='w', padx=5, pady=5)

        # Run button
        self.acc_run_button = tk.Button(fr_m, text="Run Accuracy Test",
                                         command=self.run_accuracy_test,
                                         bg=self.theme_config["success"],
                                         fg=self.theme_config["fg_dark"],
                                         height=2, width=20)
        self.acc_run_button.grid(row=2, column=2, rowspan=3, padx=20, pady=10)

    def init_fr_script(self):
        """Initialize the script runner frame."""
        fr_m = self.fr_script

        title_label = ttk.Label(fr_m, text='Script Runner', style="TPinkLabel.TLabel", width=20)
        title_label.grid(row=0, column=0, columnspan=3, pady=5)

        # Script selection dropdown
        ttk.Label(fr_m, text="Script:", style="TLabel").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        scripts = ScriptRunner.list_scripts(self.scripts_dir)
        self.script_drop = guih.generate_drop_down(fr_m, scripts if scripts else ["(no scripts found)"])
        self.script_drop[0].grid(row=1, column=1, padx=5, pady=5)

        # Refresh button
        self.script_refresh_btn = tk.Button(fr_m, text="Refresh",
                                            command=self._refresh_script_list,
                                            width=8)
        self.script_refresh_btn.grid(row=1, column=2, padx=5, pady=5)

        # Run / Stop buttons
        self.script_run_btn = tk.Button(fr_m, text="Run Script",
                                        command=self._run_script,
                                        bg=self.theme_config["success"],
                                        fg=self.theme_config["fg_dark"],
                                        height=2, width=12)
        self.script_run_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.script_stop_btn = tk.Button(fr_m, text="Stop",
                                         command=self._stop_script,
                                         bg=self.theme_config["error"],
                                         fg=self.theme_config["fg_dark"],
                                         height=2, width=12,
                                         state=tk.DISABLED)
        self.script_stop_btn.grid(row=2, column=2, padx=10, pady=10)

    def _script_log(self, msg):
        """Thread-safe log callback for the script runner."""
        self.after(0, lambda: self.prompt.print(str(msg)))

    def _run_script(self):
        """Run the selected script."""
        selected = self.script_drop[1].get()
        if not selected or selected == "(no scripts found)":
            guih.alert_user("No Script", "Please select a script to run.", "warning")
            return

        script_path = os.path.join(self.scripts_dir, selected)
        started = self.script_runner.run(script_path)
        if started:
            self.script_run_btn.config(state=tk.DISABLED)
            self.script_stop_btn.config(state=tk.NORMAL)
            self._poll_script_done()

    def _stop_script(self):
        """Stop the running script."""
        self.script_runner.stop()

    def _poll_script_done(self):
        """Check if the script thread has finished and re-enable buttons."""
        if self.script_runner.is_running():
            self.after(500, self._poll_script_done)
        else:
            self.script_run_btn.config(state=tk.NORMAL)
            self.script_stop_btn.config(state=tk.DISABLED)

    def _refresh_script_list(self):
        """Rescan scripts directory and update the dropdown."""
        scripts = ScriptRunner.list_scripts(self.scripts_dir)
        menu = self.script_drop[0]["menu"]
        menu.delete(0, "end")
        var = self.script_drop[1]
        if scripts:
            for s in scripts:
                menu.add_command(label=s, command=lambda v=s: var.set(v))
            var.set(scripts[0])
        else:
            menu.add_command(label="(no scripts found)", command=lambda: var.set("(no scripts found)"))
            var.set("(no scripts found)")

    def scan_idn(self):
        """Query *IDN? on all discovered PyVISA resources and print results."""
        import pyvisa
        self.prompt.print("--- Scanning PyVISA resources ---")
        try:
            rm = pyvisa.ResourceManager()
            resources = [r for r in rm.list_resources() if not r.startswith('ASRL')]
        except Exception as e:
            self.prompt.print(f"Could not open ResourceManager: {e}", "error")
            return

        if not resources:
            self.prompt.print("No PyVISA resources found.")
            return

        for addr in resources:
            try:
                inst = rm.open_resource(addr)
                idn = inst.query("*IDN?").strip()
                inst.close()
                self.prompt.print(f"  {addr} -> {idn}")
            except Exception as e:
                self.prompt.print(f"  {addr} -> ERROR: {e}", "warning")

        self.prompt.print(f"Scan complete. {len(resources)} resource(s) found.")

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def show_accuracy_info(self):
        """Display information about power supply accuracy testing"""
        # Create popup window
        info_window = tk.Toplevel(self)
        info_window.title("Power Supply Accuracy Information")
        info_window.geometry("600x500")
        info_window.configure(bg=self.theme_config["bg_light"])

        # Title
        title_label = ttk.Label(info_window,
                                text="Understanding Power Supply Accuracy",
                                style="TPinkLabel.TLabel",
                                font=(self.theme_config["font"]["family"], 14, "bold"))
        title_label.pack(pady=10)

        # Create frame for text with scrollbar
        text_frame = tk.Frame(info_window, bg=self.theme_config["bg_light"])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget
        text_widget = tk.Text(text_frame,
                              wrap=tk.WORD,
                              yscrollcommand=scrollbar.set,
                              bg=self.theme_config["light_4"],
                              fg=self.theme_config["fg_light"],
                              font=(self.theme_config["font"]["family"], 10),
                              padx=10,
                              pady=10)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # Informational text content
        info_text = """Power Supply Accuracy Testing

Overview:
This tool allows you to characterize the accuracy of a power supply by sweeping through voltage setpoints and measuring the actual output with a precision digital multimeter (DMM).

How It Works:
1. The test sweeps the power supply from start voltage to stop voltage in discrete steps
2. At each setpoint, the system waits for the specified settling time
3. The DMM measures the actual output voltage
4. Results are plotted and saved for analysis

Key Parameters:

Start/Stop Voltage:
Define the voltage range to test. Starting at 0V can cause issues on some power supplies, so 0.1V (100mV) is recommended as a minimum.

Number of Steps:
How many voltage points to test between start and stop. More steps provide better characterization but take longer.

Settling Time:
Time to wait at each voltage setpoint before taking a measurement. This allows the power supply output to stabilize and transients to settle. Typical values: 0.5-2 seconds.

PS Channel:
Which power supply channel to test (1 or 2 for dual-channel supplies).

Understanding Results:
- Linear deviation: How well the measured voltage tracks the setpoint
- Accuracy: Absolute difference between setpoint and measured value
- Linearity error: Deviation from ideal 1:1 relationship
- Repeatability: Consistency across multiple runs

"""

        # Insert text and make read-only
        text_widget.insert("1.0", info_text)
        text_widget.config(state=tk.DISABLED)

        # Close button
        close_button = tk.Button(info_window,
                                 text="Close",
                                 command=info_window.destroy,
                                 bg=self.theme_config["light_2"],
                                 fg=self.theme_config["fg_dark"],
                                 height=1,
                                 width=10)
        close_button.pack(pady=10)

    def ate_command(self, command_str):
        if self.ate is not None:
            self.ate.write(command_str)

    def ate_query(self, command_str):
        if self.ate is not None:
            self.prompt.print("Sending command: " + command_str)
            try:
                res = self.ate.query(command_str)
            except COMMUNICATION_ERRORS as e:
                self.prompt.print("Communication error: " + str(e), "error")
                return
            self.prompt.print(f"Got response: {res}")

    def ate_benchmark(self):
        if self.ate is None:
            return
        method_name = self.bench_method_drop[1].get()
        method = self.ate.read_value if method_name == "read_value" else self.ate.test_conn
        store = self.bench_store_var.get()

        self.prompt.print(f"Running benchmark with {method_name} (store={store})...")
        time.sleep(0.2)
        try:
            bench_result = self.ate.benchmark(100, method, store_values=store)
        except COMMUNICATION_ERRORS as e:
            self.prompt.print("Communication error: " + str(e), "error")
            guih.alert_user("Communication error: ", str(e), "error")
            return
        self.prompt.print(bench_result["string"])

        if store and bench_result["values"]:
            self._show_benchmark_values(bench_result)
        else:
            guih.alert_user("Benchmark complete!", bench_result["string"], "info")

    def _show_benchmark_values(self, bench_result):
        win = tk.Toplevel(self)
        win.title("Benchmark Values")
        win.geometry("420x500")

        ttk.Label(win, text=bench_result["string"], style="TLabel", justify="left").pack(pady=10, padx=10, anchor='w')

        frame = tk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(frame, yscrollcommand=scrollbar.set, width=50)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)

        for i, val in enumerate(bench_result["values"]):
            text.insert(tk.END, f"{i + 1}: {val}\n")
        text.config(state=tk.DISABLED)

        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def run_accuracy_test(self):
        """Run instrument accuracy test by sweeping PS and measuring with DMM"""
        # Check that PS and DMM are connected
        if not self.cc.get_ps_status():
            guih.alert_user("PS Not Connected", "Please connect a power supply before running accuracy test", "error")
            return

        if not self.cc.get_dmm_status():
            guih.alert_user("DMM Not Connected", "Please connect a DMM before running accuracy test", "error")
            return

        # Parse configuration from GUI
        try:
            start_voltage = float(self.acc_start_entry.get())
            stop_voltage = float(self.acc_stop_entry.get())
            num_steps = int(self.acc_steps_entry.get())
            settling_time = float(self.acc_settling_entry.get())
            ps_channel = int(self.acc_channel_entry.get())
        except ValueError as e:
            guih.alert_user("Invalid Input", f"Please enter valid numeric values: {str(e)}", "error")
            return

        # Validate inputs
        if num_steps < 2:
            guih.alert_user("Invalid Input", "Number of steps must be at least 2", "error")
            return

        if start_voltage == stop_voltage:
            guih.alert_user("Invalid Input", "Start and stop voltages cannot be the same", "error")
            return

        self.prompt.print("Starting instrument accuracy test...")
        self.prompt.print(f"Sweep: {start_voltage}V to {stop_voltage}V in {num_steps} steps")

        # Create stimulus configuration using logger's StimulusConfig
        stimulus_config = logger.StimulusConfig(
            enabled=True,
            stimulus_type=logger.StimulusType.PS_VOLTAGE,
            sweep_mode=logger.SweepMode.LINEAR,
            step_mode=logger.StepMode.NUM_STEPS,
            start_value=start_voltage,
            stop_value=stop_voltage,
            step_value=num_steps,
            settling_time=settling_time,
            channel=ps_channel
        )

        # Validate configuration
        valid, error_msg = stimulus_config.validate()
        if not valid:
            guih.alert_user("Configuration Error", error_msg, "error")
            return

        # Create stimulus generator
        stimulus_gen = logger.StimulusGenerator(stimulus_config)

        # Storage for measurements
        set_voltages = []
        measured_voltages = []
        errors = []

        # Perform sweep
        try:
            self.cc.ps_service.output_on(ps_channel)
            for step_num, voltage in enumerate(stimulus_gen, 1):
                # Set PS voltage
                self.cc.ps_service.set_voltage(ps_channel, voltage)

                # Wait for settling
                time.sleep(settling_time)

                # Read DMM measurement
                dmm_reading, _ = self.cc.dmm_service.read_value()
                if dmm_reading is None:
                    self.prompt.print("DMM read error, aborting test", "error")
                    break

                # Calculate error
                error = dmm_reading - voltage

                # Store data
                set_voltages.append(voltage)
                measured_voltages.append(dmm_reading)
                errors.append(error)

                # Update progress
                self.prompt.print(f"Step {step_num}/{num_steps}: Set={voltage:.4f}V, Measured={dmm_reading:.4f}V, Error={error:.4f}V")

            # end test
            self.cc.ps_service.output_off(ps_channel)

            # Calculate statistics
            set_array = np.array(set_voltages)
            measured_array = np.array(measured_voltages)

            stats = stats_analysis.compute_accuracy_stats(set_array, measured_array)
            report = stats_analysis.format_accuracy_report(
                stats, set_voltages, measured_voltages,
                config={
                    "start_voltage": start_voltage,
                    "stop_voltage": stop_voltage,
                    "num_steps": num_steps,
                    "settling_time": settling_time,
                    "ps_channel": ps_channel,
                })

            # Display results
            self.prompt.print(report, "normal")
            self.prompt.print("Accuracy test complete!")
            self.prompt.print(f"Mean Error: {stats['mean_error']:.6f}V ({stats['mean_error_pct']:.3f}% FS), Max Error: {stats['max_error']:.6f}V ({stats['max_error_pct']:.3f}% FS)")

            # Compute and display calibration coefficients
            cal = stats_analysis.fit_cal_coeffs(set_array, measured_array)
            self.prompt.print(
                f"\n--- Calibration Coefficients (CH{ps_channel}) ---\n"
                f"  fit: measured = {cal['fit_slope']:.6f}*set + {cal['fit_intercept']:.6f}  (R={cal['r']:.6f})\n"
                f"  v_slope  = {cal['v_slope']}\n"
                f"  v_offset = {cal['v_offset']}\n"
                f"  Paste into EEequipment/SPD3303X/config.ini under [CH{ps_channel}]"
            )

            # Plot results with residuals
            plotter.plot_accuracy_with_residuals(
                set_array,
                measured_array,
                stats["errors"],
                x_label="Set Voltage (V)",
                y_label="Measured Voltage (V)",
                title="Power Supply Accuracy Analysis")


        except Exception as e:
            guih.alert_user("Test Error", f"An error occurred during testing: {str(e)}", "error")
            self.prompt.print(f"Error during accuracy test: {str(e)}", "error")

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PYVISA resource!")
        ate_temp = self.registry[self.ate_drop[1].get()]
        self.ate = ate_temp(self.fr_port.get_port())
        time.sleep(1)

        try:
            import usb
            self.id = self.ate.test_conn()
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't connect to VISA", e, "warning")
            self.fr_port.set_status(False)
            return False

        if self.id:  # CONNECTION SUCCESS
            self.prompt.print(f"Connected to ATE with id: {self.id}")
            self.labelIDValue.config(text=self.id)
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.fr_port.set_status(True)

            # Save the selected model for next time
            selected_model = self.ate_drop[1].get()
            self.cc.set_used_model(selected_model, "Generic_ATE")

            # gui refresh
            self.gui_refresh("call")
            return True
        else:  # BAD ID received
            self.ate = None
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at does not respond or is not correct config")
            return False

    def port_close(self):
        self.prompt.print(f"Closing PYVISA resource!")
        self.ate.disconnect()
        self.fr_port.set_status(False)
        self.ate = None
        self.prompt.print(f"Connection is closed.")





