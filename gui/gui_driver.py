"""
@file     gui_driver.opy
@author   Anders Bandt
@date     April 2024
@brief    critical GUI code to launch Tkinter notebook
"""

# import needed packages
import tkinter as tk
from tkinter import ttk
import os
import time

# import ClassController
from class_controller import ClassController
from EEequipment.usbrelay import usbrelay_controller

# import tab classes
from gui.guiTab_parent import ThemedApp
from gui import guiTab_1_mainDashboard
from gui import guiTab_2_LOG
from gui import guiTab_3_DMM
from gui import guiTab_4_XDS110
from gui import guiTab_5_USB
from gui import guiTab_6_PS
from gui import guiTab_7_ATE


# TODO: (small) change all the class names to CamelCase with TabXxx
class MainApplication(ThemedApp):
    def __init__(self, window, height, width, theme_file, autoconnect):
        super().__init__(window, theme_file)
        self.autoconnect = autoconnect
        self.nb = ttk.Notebook(window, height=height, width=width)
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.basefilepath = os.getcwd()
        self.controller = ClassController()

        usb_dev = usbrelay_controller.find()
        self.controller.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        time.sleep(2)

        self.tab1 = None
        self.tab2 = None
        self.tab3 = None
        self.tab4 = None
        self.tab5 = None
        self.tab6 = None
        self.tab7 = None
        self.tab_names = []
        self.setTabs()

    def setTabs(self):
        print("Creating tab nav bar and initializing tab content")
        self.tab1 = guiTab_1_mainDashboard.tabMainDashboard(self.nb, self.controller, self.basefilepath,
                                                            "config/darcula.json", self.autoconnect)
        self.tab2 = guiTab_2_LOG.TabLog(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab3 = guiTab_3_DMM.tabDMM(self.nb, self.controller, self.basefilepath, "config/darcula.json", self.autoconnect)
        self.tab4 = guiTab_4_XDS110.tabXDS110(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab5 = guiTab_5_USB.tabUSB(self.nb, self.controller, self.basefilepath, "config/darcula.json", self.autoconnect)
        self.tab6 = guiTab_6_PS.tabPS(self.nb, self.controller, self.basefilepath, "config/darcula.json", self.autoconnect)
        # self.tab7 = guiTab_7_ATE.tabATE(self.nb, self.controller, self.basefilepath, "config/darcula.json", self.autoconnect)

        # Define an array of tab names
        self.tab_names = ["MAIN", "Logger Utility", "DMM Control", "XDS110 JTAG", "USB COMM", "PS Control"]
        tabs = [self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6]

        # Add tabs dynamically using a loop
        for tab, name in zip(tabs, self.tab_names):
            self.nb.add(tab, text=name)

        self.nb.grid(column=0, row=0)
        return True

    def on_tab_changed(self, event):
        selected_tab = event.widget.tab(event.widget.select(), "text")
        if selected_tab == self.tab_names[0]:
            guiTab_1_mainDashboard.tabMainDashboard.gui_refresh(self.tab1, "auto")
        if selected_tab == self.tab_names[1]:
            guiTab_2_LOG.TabLog.gui_refresh(self.tab2, "auto")
        if selected_tab == self.tab_names[2]:
            guiTab_3_DMM.tabDMM.gui_refresh(self.tab3, "auto")
        elif selected_tab == self.tab_names[5]:
            guiTab_6_PS.tabPS.gui_refresh(self.tab6, "auto")


###########################################################
######################### MAIN ############################
###########################################################

# main function
def main(autoconnect):
    print("Executing main function of gui_driver.py")

    # setup window
    window = tk.Tk()
    window.title("WWD GUI API")

    w = 1280  # width for the Tk root
    h = 900  # height for the Tk root
    # get screen width and height
    ws = window.winfo_screenwidth()  # width of the screen
    hs = window.winfo_screenheight()  # height of the screen
    # set the dimensions of the screen and where is it placed
    x = (ws / 2) - (w / 4)
    y = 70
    window.geometry('%dx%d+%d+%d' % (w, h, x, y))

    # place main app
    app = MainApplication(window,
                          1800,
                          1800,
                          "config/darcula.json",
                          autoconnect)

    # run application
    window.mainloop()

    #### USER HAS CLOSED APPLICATION WHEN CODE REACHES PAST THIS POINT ####

    # perform shutdown activities
    print("TKINTER is shutting down!")
    if app.controller.ps is not None:
        app.controller.ps.output_off(1)
        app.controller.ps.output_off(2)
        app.controller.ps.disconnect()

    if app.controller.relay is not None:
        app.controller.relay.open_all()

    return
