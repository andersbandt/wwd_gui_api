"""
@file     guiTab_5_USB.py
@author   Anders Bandt
@date     March 2024
@brief    control device through serial (COM) port
"""

# import needed packages
import time
import tkinter as tk
from tkinter import *
from tkinter import ttk
import threading
import configparser
import os

# import user defined modules
from EEequipment.xds110 import xds110_api as xds110
from EEequipment.xds110.xds110_api import base_project_path, gmake_cmd
from common import subprocessor as subp
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.guiTab_parent import ThemedFrame



# initialize the config parser
config_file_path = "config/target.ini"
if os.path.exists(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
else:
    print(f"Configuration file {config_file_path} does not exist.")
    raise BaseException


# read in parameters from the config file
ps_channel = int(config["Target"]["ps_channel"])
device_vdds = float(config["Target"]["vdds"])
print("Yepppp")

class tabXDS110(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text
        l1 = ttk.Label(self, text="XDS110 and target control", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0)

        # set up prompt
        self.prompt = guic.Prompt(self, "XDS110 Comms", height=25, width=140)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

        # init frames within tab
        self.fr_xds110 = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_xds110.grid(row=1, column=0, padx=30, pady=12)
        self.fr_target = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_target.grid(row=2, column=0, padx=30, pady=12)
        self.fr_firmware = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_firmware.grid(row=2, column=1, padx=30, pady=12)

        # add some other variables
        self.canvas1 = tk.Canvas(self.fr_xds110, width=50, height=50)  # fr_xds110
        self.canvas2 = tk.Canvas(self.fr_target, width=50, height=50)  # fr_target
        self.canvas3 = tk.Canvas(self.fr_firmware, width=50, height=50)  # fr_firmware
        self.canvas4 = tk.Canvas(self.fr_firmware, width=50, height=50)  # fr_firmware
        self.toggle_drop = None  # fr_target
        self.lbl_target_v = None  # fr_target
        self.targetConfig_drop = None  # fr_firmware

        self.ser_obj = None

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab XDS110 content")
        self.init_fr_xds110()
        self.init_fr_target()
        self.init_fr_firmware()

    def init_fr_xds110(self):
        # XDS110 - BUTTON/STATUS
        # btn_check_xds110 = tk.Button(self.fr_xds110, text="XDS110 Check",
        #                           command=lambda: threading.Thread(target=self.check_xds110).start(),
        #                           bg="green", fg="white", height=2, width=15)
        btn_check_xds110 = ttk.Button(self.fr_xds110, text="XDS110 Check", style="TGreenButton.TButton",
                                  command=lambda: threading.Thread(target=self.check_xds110).start())
        btn_check_xds110.grid(row=3, column=1, padx=15, pady=22)
        self.canvas1.grid(row=3, column=2, padx=15, pady=22)

    def init_fr_target(self):
        # ROW 1 + 2
        # TARGET - BUTTON/STATUS
        btn_check_target = Button(self.fr_target, text="Target check",
                                  command=lambda: threading.Thread(target=self.check_target).start(),
                                  bg="green", fg="white", height=2, width=15)
        btn_check_target.grid(row=1, column=1, rowspan=2, padx=15, pady=22)
        self.canvas2.grid(row=1, column=2, rowspan=2, padx=15, pady=22)

        # TARGET VOLTAGE
        self.lbl_target_v = Label(self.fr_target)
        self.lbl_target_v.config(text="x.xx V")
        self.lbl_target_v.grid(row=1, column=3, padx=15, pady=22)

        self.var_usedmm = tk.IntVar()
        ttk.Checkbutton(self.fr_target,
                        text="Use DMM",
                        variable=self.var_usedmm,
                        onvalue=1,
                        offvalue=0).grid(row=2, column=3)

        # ROW 3
        btn_toggle_target = Button(self.fr_target, text="Toggle target",
                                   command=lambda: threading.Thread(target=self.toggle_target).start(),
                                   bg="orange", fg="black", height=2, width=15)
        btn_toggle_target.grid(row=3, column=2, padx=15, pady=22)
        self.toggle_drop = guih.generate_drop_down(
            self.fr_target,
            ["toggle", "assert", "deassert"]
        )
        self.toggle_drop[0].grid(row=3, column=3, padx=15, pady=15)

    def init_fr_firmware(self):
        fr_m = self.fr_firmware

        btn_build_firmware = Button(fr_m, text="Build firmware",
                                    command=lambda: threading.Thread(target=self.build_firmware).start(),
                                    bg="purple", fg="white", height=2, width=20)
        btn_build_firmware.grid(row=1, column=2, padx=15, pady=22)
        self.canvas3.grid(row=1, column=3, padx=15, pady=22)

        btn_flash_firmware = Button(fr_m, text="Load firmware",
                                    command=lambda: threading.Thread(target=self.flash_firmware).start(),
                                    bg="green", fg="white", height=2, width=20)
        btn_flash_firmware.grid(row=2, column=2, padx=15, pady=22)

        Label(fr_m, text="Time delay to flash (seconds)").grid(row=3,  column=2)
        self.entry_timesleep = Entry(fr_m, textvariable="seconds")
        self.entry_timesleep.grid(row=3, column=3)

        Label(fr_m, text="Auto off (seconds)").grid(row=4,  column=2)
        self.entry_timeautoff = Entry(fr_m)
        self.entry_timeautoff.grid(row=4, column=3)
        self.var_autooff = tk.IntVar()
        ttk.Checkbutton(self.fr_target,
                        text="Auto off?",
                        variable=self.var_autooff,
                        onvalue=1,
                        offvalue=0).grid(row=2, column=3)

        self.targetConfig_drop = guih.generate_drop_down(
            fr_m,
            ["target_power", "probe_power", "supply_power"]
        )
        self.targetConfig_drop[0].grid(row=2, column=3, padx=3, pady=10)
        self.canvas4.grid(row=2, column=4, padx=15, pady=22)

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def check_xds110(self):
        error_flag = 0

        [xds110_status, packet] = xds110.get_xds110_status()
        self.prompt.print(packet.get_string())

        if error_flag:
            self.prompt.print("Something went wrong checking XDS110 status")

        my_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        if xds110_status:
            self.canvas1.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
            return True
        else:
            self.canvas1.itemconfig(my_oval, fill="red")  # Fill the circle with RED
            return False

    def check_target(self):
        # check through dmm
        if self.var_usedmm.get():
            if self.cc.dmm is not None:
                dmm_voltage = self.cc.dmm.read_voltage()
                print(f"DMM got this for a measurement: {dmm_voltage}")
                self.lbl_target_v.config(text=f"{dmm_voltage} V")

        my_oval = self.canvas2.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        # update status of xds110

        xds110_status = self.check_xds110()
        if not xds110_status:
            # IF NO VALID XDS110 PROBE CONNECTION
            self.canvas2.itemconfig(my_oval, fill="yellow")  # Fill the circle with GREEN
        else:
            # get target status
            packet = xds110.get_jtag_integrity()
            self.prompt.print(packet.get_string())

            if packet.result:
                self.canvas2.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
                return True
            else:
                self.canvas2.itemconfig(my_oval, fill="red")  # Fill the circle with RED
                return False

    def toggle_target(self):
        xds110_status = self.check_xds110()
        if xds110_status:
            action = self.toggle_drop[1].get()
            status = xds110.toggle_target(action)
            self.prompt.print(f"Toggle status: {status}")
        else:
            guih.alert_user("Can't toggle target!", "XDS110 connection is not valid", "error")

    def build_firmware(self):
        my_oval = self.canvas3.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        self.canvas3.itemconfig(my_oval, fill="yellow")
        exec_path = base_project_path + "Debug/"
        packet = subp.execute_Popen(
            exec_path,
            gmake_cmd,
            ["-k",  # Keep going when some targets can't be made
             "-j",  # allow N jobs at once
             "8",  # 8 jobs
             "all",
             "-O"])  # Synchronize output of parallel jobs by TYPE (might not be setup right)
        self.prompt.print(packet.get_string())

        if len(packet.stderr) < 2:
            self.canvas3.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
            return True
        elif "error" in packet.stderr.lower():
            self.canvas3.itemconfig(my_oval, fill="red")  # Fill the circle with RED
            return False
        elif "warning" in packet.stderr.lower():
            self.canvas3.itemconfig(my_oval, fill="orange")  # Fill the circle with RED
            return True
        else:
            self.canvas3.itemconfig(my_oval, fill="red")  # Fill the circle with RED
            return False


    def flash_firmware(self):
        print("... executing loadti to flash firmware ...")
        my_oval = self.canvas4.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1

        # BUILD FIRMWARE
        self.build_firmware()

        # PERFORM TARGET CHECK
        flash_option = self.targetConfig_drop[1].get()

        # CONFIG POWER
        if flash_option == "target_power" or flash_option == "probe_power":
            try:
                self.cc.ps.output_off(1)
            except AttributeError:
                res = guih.promptYesNo("Can't access power supply!", "Can't access supply to turn off. Continue with flash?")
                if not res:
                    self.canvas4.itemconfig(my_oval, fill="red")  # Fill the circle with RED
                    return False

        if flash_option == "target_power":
            try:
                dut_vdd1_channel = self.cc.relay.return_channel("DUT_VDD_1")
                self.cc.relay.set_state(dut_vdd1_channel, 1)
            except AttributeError:
                res = guih.promptYesNo("Can't access relay!", "Can't access for relay power. Continue with flash?")
                if not res:
                    self.canvas4.itemconfig(my_oval, fill="red")  # Fill the circle with RED
                    return False
        elif flash_option == "probe_power":
            self.cc.relay.open_all()
        elif flash_option == "supply_power":
            self.cc.relay.open_all()
            try:
                self.cc.ps.set_voltage(ps_channel, device_vdds)
                self.cc.ps.output_on(1)
            except AttributeError:
                guih.alert_user("Can't access power supply!", "Can't access power supply. Aborting flash", "error")
                self.canvas4.itemconfig(my_oval, fill="red")  # Fill the circle with RED
                return

        # FLASH FIRMWARE
        # apply time delay (if added)
        sleep_second = self.entry_timesleep.get()
        if guih.is_float(sleep_second):
            time.sleep(float(sleep_second))
        elif sleep_second != '':
            guih.alert_user("Invalid sleep duration.", "Input is not an integer", "error")

        # perform flashing according to debug API
        self.canvas4.itemconfig(my_oval, fill="yellow")
        [firmware_status, packet] = xds110.flash_firmware(
            flash_option
        )

        self.prompt.print(packet.get_string())
        if firmware_status:
            self.canvas4.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
        else:
            self.canvas4.itemconfig(my_oval, fill="red")  # Fill the circle with RED

        # auto shut off of target
        if self.var_autooff.get():
            wait_seconds = self.entry_timeautoff.get()
            if guih.is_float(wait_seconds):
                # time.sleep(float(wait_seconds)) # TODO: I need to actually figure out how to implement a non-blocking auto-off call
                return True
            else:
                return False

    ##############################################################################
    ####      HELPER FUNCTIONS        ############################################
    ##############################################################################

