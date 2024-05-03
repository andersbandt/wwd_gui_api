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

# import tab classes
from gui import guiTab_1_mainDashboard
from gui import guiTab_2_IMU
from gui import guiTab_3_AFE
from gui import guiTab_4_XDS110
from gui import guiTab_5_USB


class MainApplication:
    def __init__(self, window, height, width):
        self.nb = ttk.Notebook(window, height=height, width=width)

        self.tab1 = None
        self.tab2 = None
        self.tab3 = None
        self.tab4 = None
        self.tab5 = None

        self.basefilepath = os.getcwd()

        self.setTabs()

    # set up tab control
    def setTabs(self):
        print("Creating tab nav bar and initializing tab content")
        self.tab1 = guiTab_1_mainDashboard.tabMainDashboard(self.nb, self.basefilepath)
        self.tab2 = guiTab_2_IMU.tabIMU(self.nb, self.basefilepath)
        self.tab3 = guiTab_3_AFE.tabAFE(self.nb, self.basefilepath)
        self.tab4 = guiTab_4_XDS110.tabXDS110(self.nb, self.basefilepath)
        self.tab5 = guiTab_5_USB.tabUSB(self.nb, self.basefilepath)

        self.nb.add(self.tab1.frame, text="MAIN")
        self.nb.add(self.tab2.frame, text="IMU Analysis")
        self.nb.add(self.tab3.frame, text="AFE Analysis")
        self.nb.add(self.tab4.frame, text="XDS110 JTAG")
        self.nb.add(self.tab5.frame, text="USB COMM")

        self.nb.grid(column=0, row=0)

        return True


###########################################################
######################### MAIN ############################
###########################################################

# main function
def main():
    print("Executing main function of gui_driver.py")

    # setup window
    window = tk.Tk()

    window.title("WWD GUI API")
    window.geometry('1350x950')


    sv_ttk.set_theme("dark")

    ### add window Style
    # 	theme options are
    # 	"default", "alt", "classic", "clam"
    # style = ttk.Style(window)
    # style.theme_use("")

    # style.configure('TNotebook.Tab', background="green3")
    # style.map("TNotebook", background=[("selected", "green3")])

    # style.configure('TNotebook.Tab', background="Red")
    # style.map("TNotebook", background=[("selected", "red")])

    # place main app
    MainApplication(window, 1800, 1800)

    # run application
    window.mainloop()

# dir = filedialog.askdirectory()



