
# import needed packages
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import threading
import os
import time
from time import localtime, strftime
from datetime import datetime

# import user defined modules
from imu import imu_analysis
from analysis.csv_helper import CSVHelper

# import user defined GUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.gui_class import ColorCircle


class TabLog(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.basefilepath = basefilepath

        self.grid(row=0, column=0)

        # set up recording information
        self.record_speed = 1
        self.record_status = False
        self.recCnt = 0
        #self.recName = ''
        self.data_dir = basefilepath + "/data/"
        self.csvh = None
        self.record_config = None

        self.fr_status = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_setup = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_analysis = tk.Frame(self, bg=self.theme_config["light_4"])
        self.fr_status = tk.Frame(self, bg=self.theme_config["light_4"])

        # set up prompt
        self.prompt = guic.Prompt(self,
                                   "Data Logger Output",
                                  height=self.theme_config["size"]["h_prompt"],
                                  width=self.theme_config["size"]["w_prompt"])

        # initialize tab content
        self.initTabContent()

        # place everything in grid
        self.fr_status.grid(row=1, column=0, pady=15, padx=15)
        self.fr_setup.grid(row=1, column=1, rowspan=2, pady=15, padx=15)
        self.fr_analysis.grid(row=2, column=0, pady=15, padx=15)
        self.prompt.grid(row=10, column=0, columnspan=4, padx=30, pady=12)

    def initTabContent(self):
        print("Initializing tab 2 (Logger) content")

        # print welcome text_data
        l1 = ttk.Label(self, text="Data Logger", style="BW.TLabel",
                       font=(self.theme_config["font"]["family"], 16))
        l1.grid(column=0, row=0, columnspan=4)

        self.init_fr_status()
        self.init_fr_setup()
        self.init_fr_analysis()

    def init_fr_status(self):
        # Serial connection status
        self.labelSerStat = ttk.Label(self.fr_status, width=10, text='Serial', style="TLabel", anchor='w')
        self.ser_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelSerStat.grid(row=0, column=0, pady=15, padx=15)
        self.ser_status.grid(row=0, column=1, pady=15, padx=15)
        # DMM connection status
        self.labelDmmStat = ttk.Label(self.fr_status, width=10, text='DMM', style="TLabel", anchor='w')
        self.dmm_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelDmmStat.grid(row=1, column=0, pady=15, padx=15)
        self.dmm_status.grid(row=1, column=1, pady=15, padx=15)
        # PS connection status
        self.labelPsStat = ttk.Label(self.fr_status, width=10, text='PS', style="TLabel", anchor='w')
        self.ps_status = ColorCircle(self.fr_status, width=50, height=50,
                                    bg=self.theme_config["bg_dark"])  # create a Canvas widget
        self.labelPsStat.grid(row=2, column=0, pady=15, padx=15)
        self.ps_status.grid(row=2, column=1, pady=15, padx=15)

    def init_fr_setup(self):
        # add directory search
        self.lbl_data_directory = tk.Label(self.fr_setup, text=self.data_dir, bg=self.theme_config["bg_light"])
        self.lbl_data_directory.grid(row=2, column=0)
        btn_set_directory = tk.Button(self.fr_setup, text="Set directory",
                                 command=lambda: self.set_record_directory(),
                                 bg=self.theme_config["light_1"], fg="black", height=1, width=10)
        btn_set_directory.grid(row=1, column=0, padx=15, pady=22)

        # add output file name box
        tk.Label(self.fr_setup, text="Output file name").grid(row=2, column=2, padx=5, pady=20)
        self.output_file_name = tk.Text(self.fr_setup, height=2, width=20)
        self.output_file_name.grid(row=2, column=3, pady=20)

        # add serial parameters box
        tk.Label(self.fr_setup, text="Serial parameters").grid(row=3, column=0, padx=5, pady=5)
        self.serial_log_params = tk.Text(self.fr_setup, height=2, width=40)
        self.serial_log_params.grid(row=3, column=1)

        # add check boxes for the various options
        self.var_use_ser = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use Serial",
                        variable=self.var_use_ser,
                        onvalue=1,
                        offvalue=0).grid(row=4, column=0, pady=2)

        self.var_use_dmm = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use DMM",
                        variable=self.var_use_dmm,
                        onvalue=1,
                        offvalue=0).grid(row=4, column=1)

        self.var_use_ps = tk.IntVar()
        ttk.Checkbutton(self.fr_setup,
                        text="Use PS",
                        variable=self.var_use_ps,
                        onvalue=1,
                        offvalue=0).grid(row=4, column=2)

        # speed recording options
        options = ['1s', '2s', '5s', '10s', '30s', '60s', '5m', '10m', '30m', '1h', '0.5s']
        self.optRecSpd, self.RecSpdVal = guih.generate_drop_down(self.fr_setup, options)
        self.optRecSpd.grid(row=5, column=0, padx=3)

        # set up button START recording
        btn_start_entry = tk.Button(self.fr_setup, text="Start Record",
                                 command=lambda: self.start_record(),
                                 bg=self.theme_config["success"], fg="white", height=2, width=15)
        btn_start_entry.grid(row=5, column=1, padx=15, pady=5)

        # set up button STOP recording
        btn_stop_entry = tk.Button(self.fr_setup, text="Stop Record",
                                command=lambda: self.stop_record(),
                                bg=self.theme_config["error"], fg="white", height=2, width=15)
        btn_stop_entry.grid(row=5, column=2, padx=15, pady=5)

        self.labelRNums = ttk.Label(self.fr_setup, text='', width=8, relief='sunken')
        self.labelRNums.grid(row=5, column=3, padx=10, pady=10, sticky='W')

        # set up button START live GRAPH
        btn_live_graph = tk.Button(self.fr_setup, text="Live Graph",
                                command=lambda: None,
                                bg=self.theme_config["dark_3"], fg="white", height=2, width=15)
        btn_live_graph.grid(row=6, column=1, pady=5)

    def init_fr_analysis(self):
        # Create a StringVar to hold the selected file path
        selected_file = tk.StringVar(self.fr_analysis)

        def get_file_list(directory):
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            return files

        file_list = get_file_list(self.basefilepath + "/data") # tag:HARDCODE
        # Create an OptionMenu with a button to open the file dialog
        file_dropdown = tk.OptionMenu(self.fr_analysis, selected_file, *file_list)
        file_dropdown.grid(row=0, column=0, pady=10)

        def refresh_file_list():
            new_file_list = get_file_list(self.basefilepath + self.data_folder)
            new_file_dropdown = tk.OptionMenu(self.fr_analysis, selected_file, *new_file_list)
            new_file_dropdown.grid(row=0, column=0, pady=10)

        refresh_file_btn = tk.Button(self.fr_analysis, text="Refresh files",
                                  command=lambda: refresh_file_list(),
                                  bg="green", fg="white")
        refresh_file_btn.grid(row=0, column=1, padx=1, pady=7)  # place 'Add Category' button

        open_button = tk.Button(self.fr_analysis,
                                text="Analyze file data",
                                command=lambda: self.analyze_file(selected_file.get())
                                )
        open_button.grid(row=3, column=1, padx=10, pady=10)
        graph_button = tk.Button(self.fr_analysis,
                                 text="Graph file data",
                                 command=lambda: self.graph_file(selected_file.get())
                                 )
        graph_button.grid(row=4, column=1, padx=10, pady=10)

    def gui_refresh(self, event):
        if event == "auto":
            if self.cc.get_ser_status():
                self.ser_status.set_color(self.theme_config["success"])
            else:
                self.ser_status.set_color(self.theme_config["error"])
            if self.cc.get_dmm_status():
                self.dmm_status.set_color(self.theme_config["success"])
            else:
                self.dmm_status.set_color(self.theme_config["error"])
            if self.cc.get_ps_status():
                self.ps_status.set_color(self.theme_config["success"])
            else:
                self.ps_status.set_color(self.theme_config["error"])


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    def start_record(self):
        # Organize parameters first
        self.organize_record_params()
        self.record_status = False
        self.recCnt = 0

        # Check Serial if requested
        if self.record_config["use_ser"]:
            if not self.cc.get_ser_status():
                guih.alert_user("Can't start record!", "Serial connection is not valid!", "error")
                return
            print("Serial is ready.")
            self.record_status = True

        # Check DMM if requested
        if self.record_config["use_dmm"]:
            if not self.cc.get_dmm_status():
                guih.alert_user("Can't start record!", "DMM connection is not valid!", "error")
                return
            self.record_status = True

        # Check Power Supply if requested
        if self.record_config["use_ps"]:
            if not self.cc.get_ps_status():
                guih.alert_user("Can't start record!", "Power Supply connection is not valid!", "error")
                return
            self.record_status = True

        if not self.record_status:
            guih.alert_user("Can't start record!", "No instruments selected", "error")
            return

        # If we reach here, all requested instruments are ready and user has selected at least 1 instrument
        self.prompt.print(f"Starting Logging record every {self.record_speed} seconds ...")
        self.record_status = True
        threading.Thread(target=self.thread_record).start()

    def stop_record(self):
        self.record_status = False
        self.prompt.print("Stopping data record!")

    ##############################################################################
    ####      RECORDING FUNCTIONS        #########################################
    ##############################################################################

    def set_record_directory(self):
        self.data_dir = filedialog.askdirectory()
        self.lbl_data_directory.config(text=self.data_dir)

    # TODO: this function needs to know if we want serial data to base our timing off that value (record samples at each UART output)
    def set_record_speed(self):
        # changes the recording speed based on recording speed GUI element
        def parse_time_to_seconds(time_str):
            """Convert a time string to seconds.

            Args:
                time_str (str): Time string to convert. Should end with 's', 'm', or 'h'.

            Returns:
                int: Time in seconds.
            """
            if not isinstance(time_str, str):
                raise ValueError("Input should be a string.")

            time_str = time_str.strip().lower()
            if time_str.endswith('s'):
                return int(time_str[:-1])
            elif time_str.endswith('m'):
                return int(time_str[:-1]) * 60
            elif time_str.endswith('h'):
                return int(time_str[:-1]) * 3600
            else:
                raise ValueError("Time string should end with 's', 'm', or 'h'.")

        self.record_speed = parse_time_to_seconds(self.RecSpdVal.get())

    def get_record_config(self):
        self.record_config = {
            "use_ser": self.var_use_ser.get(),
            "use_dmm": self.var_use_dmm.get(),
            "use_ps": self.var_use_ps.get(),
            "ps_channel": 1,
        }

    def organize_record_params(self):
        # FILENAME SETUP
        self.recName = 'AREC_' + strftime('%Y%m%d%H%M%S',localtime())
        file_str_ext = self.output_file_name.get("1.0", "end").strip("\n")
        if file_str_ext != "":
            self.recName += "_" + file_str_ext
            self.prompt.print(f"Using filename extension: {file_str_ext}")
        self.recName += ".csv"
        self.prompt.print(f"Starting recording at: {self.data_dir}{self.recName}")

        # CALL HELPER FUNCTIONS
        self.set_record_speed()
        self.get_record_config()

        # SETUP CSV HEADER PARAMETERS
        headers = ["Time"]

        # Serial/user-entered metadata (if selected)
        if self.record_config["use_ser"]:
            raw = self.serial_log_params.get("1.0", "end").strip()
            if not raw:
                guih.alert_user("No serial params entered", "The serial parameters are blank", "warning")

            # Split by commas; do not tolerate trailing commas or empty segments
            parts = raw.split(",")
            # Strip whitespace from each part
            parts = [p.strip() for p in parts]

            # Check for empty entries (e.g., double commas or leading/trailing commas)
            if any(p == "" for p in parts):
                guih.alert_user("Invalid serial format", "Make sure there are no consecutive commas and no leading/trailing commas.\n"
                    "Example: SN,BoardRev,FW", "error")

            headers += parts

        # DMM selected?
        if self.record_config["use_dmm"]:
            # dmm_params = ["DMM_Range", "DMM_Func1", "DMM_Meas1"]
            dmm_params = ["DMM_Meas1"]
            headers += dmm_params

        # Power Supply selected?
        if self.record_config["use_ps"]:
            ps_params = ["PS_Vset1", "PS_Vmeas1", "PS_Imeas1"]

            if self.cc.ps.channel_count > 1:
                    res = guih.promptYesNo("Use all power supply channels?",
                                           f"Power supply has {self.cc.ps.channel_count} channels, use 2 of them?")
                    if res:
                        ps_params += ["PS_Vset2", "PS_Vmeas2", "PS_Imeas2"]
                        self.record_config["ps_channels"] = 2

            headers += ps_params

        # SETUP CSV
        self.csvh = CSVHelper(self.data_dir + self.recName)
        self.csvh.initialize_file(headers)

    def thread_record(self):
        while self.record_status:
            # Build a row of data based on what user wants
            row = {"Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}

            # Serial data if requested
            if self.record_config.get("use_ser", False):
                row["SerialData"] = self.cc.ser.read_line()

            # DMM data if requested
            if self.record_config.get("use_dmm", False):
                row["DMM_Meas1"] = self.cc.dmm.read_value()

            # Power Supply data if requested
            if self.record_config.get("use_ps", False):
                row["PS_Vset1"] = self.cc.ps.get_set_voltage(1)
                row["PS_Vmeas1"] = self.cc.ps.get_voltage(1)
                row["PS_Imeas1"] = self.cc.ps.get_current(1)
                if self.record_config["ps_channels"] == 2:
                    row["PS_Vset2"] = self.cc.ps.get_set_voltage(2)
                    row["PS_Vmeas2"] = self.cc.ps.get_set_voltage(2)
                    row["PS_Imeas1"] = self.cc.ps.get_current(1)

            # Update record counter and UI
            self.recCnt += 1
            self.labelRNums.config(text=f'#{self.recCnt:7d}')

            # Append to CSV
            self.csvh.add_row_from_dict(row)

            # Wait for next sample
            time.sleep(self.record_speed)



    # def analyze_file(self, filename):
    #     print("Analyzing file")
    #     file_path = self.basefilepath + self.data_folder + filename
    #
    #     # imu_data = processor.load_csv(file_path)
    #     # if imu_data is None:
    #     #     gui_helper.alert_user("Something wrong with data!",
    #     #                           "Couldn't load data, something wrong",
    #     #                           kind="error")
    #     #     return False
    #
    #     imu_stats = imu_analysis.analyze_imu(file_path)
    #     # output_frame = tk.Frame(self.master)
    #     # output_frame.grid(row=4, column=0)
    #     text_box = tk.Text(self.fr_analysis, height=17)
    #     text_box.grid(row=5, column=0, padx=15, pady=15)
    #
    #     # Add the dictionary contents to the Text widget
    #     for key, value in imu_stats.items():
    #         text_box.insert(tk.END, f"{key}: {value}\n")
    #     return True



    # def graph_file(self, filename):
    #     print("Graphing file")
    #
    #     file_path = self.basefilepath + self.data_folder + filename
    #     imu_data = processor.load_csv(file_path)
    #     if imu_data is None:
    #         gui_helper.alert_user("Something wrong with IMU data!",
    #                               "Couldn't load data, something wrong",
    #                               kind="error")
    #         return False

