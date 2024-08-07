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



class MainApplication(ThemedApp):
    def __init__(self, window, height, width, theme_file):
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

    def setTabs(self):
        print("Creating tab nav bar and initializing tab content")
        self.tab1 = guiTab_1_mainDashboard.tabMainDashboard(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab2 = guiTab_2_IMU.tabIMU(self.nb, self.basefilepath, "config/darcula.json")
        self.tab3 = guiTab_3_DMM.tabDMM(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab4 = guiTab_4_XDS110.tabXDS110(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab5 = guiTab_5_USB.tabUSB(self.nb, self.controller, self.basefilepath, "config/darcula.json")
        self.tab6 = guiTab_6_PS.tabPS(self.nb, self.controller, self.basefilepath, "config/darcula.json")

        self.nb.add(self.tab1, text="MAIN")
        self.nb.add(self.tab2, text="IMU Analysis")
        self.nb.add(self.tab3, text="DMM Control")
        self.nb.add(self.tab4, text="XDS110 JTAG")
        self.nb.add(self.tab5, text="USB COMM")
        self.nb.add(self.tab6, text="PS Control")

        self.nb.grid(column=0, row=0)
        return True

    def on_tab_changed(self, event):
        selected_tab = event.widget.tab(event.widget.select(), "text")
        if selected_tab == "MAIN":
            guiTab_1_mainDashboard.tabMainDashboard.gui_refresh_relay_state(self.tab1, "auto")
        elif selected_tab == "PS Control":
            guiTab_6_PS.tabPS.gui_refresh(self.tab6)


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

    # place main app
    app = MainApplication(window, 1800, 1800, "config/darcula.json")

    # run application
    window.mainloop()

    # perform shutdown activities
    print("TKINTER is shutting down!")
    if app.controller.ps is not None:
        try:
            app.controller.ps.output_off(1)
            app.controller.ps.output_off(2)
        except Exception as e:
            raise e

    # close any open serial ports
    # TODO: none of these can properly close because there is all sorts of runtime exceptions since mainloop() has terminated
    app.tab3.port_close()
    app.tab5.port_close()
    app.tab6.port_close()


