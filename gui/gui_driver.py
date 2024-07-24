"""
@file     gui_driver.opy
@author   Anders Bandt
@date     April 2024
@brief    critical GUI code to launch Tkinter notebook
"""


# import needed packages
import tkinter as tk
from tkinter import ttk
import sv_ttk
import os
import time

# import ClassController
from class_controller import ClassController
from EEequipment.usbrelay import usbrelay_controller

# import tab classes
from gui.guiTab_parent import ThemedApp
from gui import guiTab_1_mainDashboard
from gui import guiTab_2_IMU
from gui import guiTab_3_DMM
from gui import guiTab_4_XDS110
from gui import guiTab_5_USB
from gui import guiTab_6_PS


# TODO: an alternative method to threads. Could possibly be better for GUI updates? Check performance somehow
# elapsed = (perf_counter_ns() - self.ProgStart) // 1000000  # time in ms since start
# time2sleep = 1000 - (elapsed % 1000)
# self.frame.after(time2sleep, self.PollMiniBM)


class MainApplication(ThemedApp):
    def __init__(self, window, height, width, theme_file): # TODO: consider changing "window" to "root" (seems proper)
        super().__init__(window, theme_file)

        self.nb = ttk.Notebook(window, height=height, width=width)
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.basefilepath = os.getcwd()

        self.controller = ClassController()

        usb_dev = usbrelay_controller.find()
        self.controller.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )

        self.tab1 = None
        self.tab2 = None
        self.tab3 = None
        self.tab4 = None
        self.tab5 = None
        self.tab6 = None
        self.setTabs()

    # set up tab control
    def setTabs(self):
        print("Creating tab nav bar and initializing tab content")
        self.tab1 = guiTab_1_mainDashboard.tabMainDashboard(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab2 = guiTab_2_IMU.tabIMU(self.nb, self.basefilepath)
        self.tab3 = guiTab_3_DMM.tabDMM(self.nb, self.controller, self.basefilepath)
        self.tab4 = guiTab_4_XDS110.tabXDS110(self.nb, self.controller, self.basefilepath)
        self.tab5 = guiTab_5_USB.tabUSB(self.nb, self.controller, self.basefilepath)
        self.tab6 = guiTab_6_PS.tabPS(self.nb, self.controller, self.basefilepath)

        self.nb.add(self.tab1.frame, text="MAIN")
        self.nb.add(self.tab2.frame, text="IMU Analysis")
        self.nb.add(self.tab3.frame, text="DMM Control")
        self.nb.add(self.tab4.frame, text="XDS110 JTAG")
        self.nb.add(self.tab5.frame, text="USB COMM")
        self.nb.add(self.tab6.frame, text="PS Control")

        self.nb.grid(column=0, row=0)
        return True

    def on_tab_changed(self, event):
        selected_tab = event.widget.tab(event.widget.select(), "text")
        print(selected_tab)
        if selected_tab == "MAIN":
            guiTab_1_mainDashboard.tabMainDashboard.gui_refresh_relay_state(self.tab1, "auto")
        elif selected_tab == "PS Control":
            guiTab_6_PS.tabPS.gui_refresh_channel_state(self.tab6)

###########################################################
######################### MAIN ############################
###########################################################

# main function
def main():
    print("Executing main function of gui_driver.py")

    # setup window
    window = tk.Tk()

    window.title("WWD GUI API")
    window.geometry('1280x900')

    # sv_ttk.set_theme("dark")

    ### add window Style
    # style = ttk.Style(window)
    # style.configure('TNotebook.Tab', background="Red")
    # style.map("TNotebook", background=[("selected", "red")])
    # style.theme_use("clam") # options are: "default", "alt", "classic", "clam"

    # Configure styles for notebook tabs
    # style.configure('TNotebook.Tab',
    #                 background="#FF6347",  # Tomato red background
    #                 foreground="#000000",  # Black text
    #                 font=('Arial', 12, 'bold'),  # Font family, size, and style
    #                 padding=(10, 5))  # Padding around the text
    # style.map("TNotebook.Tab",
    #           background=[("selected", "red")],
    #           foreground=[("selected", "white")])

    # place main app
    MainApplication(window, 1800, 1800, "config/darcula.json")

    # run application
    window.mainloop()

    print("TKINTER is shutting down!")
    print("Anders you should put some graceful exit stuff here!")
    # TODO: now that I'm adding all these pieces of test equipment I need some way to have a "graceful exit" (shutting off all supplies, etc)
