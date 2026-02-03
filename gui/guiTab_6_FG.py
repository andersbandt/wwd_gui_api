"""
@file     guiTab_9_FG.py
@author   Anders Bandt
@date     January 2025
@brief    control function generator test equipment
"""

# import needed GUI packages
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as tkmb

# import needed packages
import time
from datetime import datetime

# import user defined modules
from common import path_helper
from EEequipment import equipment_manager
from EEequipment.equipment_manager import COMMUNICATION_ERRORS

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle


class TabFG(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config, autoconnect):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath
        self.grid(row=0, column=0)

        self.fr_port = None
        self.fr_info = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_control = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up function generator variables
        self.id = None
        self.output_on = False
        self.frequency = "?"
        self.waveform = "?"
        self.duty_cycle = "?"
        self.amplitude = "?"

        # set up recording / data information
        self.recName = False
        self.data_dir = path_helper.get_full_data_path(subdir="fg_data")

        # set up prompt
        self.prompt = guic.Prompt(self,
                                  self.theme_config,
                                  "FG Console Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        # TODO: need to add dynamic padding here (based on theme_config)
        self.fr_info.grid(row=0, column=0)
        self.fr_control.grid(row=1, column=0)
        self.prompt.grid(row=1, column=1)

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "FG_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3)
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, padx=15, pady=15)

    def initTabContent(self):
        print("Initializing tab 9 (FG) content")
        self.init_fr_info()
        self.init_fr_control()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Function Generator Info', style="TPinkLabel.TLabel", width=20)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("fg")
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

        # Add labels for device information
        self.labelID = ttk.Label(self.fr_info, text='Device ID:', style="TLabel", width=15, anchor='w')
        self.labelIDValue = tk.Label(self.fr_info, text='', width=40, relief='sunken', anchor='w')

        self.labelTimeConnected = ttk.Label(self.fr_info, text='Connected At:', style="TLabel", width=15, anchor='w')
        self.labelTimeConnectedValue = tk.Label(self.fr_info, text='', width=25, relief='sunken', anchor='w')

        # Position the device information labels
        self.labelID.grid(row=1, column=0, sticky='W', padx=5, pady=2)
        self.labelIDValue.grid(row=1, column=1, sticky='W', padx=5, pady=2)
        self.labelTimeConnected.grid(row=2, column=0, sticky='W', padx=5, pady=2)
        self.labelTimeConnectedValue.grid(row=2, column=1, sticky='W', padx=5, pady=2)

        # Add labels for FG parameters
        self.labelWaveform = ttk.Label(self.fr_info, width=15, text='Waveform', style="TLabel", anchor='w')
        self.labelFrequency = ttk.Label(self.fr_info, width=15, text='Frequency (Hz)', style="TLabel", anchor='w')
        self.labelDutyCycle = ttk.Label(self.fr_info, width=15, text='Duty Cycle (%)', style="TLabel", anchor='w')

        # Position the parameter labels
        self.labelWaveform.grid(row=3, column=0, sticky='W', padx=5, pady=2)
        self.labelFrequency.grid(row=4, column=0, sticky='W', padx=5, pady=2)
        self.labelDutyCycle.grid(row=5, column=0, sticky='W', padx=5, pady=2)

        # Add value labels for parameters
        self.valueWaveform = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')
        self.valueFrequency = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')
        self.valueDutyCycle = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')

        # Position the value labels
        self.valueWaveform.grid(row=3, column=1, sticky='E', padx=5, pady=2)
        self.valueFrequency.grid(row=4, column=1, sticky='E', padx=5, pady=2)
        self.valueDutyCycle.grid(row=5, column=1, sticky='E', padx=5, pady=2)

        # ADD A REFRESH BUTTON
        self.btn_update = tk.Button(self.fr_info, text='UPDATE FG', command=self.update_FG)
        self.btn_update.grid(row=6, column=2, pady=5, padx=3, sticky='W')

    def init_fr_control(self):
        fr_m = self.fr_control

        # WAVEFORM SELECTION
        self.waveform_label = ttk.Label(fr_m, text="Waveform", style="TLabel")
        self.waveform_drop = guih.generate_drop_down(
            fr_m,
            ["SIN", "SQU", "TRI", "RAMP"]
        )
        self.waveform_set_btn = tk.Button(fr_m, text="Set Waveform",
                                          command=lambda: self.set_waveform(self.waveform_drop[1].get()))

        self.waveform_label.grid(row=0, column=0, padx=10, pady=10)
        self.waveform_drop[0].grid(row=0, column=1, padx=10, pady=10)
        self.waveform_set_btn.grid(row=0, column=2, padx=10, pady=10)

        # FREQUENCY CONTROL
        self.freq_label = ttk.Label(fr_m, text="Frequency (Hz)", style="TLabel")
        self.freq_entry = tk.Entry(fr_m)
        self.freq_set_btn = tk.Button(fr_m, text="Set Frequency",
                                      command=lambda: self.set_frequency(self.freq_entry.get()))

        self.freq_label.grid(row=1, column=0, padx=10, pady=10)
        self.freq_entry.grid(row=1, column=1, padx=10, pady=10)
        self.freq_set_btn.grid(row=1, column=2, padx=10, pady=10)

        # DUTY CYCLE CONTROL
        self.duty_label = ttk.Label(fr_m, text="Duty Cycle (%)", style="TLabel")
        self.duty_entry = tk.Entry(fr_m)
        self.duty_set_btn = tk.Button(fr_m, text="Set Duty",
                                      command=lambda: self.set_duty(self.duty_entry.get()))

        self.duty_label.grid(row=2, column=0, padx=10, pady=10)
        self.duty_entry.grid(row=2, column=1, padx=10, pady=10)
        self.duty_set_btn.grid(row=2, column=2, padx=10, pady=10)

        # OUTPUT TOGGLE
        self.output_toggle_btn = tk.Button(fr_m, text="Toggle Output", command=self.toggle_output)
        self.output_toggle_btn.grid(row=3, column=1, padx=10, pady=10)

    def gui_refresh_info(self):
        if self.fr_port.status:
            self.valueWaveform.config(text='{:8s}'.format(str(self.waveform)))
            self.valueFrequency.config(text='{:8s}'.format(str(self.frequency)))
            self.valueDutyCycle.config(text='{:8s}'.format(str(self.duty_cycle)))

    def gui_refresh(self, event):
        if event == "auto":
            self.fr_port.refresh_ports()
        # self.gui_refresh_info()

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def update_FG(self):
        if self.fr_port.status:
            try:
                self.frequency = self.cc.fg.query(
                    self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_frequency")
                )
                self.waveform = self.cc.fg.query(
                    self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_shape")
                )
                # Only try to get duty cycle if it exists in the command registry
                try:
                    self.duty_cycle = self.cc.fg.query(
                        self.cc.fg.registry.get_command(self.cc.fg.model, "command", "get_duty")
                    )
                except ValueError:
                    self.duty_cycle = "N/A"

                self.gui_refresh_info()
            except COMMUNICATION_ERRORS as e:
                guih.alert_user("Can't update FG", str(e), "warning")

    def toggle_output(self):
        if not self.cc.get_fg_status():
            guih.alert_user("Can't toggle output", "No FG connection!", "error")
            return False

        try:
            # Note: Most function generators use SCPI command for output control
            # This is a simplified version - may need model-specific implementation
            if self.output_on:
                self.cc.fg.write("OUTPut OFF")
                self.output_on = False
                self.prompt.print("Output turned OFF")
            else:
                self.cc.fg.write("OUTPut ON")
                self.output_on = True
                self.prompt.print("Output turned ON")
        except Exception as e:
            guih.alert_user("Can't toggle output", f"Error: {e}", "error")

        time.sleep(0.3)
        self.gui_refresh("call")

    def set_waveform(self, waveform):
        if self.cc.get_fg_status():
            try:
                cmd = self.cc.fg.registry.get_command(self.cc.fg.model, "command", "set_shape")
                cmd = cmd.format(value=waveform)
                self.cc.fg.write(cmd)
                self.waveform = waveform
                self.prompt.print(f"Set waveform to {waveform}")
                self.gui_refresh_info()
            except Exception as e:
                guih.alert_user("Can't set waveform", str(e), "error")
        else:
            guih.alert_user("Can't set waveform", "No FG connection!", "error")

    def set_frequency(self, frequency_str):
        if self.cc.get_fg_status():
            try:
                frequency = float(frequency_str)
                self.cc.fg.set_frequency(frequency)
                self.frequency = frequency
                self.prompt.print(f"Set frequency to {frequency} Hz")
                self.gui_refresh_info()
            except ValueError:
                guih.alert_user("Invalid Input", "Frequency must be a number", "error")
            except Exception as e:
                guih.alert_user("Can't set frequency", str(e), "error")
        else:
            guih.alert_user("Can't set frequency", "No FG connection!", "error")

    def set_duty(self, duty_str):
        if self.cc.get_fg_status():
            try:
                duty = float(duty_str)
                if duty < 0 or duty > 100:
                    guih.alert_user("Invalid Input", "Duty cycle must be 0-100%", "error")
                    return

                self.cc.fg.set_duty(duty)
                self.duty_cycle = duty
                self.prompt.print(f"Set duty cycle to {duty}%")
                self.gui_refresh_info()
            except ValueError:
                guih.alert_user("Invalid Input", "Duty cycle must be a number", "error")
            except Exception as e:
                guih.alert_user("Can't set duty cycle", str(e), "error")
        else:
            guih.alert_user("Can't set duty cycle", "No FG connection!", "error")

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PYVISA resource!")
        port = self.fr_port.get_port()

        ate_temp = self.registry[self.ate_drop[1].get()]
        self.cc.set_fg(ate_temp(self.fr_port.get_port()))

        try:
            self.id = self.cc.fg.test_conn()
        except COMMUNICATION_ERRORS as e:
            guih.alert_user("Can't connect to FG", str(e), "warning")
            self.fr_port.set_status(False)
            return False

        if self.id:  # CONNECTION SUCCESS
            # NOTE: re-initialize the frames in case anything like channel count, etc. needs different GUI elements
            self.init_fr_info()
            self.init_fr_control()

            # start doing stuff
            self.prompt.print(f"Connected to FG with id: {self.id}")
            self.labelIDValue.config(text=self.id)
            self.labelTimeConnectedValue.config(text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S"))
            self.fr_port.set_status(True)

            # turn output off initially
            self.output_on = False
            try:
                self.cc.fg.write("OUTPut OFF")
            except Exception:
                pass  # Some FGs may not support this command

            return True
        else:  # BAD ID received
            self.cc.set_fg(None)
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False

    def port_close(self):
        self.prompt.print(f"Closing PYVISA resource!")
        self.cc.fg.disconnect()
        self.fr_port.set_status(False)
        self.cc.set_fg(None)
        self.prompt.print(f"Connection is closed.")
