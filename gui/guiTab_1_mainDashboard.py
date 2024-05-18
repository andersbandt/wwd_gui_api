
# import needed packages
import tkinter as tk
from tkinter import *
from tkinter import ttk


# import user defined modules
from gui import gui_helper as guih
from gui import gui_class as guic
from analysis import afe_analysis


class tabMainDashboard:
    def __init__(self, master, class_controller, basefilepath):
        self.master = master
        self.cc = class_controller
        self.frame = tk.Frame(self.master)
        self.frame.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # print welcome text
        l1 = ttk.Label(self.frame, text="Welcome to the WWD program!!!!", style="BW.TLabel",
                       font=("Arial", 16))
        l1.grid(column=0, row=0, columnspan=2)

        # init frames within tab
        self.fr_main_status = tk.Frame(self.frame, bg="#00bcd4")
        self.fr_main_status.grid(row=1, column=0, padx=30, pady=12)

        # add some other variables
        self.canvas1 = tk.Canvas(self.fr_main_status, width=50, height=50)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 1 main dashboard")
        self.init_fr_main_status()



    def init_fr_main_status(self):
        fr_m = self.fr_main_status
        self.canvas1.grid(row=1, column=2, padx=15, pady=22)

        # RELAY STATUS INDICATOR
        Label(fr_m, text="Relay status").grid(row=1, column=1, padx=5, pady=5)

        my_oval = self.canvas1.create_oval(50 * .25, 50 * .25, 50 * .75, 50 * 0.75)  # x0, y0, x1, y1
        if self.cc.relay is not None:
            self.canvas1.itemconfig(my_oval, fill="green")  # Fill the circle with GREEN
            return True
        else:
            self.canvas1.itemconfig(my_oval, fill="red")  # Fill the circle with RED
            return False

        Label(fr_m, text="Relay config").grid(row=2, column=1, padx=5, pady=5)



