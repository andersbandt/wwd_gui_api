"""
@file     guiTab_7_ATE.py
@author   Anders Bandt
@date     November 2024
@brief    control devices to assist in ATE control
"""

# import needed GUI packages
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb

# import uGUI modules
from gui import gui_helper as guih
from gui import gui_class as guic

# import needed packages
from datetime import datetime
import time
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS
from common import logger
import numpy as np



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

        # set up serial / PS variables
        self.ate = None

        # set up prompt
        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                   "ATE Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_info.grid(row=0, column=0, padx=15, pady=self.theme_config["pad"]["ypad_s"])
        self.fr_control.grid(row=1, column=0, padx=15, pady=self.theme_config["pad"]["ypad_s"])
        self.fr_accuracy.grid(row=2, column=0, columnspan=2, padx=15, pady=self.theme_config["pad"]["ypad_s"])
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=self.theme_config["pad"]["ypad_s"])

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "Generic_ATE",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3)
        self.fr_port.initialize_fr()
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, rowspan=2, padx=15, pady=self.theme_config["pad"]["ypad_s"])

    def initTabContent(self):
        print("Initializing tab 7 (ATE) content")
        self.init_fr_info()
        self.init_fr_control()
        self.init_fr_accuracy()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Generic ATE Info', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("all")
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )

        # Add labels for device information
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=40, relief='sunken', anchor='w')

        self.labelTimeConnected = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        self.labelVers = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        # Position the device information labels
        self.ate_drop[0].grid(row=1, column=1, columnspan=1, padx=3, pady=10)
        self.labelID.grid(row=2, column=0, sticky='W', padx=5, pady=2)
        self.labelIDValue.grid(row=2, column=1, sticky='W', padx=5, pady=2)
        self.labelTimeConnected.grid(row=3, column=0, sticky='W', padx=5, pady=2)
        self.labelTimeConnectedValue.grid(row=3, column=1, sticky='W', padx=5, pady=2)

    def init_fr_control(self):
        fr_m = self.fr_control

        self.labelInfo = ttk.Label(fr_m, text='ATE Control', style="TPinkLabel.TLabel", width=15)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # GENERAL CONTROLS
        self.cmd_label = ttk.Label(fr_m, text="Command", style="TLabel")
        self.cmd_entry = tk.Entry(fr_m)
        self.cmd_button = tk.Button(fr_m, text="Send",
                                      command=lambda: self.ate_command(self.cmd_entry.get())
                                      )
        self.qry_button = tk.Button(fr_m, text="Query",
                                      command=lambda: self.ate_query(self.cmd_entry.get())
                                      )


        # MISC CONTROL
        self.benchmark = tk.Button(fr_m, text="Benchmark",
                                      command=lambda: self.ate_benchmark()
                                      )

        # place everything on grid
        self.cmd_label.grid(row=1, column=0, padx=10, pady=10)
        self.cmd_entry.grid(row=1, column=1, padx=10, pady=10)
        self.cmd_button.grid(row=1, column=2, padx=10, pady=10)
        self.qry_button.grid(row=1, column=3, padx=10, pady=10)
        self.benchmark.grid(row=2, column=0, padx=10, pady=10)

    def init_fr_accuracy(self):
        """Initialize the instrument accuracy testing frame"""
        fr_m = self.fr_accuracy

        # Title
        title_label = ttk.Label(fr_m, text='Instrument Accuracy Testing', style="TPinkLabel.TLabel", width=30)
        title_label.grid(row=0, column=0, columnspan=4, pady=5)

        # Description
        desc_label = ttk.Label(fr_m, text='Sweep PS voltage and measure with DMM to calculate accuracy statistics', style="TLabel")
        desc_label.grid(row=1, column=0, columnspan=4, pady=2)

        # Sweep configuration
        ttk.Label(fr_m, text="Start Voltage (V):", style="TLabel").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.acc_start_entry = tk.Entry(fr_m, width=10)
        self.acc_start_entry.insert(0, "0")
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
        self.acc_settling_entry.insert(0, "0.5")
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

        # Results display
        ttk.Label(fr_m, text="Results:", style="TLabel").grid(row=7, column=0, sticky='nw', padx=5, pady=5)
        self.acc_results_text = tk.Text(fr_m, height=10, width=80, wrap=tk.WORD)
        self.acc_results_text.grid(row=8, column=0, columnspan=4, padx=10, pady=5)

        # Scrollbar for results
        scrollbar = tk.Scrollbar(fr_m, command=self.acc_results_text.yview)
        scrollbar.grid(row=8, column=4, sticky='ns', pady=5)
        self.acc_results_text.config(yscrollcommand=scrollbar.set)

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def ate_command(self, command_str):
        if self.ate is not None:
            self.ate.write(command_str)

    def ate_query(self, command_str):
        if self.ate is not None:
            self.prompt.print("Sending command: " + command_str)
            res = self.ate.query(command_str)
            self.prompt.print(f"Got response: {res}")

    def ate_benchmark(self):
        if self.ate is not None:
            self.prompt.print("Running benchmark with the `test_conn` function")
            time.sleep(0.2)
            # bench_result = self.ate.benchmark(100, self.ate.test_conn)
            bench_result = self.ate.benchmark(100, self.ate.read_value)
            self.prompt.print(bench_result["string"])
            guih.alert_user("Benchmark complete!", bench_result["string"], "info")

    def run_accuracy_test(self):
        """Run instrument accuracy test by sweeping PS and measuring with DMM"""
        # Check that PS and DMM are connected
        if self.cc.ps is None:
            guih.alert_user("PS Not Connected", "Please connect a power supply before running accuracy test", "error")
            return

        if self.cc.dmm is None:
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

        # Clear previous results
        self.acc_results_text.delete("1.0", tk.END)
        self.acc_results_text.insert(tk.END, "Running accuracy test...\n\n")
        self.acc_results_text.update()

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
            num_steps=num_steps,
            settling_time=settling_time,
            ps_channel=ps_channel
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
            for step_num, voltage in enumerate(stimulus_gen, 1):
                # Set PS voltage
                self.cc.ps.set_voltage(ps_channel, voltage)

                # Wait for settling
                time.sleep(settling_time)

                # Read DMM measurement
                dmm_reading = self.cc.dmm.read_value()

                # Calculate error
                error = dmm_reading - voltage

                # Store data
                set_voltages.append(voltage)
                measured_voltages.append(dmm_reading)
                errors.append(error)

                # Update progress
                self.prompt.print(f"Step {step_num}/{num_steps}: Set={voltage:.4f}V, Measured={dmm_reading:.4f}V, Error={error:.4f}V")

            # Calculate statistics
            errors_array = np.array(errors)
            set_array = np.array(set_voltages)
            measured_array = np.array(measured_voltages)

            mean_error = np.mean(errors_array)
            std_error = np.std(errors_array)
            max_error = np.max(np.abs(errors_array))
            rms_error = np.sqrt(np.mean(errors_array**2))

            # Calculate percent errors
            # Avoid division by zero by using full scale (stop - start)
            full_scale = abs(stop_voltage - start_voltage)
            if full_scale > 0:
                mean_error_pct = (abs(mean_error) / full_scale) * 100
                max_error_pct = (max_error / full_scale) * 100
            else:
                mean_error_pct = 0
                max_error_pct = 0

            # Format results
            results = []
            results.append("=" * 80)
            results.append("INSTRUMENT ACCURACY TEST RESULTS")
            results.append("=" * 80)
            results.append(f"\nTest Configuration:")
            results.append(f"  Voltage Range: {start_voltage}V to {stop_voltage}V")
            results.append(f"  Number of Steps: {num_steps}")
            results.append(f"  Settling Time: {settling_time}s")
            results.append(f"  PS Channel: {ps_channel}")
            results.append(f"\nStatistics:")
            results.append(f"  Mean Error:          {mean_error:>10.6f} V  ({mean_error_pct:>6.3f}% of full scale)")
            results.append(f"  Std Deviation:       {std_error:>10.6f} V")
            results.append(f"  RMS Error:           {rms_error:>10.6f} V")
            results.append(f"  Max Absolute Error:  {max_error:>10.6f} V  ({max_error_pct:>6.3f}% of full scale)")
            results.append(f"\nDetailed Measurements:")
            results.append(f"{'Step':<6} {'Set (V)':<12} {'Measured (V)':<12} {'Error (V)':<12} {'Error (%FS)':<12}")
            results.append("-" * 80)

            for i in range(len(set_voltages)):
                error_pct = (abs(errors[i]) / full_scale) * 100 if full_scale > 0 else 0
                results.append(f"{i+1:<6} {set_voltages[i]:<12.6f} {measured_voltages[i]:<12.6f} {errors[i]:<12.6f} {error_pct:<12.3f}")

            results.append("=" * 80)

            # Display results
            self.acc_results_text.delete("1.0", tk.END)
            self.acc_results_text.insert(tk.END, "\n".join(results))

            self.prompt.print("Accuracy test complete!")
            self.prompt.print(f"Mean Error: {mean_error:.6f}V ({mean_error_pct:.3f}% FS), Max Error: {max_error:.6f}V ({max_error_pct:.3f}% FS)")

        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Communication Error", f"Error communicating with equipment: {str(e)}", "error")
            self.prompt.print(f"Error during accuracy test: {str(e)}", "error")
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
        self.cc.set_ps(None)
        self.prompt.print(f"Connection is closed.")





