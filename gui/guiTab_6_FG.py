"""Function generator control tab."""

# import needed GUI packages
import tkinter as tk
from tkinter import ttk

# import needed packages
import time

# import user defined modules
from common import path_helper
from EEequipment import equipment_manager

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
        self.offset = "?"

        # set up recording / data information
        self.recName = False
        self.data_dir = path_helper.get_full_data_path(subdir="fg_data")

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "FG Console Output")

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_info.grid(row=0, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_control.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.prompt.grid(row=1, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
                                            self.theme_config,
                                            self.cc,
                                            "FG_PyVISA",
                                            self.port_init,
                                            self.port_close,
                                            port_func=3,
                                            status_cmd=lambda: self.cc.get_fg_status())
        if autoconnect:
            self.fr_port.connect_previous_port()
        self.fr_port.grid(row=0, column=1, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])

    def initTabContent(self):
        print("Initializing tab 6 (FG) content")
        self.init_fr_info()
        self.init_fr_control()

    def init_fr_info(self):
        self.labelInfo = ttk.Label(self.fr_info, text='Function Generator Info', style="TPinkLabel.TLabel", width=20)
        self.labelInfo.grid(row=0, column=0, columnspan=2, pady=5)

        # add equipment selector dropdown
        self.registry = equipment_manager.get_instruments("fg")
        self.cc.fg_service.set_registry(self.registry)
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            sorted(self.registry.keys())
        )
        self.ate_drop[0].grid(row=0, column=2, padx=15)

        # Load and set previous model if available
        previous_model = self.cc.get_used_model("FG_PyVISA")
        if previous_model and previous_model in self.registry:
            self.ate_drop[1].set(previous_model)
            print(f"Restored previous FG model: {previous_model}")

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
        self.labelAmplitude = ttk.Label(self.fr_info, width=15, text='Amplitude (V)', style="TLabel", anchor='w')
        self.labelOffset = ttk.Label(self.fr_info, width=15, text='Offset (V)', style="TLabel", anchor='w')

        # Position the parameter labels
        self.labelWaveform.grid(row=3, column=0, sticky='W', padx=5, pady=2)
        self.labelFrequency.grid(row=4, column=0, sticky='W', padx=5, pady=2)
        self.labelDutyCycle.grid(row=5, column=0, sticky='W', padx=5, pady=2)
        self.labelAmplitude.grid(row=6, column=0, sticky='W', padx=5, pady=2)
        self.labelOffset.grid(row=7, column=0, sticky='W', padx=5, pady=2)

        # Add value labels for parameters
        self.valueWaveform = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')
        self.valueFrequency = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')
        self.valueDutyCycle = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')
        self.valueAmplitude = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')
        self.valueOffset = tk.Label(self.fr_info, width=15, text='', relief='sunken', anchor='w')

        # Position the value labels
        self.valueWaveform.grid(row=3, column=1, sticky='E', padx=5, pady=2)
        self.valueFrequency.grid(row=4, column=1, sticky='E', padx=5, pady=2)
        self.valueDutyCycle.grid(row=5, column=1, sticky='E', padx=5, pady=2)
        self.valueAmplitude.grid(row=6, column=1, sticky='E', padx=5, pady=2)
        self.valueOffset.grid(row=7, column=1, sticky='E', padx=5, pady=2)

        # ADD A REFRESH BUTTON
        self.btn_update = tk.Button(self.fr_info, text='UPDATE FG', command=self.update_FG)
        self.btn_update.grid(row=8, column=2, pady=5, padx=3, sticky='W')

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

        # AMPLITUDE CONTROL
        self.amplitude_label = ttk.Label(fr_m, text="Amplitude (V)", style="TLabel")
        self.amplitude_entry = tk.Entry(fr_m)
        self.amplitude_set_btn = tk.Button(fr_m, text="Set Amplitude",
                                           command=lambda: self.set_amplitude(self.amplitude_entry.get()))

        self.amplitude_label.grid(row=3, column=0, padx=10, pady=10)
        self.amplitude_entry.grid(row=3, column=1, padx=10, pady=10)
        self.amplitude_set_btn.grid(row=3, column=2, padx=10, pady=10)

        # OFFSET CONTROL
        self.offset_label = ttk.Label(fr_m, text="Offset (V)", style="TLabel")
        self.offset_entry = tk.Entry(fr_m)
        self.offset_set_btn = tk.Button(fr_m, text="Set Offset",
                                        command=lambda: self.set_offset(self.offset_entry.get()))

        self.offset_label.grid(row=4, column=0, padx=10, pady=10)
        self.offset_entry.grid(row=4, column=1, padx=10, pady=10)
        self.offset_set_btn.grid(row=4, column=2, padx=10, pady=10)

        # OUTPUT TOGGLE
        self.output_toggle_btn = tk.Button(fr_m, text="Toggle Output", command=self.toggle_output)
        self.output_toggle_btn.grid(row=5, column=1, padx=10, pady=10)

    def gui_refresh_info(self):
        if self.fr_port.status:
            self.valueWaveform.config(text='{:8s}'.format(str(self.waveform)))
            self.valueFrequency.config(text='{:8s}'.format(str(self.frequency)))
            self.valueDutyCycle.config(text='{:8s}'.format(str(self.duty_cycle)))
            self.valueAmplitude.config(text='{:8s}'.format(str(self.amplitude)))
            self.valueOffset.config(text='{:8s}'.format(str(self.offset)))

    def gui_refresh(self, event):
        if event == "auto":
            self.fr_port.refresh_ports()
        # self.gui_refresh_info()

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def update_FG(self):
        if self.fr_port.status:
            freq = self.cc.fg_service.get_frequency()
            shape = self.cc.fg_service.get_shape()
            if freq is None or shape is None:
                guih.alert_user("Can't update FG", "Communication error reading FG parameters", "warning")
                return

            self.frequency = freq
            self.waveform = shape
            self.duty_cycle = self.cc.fg_service.get_duty() or "N/A"
            self.amplitude = self.cc.fg_service.get_amplitude() or "N/A"
            self.offset = self.cc.fg_service.get_offset() or "N/A"
            self.gui_refresh_info()

    def toggle_output(self):
        if not self.cc.get_fg_status():
            guih.alert_user("Can't toggle output", "No FG connection!", "error")
            return False

        if self.output_on:
            success = self.cc.fg_service.output_off()
            if success:
                self.output_on = False
                self.prompt.print("Output turned OFF")
            else:
                guih.alert_user("Can't toggle output", "Failed to turn output OFF", "error")
        else:
            success = self.cc.fg_service.output_on()
            if success:
                self.output_on = True
                self.prompt.print("Output turned ON")
            else:
                guih.alert_user("Can't toggle output", "Failed to turn output ON", "error")

        time.sleep(0.3)
        self.gui_refresh("call")

    def set_waveform(self, waveform):
        if self.cc.fg_service.set_shape(waveform):
            self.waveform = waveform
            self.prompt.print(f"Set waveform to {waveform}")
            self.gui_refresh_info()
        else:
            guih.alert_user("Can't set waveform", "No FG connection or communication error", "error")

    def set_frequency(self, frequency_str):
        try:
            frequency = float(frequency_str)
        except ValueError:
            guih.alert_user("Invalid Input", "Frequency must be a number", "error")
            return

        if self.cc.fg_service.set_frequency(frequency):
            self.frequency = frequency
            self.prompt.print(f"Set frequency to {frequency} Hz")
            self.gui_refresh_info()
        else:
            guih.alert_user("Can't set frequency", "No FG connection or communication error", "error")

    def set_duty(self, duty_str):
        try:
            duty = float(duty_str)
        except ValueError:
            guih.alert_user("Invalid Input", "Duty cycle must be a number", "error")
            return

        if duty < 0 or duty > 100:
            guih.alert_user("Invalid Input", "Duty cycle must be 0-100%", "error")
            return

        if self.cc.fg_service.set_duty(duty):
            self.duty_cycle = duty
            self.prompt.print(f"Set duty cycle to {duty}%")
            self.gui_refresh_info()
        else:
            guih.alert_user("Can't set duty cycle", "No FG connection or communication error", "error")

    def set_amplitude(self, amplitude_str):
        try:
            amplitude = float(amplitude_str)
        except ValueError:
            guih.alert_user("Invalid Input", "Amplitude must be a number", "error")
            return

        if self.cc.fg_service.set_amplitude(amplitude):
            self.amplitude = amplitude
            self.prompt.print(f"Set amplitude to {amplitude} V")
            self.gui_refresh_info()
        else:
            guih.alert_user("Can't set amplitude", "No FG connection or communication error", "error")

    def set_offset(self, offset_str):
        try:
            offset = float(offset_str)
        except ValueError:
            guih.alert_user("Invalid Input", "Offset must be a number", "error")
            return

        if self.cc.fg_service.set_offset(offset):
            self.offset = offset
            self.prompt.print(f"Set offset to {offset} V")
            self.gui_refresh_info()
        else:
            guih.alert_user("Can't set offset", "No FG connection or communication error", "error")

    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PyVISA resource!")
        port = self.fr_port.get_port()
        model_name = self.ate_drop[1].get()
        result = self.cc.fg_service.connect(port, model_name)

        if not result.success:
            self.prompt.print(result.error, "error")
            guih.alert_user("Can't connect to FG", result.error, "warning")
            self.fr_port.set_status(False)
            return False

        self.init_fr_info()
        self.init_fr_control()

        self.prompt.print(f"Connected to FG with id: {result.device_id}")
        self.labelIDValue.config(text=result.device_id)
        self.labelTimeConnectedValue.config(text=result.timestamp)
        self.fr_port.set_status(True)
        self.output_on = False

        if result.error:
            self.prompt.print(f"Warning: {result.error}", "warning")
        return True

    def port_close(self):
        self.prompt.print("Closing FG resource!")
        result = self.cc.fg_service.disconnect()
        if not result.success:
            guih.alert_user("Can't disconnect FG", result.error, "warning")
        self.fr_port.set_status(False)
