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
import configparser

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



def parse_autoconnect_config():
    # initialize the config parser
    config_file_path = "config/master.ini"
    if os.path.exists(config_file_path):
        config = configparser.ConfigParser()
        config.read(config_file_path)
    else:
        print(f"Configuration file {config_file_path} does not exist.")
        raise BaseException

    # Ensure the section and option exist
    if "AUTOCONNECT" not in config:
        raise KeyError("Missing [AUTOCONNECT] section in config.")

    # read in parameters from the config file
    autoconn_vars = []
    for i in range(1, 8):
        tmp = config["AUTOCONNECT"][f"tab_{i}"]
        if tmp.strip().upper() == "YES":
            autoconn_vars.append(True)
        else:
            autoconn_vars.append(False)
    return autoconn_vars



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

        # setup autoconnect array
        if self.autoconnect:
            autoconnect = parse_autoconnect_config()
        else:
            autoconnect = [False for i in range(8)]

        # create Tab objects
        self.tab1 = guiTab_1_mainDashboard.TabMainDashboard(self.nb, self.controller, self.basefilepath,"config/darcula.json", autoconnect[0])
        self.tab2 = guiTab_2_LOG.TabLog(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab3 = guiTab_3_DMM.TabDMM(self.nb, self.controller, self.basefilepath, "config/darcula.json", autoconnect[2])
        self.tab4 = guiTab_4_XDS110.tabXDS110(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab5 = guiTab_5_USB.TabUSB(self.nb, self.controller, self.basefilepath, "config/darcula.json", autoconnect[4])
        self.tab6 = guiTab_6_PS.TabPS(self.nb, self.controller, self.basefilepath, "config/darcula.json", autoconnect[5])
        self.tab7 = guiTab_7_ATE.TabATE(self.nb, self.controller, self.basefilepath, "config/darcula.json", autoconnect[6])

        # Define an array of tab names
        self.tab_names = ["MAIN", "Logger Utility", "DMM Control", "XDS110 JTAG", "USB COMM", "PS Control", "ATE"]
        tabs = [self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6, self.tab7]

        # Add tabs dynamically using a loop
        for tab, name in zip(tabs, self.tab_names):
            self.nb.add(tab, text=name)

        self.nb.grid(column=0, row=0)
        return True

    def on_tab_changed(self, event):
        selected_tab = event.widget.tab(event.widget.select(), "text")
        if selected_tab == self.tab_names[0]:
            guiTab_1_mainDashboard.TabMainDashboard.gui_refresh(self.tab1, "auto")
        elif selected_tab == self.tab_names[1]:
            guiTab_2_LOG.TabLog.gui_refresh(self.tab2, "auto")
        elif selected_tab == self.tab_names[2]:
            guiTab_3_DMM.TabDMM.gui_refresh(self.tab3, "auto")
        elif selected_tab == self.tab_names[3]:
            guiTab_5_USB.TabUSB.gui_refresh(self.tab5, "auto")
        elif selected_tab == self.tab_names[5]:
            guiTab_6_PS.TabPS.gui_refresh(self.tab6, "auto")
        elif selected_tab == self.tab_names[6]:
            guiTab_7_ATE.TabATE.gui_refresh(self.tab7, "auto")


###########################################################
######################### MAIN ############################
###########################################################

# main function
def main(autoconnect):
    print("Executing main function of gui_driver.py")

    # tag:HARDCODE
    desired_w = 1300
    desired_h = 900
    margin_w = 50
    margin_h = 125

    # setup window
    window = tk.Tk()
    window.title("WWD GUI API")

    # Get screen size
    # TODO: this could be a big ask ... but can I dynamically size elements if the screen size is small?
    #   bonus points if I can update the theme_config based on sizing
    ws = window.winfo_screenwidth()
    hs = window.winfo_screenheight()

    # Clamp desired size within screen (leave a margin for taskbar/titlebar)
    w = min(desired_w, max(300, ws - margin_w))
    h = min(desired_h, max(300, hs - margin_h))

    # Center placement
    x = (ws / 2) - (w / 4)
    y = 20

    window.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # place main app
    app = MainApplication(window,
                          h,
                          w,
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
