
# import needed packages
import tkinter as tk
from tkinter import *
from tkinter import ttk
import threading
import os
from serial.tools import list_ports

import matplotlib.pyplot as plt  # import matplotlib library
from drawnow import *

# import user defined modules
from gui import gui_helper as guih
from analysis import afe_analysis


class tabMainDashboard:
    def __init__(self, master, basefilepath):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.frame.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text
        l1 = ttk.Label(self.frame, text="Welcome to the WWD program!!!!", style="BW.TLabel",
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
        print("Initializing tab 1 main dashboard")
        self.init_fr_prompt()
        self.init_fr_data_record()

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


    ##############################################################################
    ####      ACTION FUNCTIONS        ############################################
    ##############################################################################

    # add_category_gui: attempts to add a category to the SQL database
    def analyze_file(self, filename):
        print("Analyzing file")
        afe_data = processor.load_csv(self.basefilepath + "/data/" + filename)
        if afe_data is None:
            guih.alert_user("Something wrong with data!",
                                  "Couldn't load data, something wrong",
                            kind="error")
            return False
        afe_stats = afe_analysis.analyze_afe(afe_data)
        # output_frame = tk.Frame(self.master)
        # output_frame.grid(row=4, column=0)
        text_box = tk.Text(self.fr_analysis, height=17)
        text_box.grid(row=5, column=0, padx=15, pady=15)

        # Add the dictionary contents to the Text widget
        for key, value in afe_stats.items():
            text_box.insert(tk.END, f"{key}: {value}\n")
        return True


