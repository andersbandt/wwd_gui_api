"""XDS110 JTAG debug probe interface tab."""

# import needed packages
import time
from tkinter import *
from tkinter import filedialog
import os

# import user defined modules
from EEequipment.xds110 import xds110_api as xds110
from EEequipment.xds110.xds110_api import base_project_path, gmake_cmd
from common import subprocessor as subp
from common.path_helper import get_config_path
from services.config_service import ConfigService
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import *


class tabXDS110(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config):
        super().__init__(master, theme_config)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath
        self.after_call_id = None

        # print welcome text_data
        l1 = ttk.Label(self, text="XDS110 and target control", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0)

        # set up prompt
        self.prompt = guic.Prompt(self, self.theme_config, "XDS110 Comms")
        self.prompt.grid(row=10, column=0, columnspan=4, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], sticky="NSEW")

        # configure grid weights so prompt expands to fill available space
        self.columnconfigure(0, weight=1)
        self.rowconfigure(10, weight=1)

        # init frames within tab
        self.fr_xds110 = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_xds110.grid(row=1, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])
        self.fr_firmware = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_firmware.grid(row=1, column=2, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"], rowspan=2)
        self.fr_target = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_target.grid(row=2, column=0, padx=self.theme_config["pad"]["frame_x"], pady=self.theme_config["pad"]["frame_y"])

        # add some other GUI variables
        self.status_xds110 = ColorCircle(self.fr_xds110, width=50, height=50, bg=self.theme_config["bg_dark"])
        self.status_target = ColorCircle(self.fr_target, width=50, height=50, bg=self.theme_config["bg_dark"])
        self.toggle_drop = None  # fr_target
        self.lbl_target_v = None  # fr_target
        self.targetConfig_drop = None  # fr_firmware

        # initialize tab content
        self.initTabContent()

        # load target settings
        self.parse_target_config(get_config_path())

    def initTabContent(self):
        print("Initializing tab 4 (XDS110) content")
        self.init_fr_xds110()
        self.init_fr_target()
        self.init_fr_firmware()

    def _run_in_thread(self, func, button):
        """Disable button, run func in a background thread, re-enable when done."""
        button.config(state="disabled")
        def wrapper():
            try:
                func()
            finally:
                self.after(0, lambda: button.config(state="normal"))
        threading.Thread(target=wrapper).start()

    def init_fr_xds110(self):
        # XDS110 - BUTTON/STATUS
        self.btn_check_xds110 = tk.Button(self.fr_xds110, text="XDS110 Check",
                                          command=lambda: self._run_in_thread(self.check_xds110, self.btn_check_xds110))
        self.btn_check_xds110.grid(row=3, column=1, padx=15, pady=22)
        self.status_xds110.grid(row=3, column=2, padx=15, pady=22)

    def init_fr_target(self):
        # ROW 1 + 2
        # TARGET - BUTTON/STATUS
        self.btn_check_target = Button(self.fr_target, text="Target check",
                                  command=lambda: self._run_in_thread(self.check_target, self.btn_check_target),
                                  bg=self.theme_config["dark_2"], fg=self.theme_config["fg_light"], height=2, width=15)
        self.btn_check_target.grid(row=1, column=1, rowspan=2, padx=15, pady=22)
        self.status_target.grid(row=1, column=2, rowspan=2, padx=15, pady=22)

        # TARGET VOLTAGE
        self.lbl_target_v = ttk.Label(self.fr_target, style="TSpunkLabel.TLabel")
        self.lbl_target_v.config(text="x.xx V")
        self.lbl_target_v.grid(row=1, column=3, padx=15, pady=22)

        self.var_usedmm = tk.IntVar()
        ttk.Checkbutton(self.fr_target,
                        text="Use DMM",
                        variable=self.var_usedmm,
                        onvalue=1,
                        offvalue=0).grid(row=2, column=3)

        # ROW 3
        self.btn_toggle_target = Button(self.fr_target, text="Toggle target",
                                   command=lambda: self._run_in_thread(self.toggle_target, self.btn_toggle_target),
                                   bg=self.theme_config["light_3"], fg=self.theme_config["fg_dark"], height=2, width=15)
        self.btn_toggle_target.grid(row=3, column=2, padx=15, pady=22)
        self.toggle_drop = guih.generate_drop_down(
            self.fr_target,
            ["toggle", "assert", "deassert"]
        )
        self.toggle_drop[0].grid(row=3, column=3, padx=15, pady=15)

    def init_fr_firmware(self):
        fr_m = self.fr_firmware

        # set up all the usable objects
        self.entry_timesleep = Entry(fr_m, textvariable="seconds")
        self.entry_timeautoff = Entry(fr_m)
        self.buildStatus = ColorCircle(fr_m, width=50, height=50, bg=self.theme_config["bg_dark"])
        self.flashStatus = ColorCircle(fr_m, width=60, height=60, bg=self.theme_config["bg_dark"])

        # place buttons
        self.btn_build_firmware = Button(fr_m, text="Build firmware",
                                    command=lambda: self._run_in_thread(self.build_firmware, self.btn_build_firmware),
                                    bg=self.theme_config["dark_2"], fg=self.theme_config["fg_dark"], height=2,
                                    width=20)

        self.btn_flash_firmware = Button(fr_m, text="Load firmware",
                                    command=lambda: self._run_in_thread(self.flash_firmware, self.btn_flash_firmware),
                                    bg=self.theme_config["light_1"], fg=self.theme_config["fg_light"], height=2,
                                    width=20)
        load_config = Button(fr_m, text="Load configuration",
                                    command=lambda: self.load_config(),
                                    bg=self.theme_config["dark_3"], fg=self.theme_config["fg_dark"], height=1,
                                    width=20)

        # place drop downs
        self.tg_opt = ["target_power", "probe_power", "supply_power"]
        self.targetConfig_drop = guih.generate_drop_down(
            fr_m,
            self.tg_opt
        )
        self.db_opt = ["", "ORANGE12", "PURPLE47"]
        self.serialNumber_drop = guih.generate_drop_down(
            fr_m,
            self.db_opt
        )
        self.defaultTarget_drop = guih.generate_drop_down(
            fr_m,
            ["default", 2],
            callback_func=lambda: self.autoload_config()
        )

        # place checkbuttons
        self.var_autooff = tk.IntVar()
        self.checkAutoOff = ttk.Checkbutton(fr_m,
                                            text="Auto off?",
                                            variable=self.var_autooff,
                                            onvalue=1,
                                            offvalue=0)
        self.var_toggle= tk.IntVar()
        self.checkToggle = ttk.Checkbutton(fr_m,
                                            text="Toggle?",
                                            variable=self.var_toggle,
                                            onvalue=1,
                                            offvalue=0)

        # place the usable objects with .grid()
        self.btn_build_firmware.grid(row=1, column=0, padx=15, pady=22)
        self.buildStatus.grid(row=1, column=1)
        ttk.Label(fr_m, text="Time delay to flash (seconds)").grid(row=2, column=0, padx=10, pady=15)
        self.entry_timesleep.grid(row=2, column=1)
        ttk.Label(fr_m, text="Auto off (seconds)", style="TLabel").grid(row=4, column=0)
        self.entry_timeautoff.grid(row=4, column=1)
        self.checkAutoOff.grid(row=4, column=2, pady=6)
        self.checkToggle.grid(row=5, column=2)
        self.targetConfig_drop[0].grid(row=2, column=2, padx=6, pady=10)
        self.serialNumber_drop[0].grid(row=3, column=2, pady=2)
        self.btn_flash_firmware.grid(row=6, column=0, padx=15, pady=22)
        self.flashStatus.grid(row=6, column=1, padx=15, pady=22)
        self.defaultTarget_drop[0].grid(row=7, column=0, pady=2)
        load_config.grid(row=7, column=1, padx=15, pady=22)


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def check_xds110(self):
        [xds110_status, packet] = xds110.get_xds110_status()
        if packet is False:
            self.prompt.print("Something went wrong checking XDS110 status", print_type="error")
            self.status_xds110.set_color("red")
            return False
        else:
            self.prompt.print(packet.get_string())


        if xds110_status:
            self.status_xds110.set_color("green")
            return True
        else:
            return False

    def check_target(self):
        # check through dmm
        if self.var_usedmm.get():
            if self.cc.dmm is not None:
                dmm_voltage = self.cc.dmm.read_voltage()
                print(f"DMM got this for a measurement: {dmm_voltage}")
                self.lbl_target_v.config(text=f"{dmm_voltage} V")


        # update status of xds110
        xds110_status = self.check_xds110()
        if not xds110_status:
            # IF NO VALID XDS110 PROBE CONNECTION
            self.status_target.set_color("yellow")
        else:
            # get target status
            packet = xds110.get_jtag_integrity()
            self.prompt.print(packet.get_string())

            if packet.result:
                self.status_target.set_color("green")
                return True
            else:
                self.status_target.set_color("red")
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
        self.buildStatus.set_color("yellow")
        exec_path = base_project_path + "Debug/"
        packet = subp.execute_Popen(
            exec_path,
            gmake_cmd,
            ["-k",  # Keep going when some targets can't be made
             "-j",  # allow N jobs at once
             "8",  # 8 jobs
             "all",
             "-O"])  # Synchronize output of parallel jobs by TYPE (might not be setup right)

        # something went wrong executing subprocess
        if packet is False:
            self.prompt.print(f"Probably FileNotFoundError for path {exec_path}", "error")
            self.prompt.print("Something went wrong executing subprocess.", "error")
            return

        # otherwise we probably got some response
        self.prompt.print(packet.get_string())
        if len(packet.stderr) < 2:
            self.buildStatus.set_color("green")
            return True
        elif "error" in packet.stderr.lower():
            self.buildStatus.set_color("red")
            return False
        elif "warning" in packet.stderr.lower():
            self.buildStatus.set_color("orange")
            return True
        else:
            self.buildStatus.set_color("red")
            return False

    def flash_firmware(self):
        print("... executing loadti to flash firmware ...")

        ### BUILD FIRMWARE
        build_status = self.build_firmware()
        if not build_status:
            self.flashStatus.set_color("black")  # RED
            return False

        ### HANDLE POWER
        flash_option = self.targetConfig_drop[1].get()

        # destroy any previous calls to turn off power
        if self.after_call_id is not None:
            self.after_cancel(self.after_call_id)

        # toggle power
        if self.var_toggle.get():
            self.turn_power_off(flash_option)
            time.sleep(self.toggle_power_delay)
        # turn on power
        power_status = self.turn_power_on(flash_option)
        if power_status is False:
            return False

        ### FLASH FIRMWARE
        # apply time delay (if added)
        sleep_second = self.entry_timesleep.get()
        if type(sleep_second) == float:
            time.sleep(float(sleep_second))
        elif sleep_second != '':
            guih.alert_user("Invalid sleep duration.", "Input is not an integer", "error")

        # perform flashing according to debug API
        serial_option = self.serialNumber_drop[1].get()
        self.flashStatus.set_color(self.theme_config["warning"])
        [firmware_status, packet] = xds110.flash_firmware(
            flash_option, serial_option
        )

        # Assuming packet.stdout and packet.stderr are available
        if hasattr(packet, "stdout") and hasattr(packet, "stderr"):
            self.prompt.print(packet.stdout, type="info")
            self.prompt.print(packet.stderr, type="error")
        else:
            # Fallback if separate streams are not available
            self.prompt.print(packet.get_string())

        if firmware_status:
            self.flashStatus.set_color(self.theme_config["success"])
        else:
            self.flashStatus.set_color(self.theme_config["error"])

        # auto shut off of target
        if self.var_autooff.get():
            wait_seconds = int(self.entry_timeautoff.get())
            self.after_call_id = self.after(wait_seconds * 1000, lambda: self.turn_power_off(flash_option))
            return True
        else:
            return False

    def load_config(self):
        """
        Open a configuration file and display its contents in the text widget.
        """
        print("Loading target configuration")
        file_path = filedialog.askopenfilename(
            title="Open Configuration File",
            filetypes=(("Config Files", "*.ini *.cfg *.json *.yaml *.yml"), ("All Files", "*.*"))
        )
        if file_path:
            try:
                self.prompt.print(f"Trying to open and parse target configuration file @ {file_path}")
                self.parse_target_config(file_path)
            except Exception:
                guih.alert_user("Can't open file", "Couldn't open target configuration file", "error")

    def autoload_config(self):
        cfg = self.defaultTarget_drop[1].get()
        print(f"Autoloading with config num: {cfg}")
        self.parse_target_config(os.path.join("config", f"{cfg}.ini"))


    ##############################################################################
    ####      HELPER FUNCTIONS        ############################################
    ##############################################################################

    def parse_target_config(self, config_file_path):
        # Load target config via ConfigService
        if config_file_path == get_config_path():
            tc = self.cc.config_svc.get_target_config()
        else:
            tc = ConfigService.load_target_config_from_file(config_file_path)

        # Apply parsed values to GUI variables
        self.ps_channel = tc.ps_channel
        self.device_vdds = tc.vdds
        self.device_usb_relay = tc.usb_relay
        self.toggle_power_delay = tc.toggle_power_delay

        self.targetConfig_drop[1].set(self.tg_opt[tc.power_type])
        self.serialNumber_drop[1].set(self.db_opt[tc.debug_config])

    def turn_power_on(self, flash_option):
        # CONFIG POWER
        if flash_option == "target_power" or flash_option == "probe_power":
            try:
                self.cc.ps.output_off(self.ps_channel)
            except (AttributeError, ValueError):
                res = guih.promptYesNo("Can't access power supply!",
                                       "Can't access supply to turn off. Continue with flash?")
                if not res:
                    self.flashStatus.set_color(self.theme_config["error"])
                    return False

        if flash_option == "target_power":
            pass
            try:
                if self.device_usb_relay != 0:
                    self.cc.relay.set_state(self.device_usb_relay, 1)
            except AttributeError:
                res = guih.promptYesNo("Can't access relay!", "Can't access for relay power. Continue with flash?")
                if not res:
                    self.flashStatus.set_color(self.theme_config["error"])
                    return False
        elif flash_option == "probe_power":
            pass
        elif flash_option == "supply_power":
            self.cc.relay.set_state(self.device_usb_relay, 0)
            try:
                self.cc.ps.set_voltage(self.ps_channel, self.device_vdds)
                self.cc.ps.output_on(self.ps_channel)
            except (AttributeError, ValueError): # AttributeError covers PS not init case. ValueError covers disconnect case.
                guih.alert_user("Can't access power supply!", "Can't access power supply. Aborting flash", "error")
                self.flashStatus.set_color(self.theme_config["error"])  # RED
                return False

    def turn_power_off(self, flash_option):
        if flash_option == "target_power":
            self.cc.relay.open_all()
        elif flash_option == "probe_power":
            return
        elif flash_option == "supply_power":
            self.cc.ps.output_off(self.ps_channel)
