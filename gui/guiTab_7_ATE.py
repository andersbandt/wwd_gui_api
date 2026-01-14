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


# TODO: add some accuracy calculation section? or maybe that would be better in the respective equipment sections? if I can make it generic enough it can life here


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
        self.fr_info.grid(row=0, column=0, pady=15, padx=15)
        self.fr_control.grid(row=1, column=0, pady=15, padx=15)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

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
        self.fr_port.grid(row=0, column=1, padx=15, pady=15)

    def initTabContent(self):
        print("Initializing tab 7 (ATE) content")
        self.init_fr_info()
        self.init_fr_control()

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

    def gui_refresh(self, event):
        self.fr_port.refresh_ports()

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def ate_command(self, command_str):
        if self.ate is not None:
            self.ate.send_cmd(command_str)

    def ate_query(self, command_str):
        if self.ate is not None:
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





