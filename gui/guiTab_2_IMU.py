
# import needed packages
import tkinter as tk
from tkinter import *
from tkinter import ttk
import tkinter.filedialog as tkfd
import threading
import os
from serial.tools import list_ports

import matplotlib.pyplot as plt  # import matplotlib library
from drawnow import *

# import user defined modules
from common import SerialReader
from common.SerialReader import SerialReader
from gui import gui_helper as guih
from imu import imu_analysis


class tabIMU:
    def __init__(self, master, basefilepath):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.frame.grid(row=0, column=0)
        self.basefilepath = basefilepath
        self.data_folder = "/data/imu_data"

        # print welcome text
        l1 = ttk.Label(self.frame, text="IMU Control Center", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0)

        # init frames within tab
        self.fr_add_data = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_add_data.grid(row=1, column=0, padx=30, pady=12)
        self.fr_analysis = tk.Frame(self.frame, bg="#0f0dba")
        self.fr_analysis.grid(row=2, column=0, padx=30, pady=12)
        self.fr_prompt = tk.Frame(self.frame, bg="gray")
        self.fr_prompt.grid(row=10, column=0, padx=30, pady=12)

        # add some other variables
        self.ser_obj = None

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 2 content")
        self.init_fr_prompt()
        self.init_fr_data_record()
        self.init_fr_analysis()

    def init_fr_prompt(self):
        # set up text box for user communication
        Label(self.fr_prompt, text="Console Output").grid(row=0, column=0, pady=10)
        self.prompt = Text(self.fr_prompt, padx=10, pady=10, height=20, width=100)
        self.prompt.grid(row=1, column=0, padx=10, pady=10)

    def init_fr_data_record(self):
        self.com_drop_down = 0

        # COM port selection
        def refresh_ports():
            com_ports = [port.device for port in list_ports.comports()]
            # ports_var.set(com_ports)
            # set up user inputs for statement (year and month)
            self.com_dropdown = guih.generate_drop_down(
                self.fr_add_data,
                [port.device for port in list_ports.comports()]
            )
            self.com_dropdown[0].grid(row=1, column=2, columnspan=2, padx=3, pady=10)

        # Button to refresh the list of COM ports
        refresh_button = tk.Button(self.fr_add_data, text="Refresh Ports",
                                   command=refresh_ports,
                                   bg="green", fg="white")
        refresh_button.grid(row=1, column=3, columnspan=2, pady=10)

        # Initial port list
        refresh_ports()

        # add output file name box
        Label(self.fr_add_data, text="Output file name").grid(row=2, column=1, padx=5, pady=5)
        self.output_file_name = Text(self.fr_add_data, height=2, width=20)
        self.output_file_name.grid(row=2, column=2)

        # set up button START recording
        btn_start_entry = Button(self.fr_add_data, text="Start Record",
                                 command=lambda: threading.Thread(target=self.start_record).start(),
                                 bg="green", fg="white", height=2, width=20)
        btn_start_entry.grid(row=3, column=2, padx=15, pady=22)  # place 'Add Category' button

        # set up button STOP recording
        btn_stop_entry = Button(self.fr_add_data, text="Stop Record",
                                command=lambda: threading.Thread(target=self.stop_record).start(),
                                bg="red", fg="white", height=2, width=20)
        btn_stop_entry.grid(row=3, column=3, padx=15, pady=22)  # place 'Add Category' button

        # set up button START live GRAPH
        btn_stop_entry = Button(self.fr_add_data, text="Live Graph",
                                command=lambda: threading.Thread(target=self.live_graph).start(),
                                bg="blue", fg="gold", height=2, width=20)
        btn_stop_entry.grid(row=4, column=3, pady=12)  # place 'Add Category' button

    def init_fr_analysis(self):
        # Create a StringVar to hold the selected file path
        selected_file = tk.StringVar(self.fr_analysis)

        def get_file_list(directory):
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            return files

        file_list = get_file_list(self.basefilepath + self.data_folder)
        # Create an OptionMenu with a button to open the file dialog
        file_dropdown = tk.OptionMenu(self.fr_analysis, selected_file, *file_list)
        file_dropdown.grid(row=0, column=0, pady=10)

        def refresh_file_list():
            new_file_list = get_file_list(self.basefilepath + self.data_folder)
            new_file_dropdown = tk.OptionMenu(self.fr_analysis, selected_file, *new_file_list)
            new_file_dropdown.grid(row=0, column=0, pady=10)

        refresh_file_btn = Button(self.fr_analysis, text="Refresh files",
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

    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    # add_category_gui: attempts to add a category to the SQL database
    def start_record(self):
        error_flag = 0
        out_file_name_obj = self.output_file_name
        serial_port = self.com_dropdown[1].get()

        file_str_ext = out_file_name_obj.get("1.0", "end").strip(
            "\n")  # I THINK THIS CATEGORY NAME IS GETTING STRIPPED WRONG
        if file_str_ext == "":
            gui_helper.gui_print(self.frame, self.prompt, "Detected blank file name, going to use default")
            file_str_ext = None
        else:
            gui_helper.gui_print(self.frame, self.prompt, f"Using filename extension: {file_str_ext}")

        # init serial object and start data processing
        error_flag |= self.serial_init(serial_port)
        error_flag |= self.ser_obj.init_data_process(self.basefilepath + self.data_folder, filename_ext=file_str_ext)

        if error_flag:
            gui_helper.gui_print(self.frame, self.prompt, "Something went wrong starting data record")

    def serial_init(self, serial_port):
        gui_helper.gui_print(self.frame, self.prompt, f"Init with port: {serial_port}")
        self.ser_obj = SerialReader(serial_port)
        return True

    def stop_record(self):
        gui_helper.gui_print(self.frame, self.prompt, "Stopping data record")
        self.ser_obj.stop_data_process()
        pass

    def live_graph(self):
        error_flag = 0
        serial_port = self.com_dropdown[1].get()
        error_flag |= self.serial_init(serial_port)

        gui_helper.gui_print(self.frame, self.prompt, f"Starting live graph with: {serial_port}")
        while True:
            data = self.ser_obj.get_data()
            print(f"gui got this data: {data}")
            if data is not None:
                self.ser_obj.live_plot(data)

    def analyze_file(self, filename):
        print("Analyzing file")
        file_path = self.basefilepath + self.data_folder + filename

        # imu_data = processor.load_csv(file_path)
        # if imu_data is None:
        #     gui_helper.alert_user("Something wrong with data!",
        #                           "Couldn't load data, something wrong",
        #                           kind="error")
        #     return False

        imu_stats = imu_analysis.analyze_imu(file_path)
        # output_frame = tk.Frame(self.master)
        # output_frame.grid(row=4, column=0)
        text_box = tk.Text(self.fr_analysis, height=17)
        text_box.grid(row=5, column=0, padx=15, pady=15)

        # Add the dictionary contents to the Text widget
        for key, value in imu_stats.items():
            text_box.insert(tk.END, f"{key}: {value}\n")
        return True


    def graph_file(self, filename):
        print("Graphing file")

        file_path = self.basefilepath + self.data_folder + filename
        imu_data = processor.load_csv(file_path)
        if imu_data is None:
            gui_helper.alert_user("Something wrong with IMU data!",
                                  "Couldn't load data, something wrong",
                                  kind="error")
            return False


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    # add_category_gui: attempts to add a category to the SQL database
    # def analyze_file(self, filename):
    #     print("Analyzing file")
    #     afe_data = processor.load_csv(self.basefilepath + "/data/" + filename)
    #     if afe_data is None:
    #         guih.alert_user("Something wrong with data!",
    #                               "Couldn't load data, something wrong",
    #                         kind="error")
    #         return False
    #     afe_stats = afe_analysis.analyze_afe(afe_data)
    #     # output_frame = tk.Frame(self.master)
    #     # output_frame.grid(row=4, column=0)
    #     text_box = tk.Text(self.fr_analysis, height=17)
    #     text_box.grid(row=5, column=0, padx=15, pady=15)
    #
    #     # Add the dictionary contents to the Text widget
    #     for key, value in afe_stats.items():
    #         text_box.insert(tk.END, f"{key}: {value}\n")
    #     return True