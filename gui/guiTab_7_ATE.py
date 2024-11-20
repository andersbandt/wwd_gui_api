"""
@file     guiTab_7_ATE.py
@author   Anders Bandt
@date     November 2024
@brief    control devices to assist in ATE control
"""

# import needed packages
import tkinter as tk
from tkinter import ttk

# import uGUI modules
from gui import gui_helper as guih
from gui import gui_class as guic
from gui.guiTab_parent import ThemedFrame



class tabATE(ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_file, autoconnect):
        super().__init__(master, theme_file)
        self.master = master
        self.cc = class_controller
        self.grid(row=0, column=0)
        self.basefilepath = basefilepath

        # serial Object
        self.ser_obj = None

        # print welcome text_data
        l1 = ttk.Label(self, text="ATE Control", style="BW.TLabel",
                       font=("Arial", 24))
        l1.grid(row=0, column=0, columnspan=2)

        # initialize tab content
        self.initTabContent()

    def initTabContent(self):
        print("Initializing tab 7 (ATE) content")
        return True





