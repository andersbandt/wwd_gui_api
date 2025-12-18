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
from gui.guiTab_parent import ThemedFrame

# import needed packages
from datetime import datetime
import pyvisa.errors


import EEequipment
import inspect, pkgutil, importlib, EEequipment
# TODO: can I print out everything I imported and tie that into a drop down ???



def get_instruments():
    """
    Return [(display_name, class_obj), ...] by walking all subpackages/submodules
    within EEequipment. Only includes classes defined in their modules (no imports).
    """
    items = []
    pkg_name = EEequipment.__name__
    for module_info in pkgutil.walk_packages(EEequipment.__path__, prefix=f"{pkg_name}."):
        modname = module_info.name
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue  # Skip modules that fail to import

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Only include classes defined in this module (avoid re-exported ones)
            if obj.__module__ == modname:
                display = f"{modname}.{name}"  # e.g., EEequipment.power_supplies.E3640A.E3640A
                items.append((display, obj))
    return items




class TabATE(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file, autoconnect):
        super().__init__(master, theme_file)
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
        self.prompt = guic.Prompt(self, "ATE Output", height=18, width=140)

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_info.grid(row=0, column=0, pady=15, padx=15)
        self.fr_control.grid(row=1, column=0, pady=15, padx=15)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # set up serial port (has to be done after tab content is initialized)
        self.fr_port = guic.SerialConnFrame(self,
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
        # initialize port list
        self.ate_drop = guih.generate_drop_down(
            self.fr_info,
            get_instruments()
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
        self.cmd_button = ttk.Button(fr_m, text="Send", style="TButton",
                                      command=lambda: self.ate_command(self.cmd_entry.get())
                                      )


        # MISC CONTROL
        self.benchmark = ttk.Button(fr_m, text="Benchmark", style="TButton",
                                      command=lambda: self.ate_benchmark()
                                      )

        # place everything on grid
        self.cmd_label.grid(row=1, column=0, padx=10, pady=10)
        self.cmd_entry.grid(row=1, column=1, padx=10, pady=10)
        self.cmd_button.grid(row=1, column=2, padx=10, pady=10)
        self.benchmark.grid(row=2, column=0, padx=10, pady=10)

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################


    def ate_command(self, command_str):
        if self.ate is not None:
            self.ate.send_command(command_str)

    def ate_benchmark(self):
        if self.ate is not None:
            self.ate.benchmark()


    #################################
    #### SERIAL (COM)  ##############
    #################################

    # NOTE: this is called by my SerialConnFrame. It must return True or False to properly set status
    def port_init(self):
        self.prompt.print("Connect to PYVISA resource!")
        port = self.fr_port.get_port()

        # TODO: need to somehow grab a dropdown of selectable classes here
        self.ate = EEequipment.E3640A.E3640A.E3640A(port)

        try:
            self.id = self.ate.test_conn()
        except AttributeError as e:
            guih.alert_user("Can't connect to VISA", e, "warning")
            self.fr_port.set_status(False)
            return False
        except pyvisa.errors.VisaIOError as e:
            guih.alert_user("Can't connect to VISA", e, "error")
            self.fr_port.set_status(False)

        if self.id:  # CONNECTION SUCCESS
            self.prompt.print(f"Connected to PS with id: {self.id}")
            self.cc.set_ps(self.ps)
            self.labelIDValue.config(text=self.id)
            self.labelTimeConnectedValue.config(
                text=datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            )
            self.fr_port.set_status(True)

            # turn channels off and set voltages
            self.ps.output_off(1)
            self.ps.output_off(2)
            self.ch1_on = 0
            self.ch2_on = 0

            # gui refresh
            self.gui_refresh_channel_state()
            return True
        else:  # BAD ID received
            self.ps = None
            self.fr_port.set_status(False)
            tkmb.showerror("Device error", "Device at " + port + " does not respond or is not correct config")
            return False

    def port_close(self):
        self.prompt.print(f"Closing PYVISA resource!")
        self.ps.disconnect()
        self.fr_port.set_status(False)
        self.cc.set_ps(None)
        self.prompt.print(f"Connection is closed.")





