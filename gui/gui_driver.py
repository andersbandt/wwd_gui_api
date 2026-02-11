"""Creates the Tkinter window and launches the main notebook interface."""


# import needed packages
import tkinter as tk
from tkinter import ttk
import os
import time
import configparser

from EEequipment.equipment_manager import COMMUNICATION_ERRORS
# import ClassController
from class_controller import ClassController
from EEequipment.usbrelay import usbrelay_controller

# import tab classes
from gui.gui_class import ThemedApp
from gui import guiTab_1_mainDashboard
from gui import guiTab_2_DMM
from gui import guiTab_3_XDS110
from gui import guiTab_4_USB
from gui import guiTab_5_PS
from gui import guiTab_6_FG
from gui import guiTab_7_ATE
from gui import guiTab_8_LOG
from gui import guiTab_9_GRAPH
from gui import guiTab_10_OSC


def parse_autoconnect_config():
    # initialize the config parser
    config_file_path = "config/master.ini" # tag:HARDCODE
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
    for i in range(1, 11): #tag:HARDCODE
        tmp = config["AUTOCONNECT"][f"tab_{i}"]
        if tmp.strip().upper() == "YES":
            autoconn_vars.append(True)
        else:
            autoconn_vars.append(False)
    return autoconn_vars


def parse_theme_config():
    """
    Parse the theme configuration from master.ini.

    Returns:
        str: Path to the theme file (e.g., "config/darcula.json")
    """
    config_file_path = "config/master.ini"
    default_theme = "config/darcula.json"

    if not os.path.exists(config_file_path):
        print(f"Configuration file {config_file_path} does not exist. Using default theme.")
        return default_theme

    config = configparser.ConfigParser()
    config.read(config_file_path)

    # Check if THEME section exists
    if "THEME" not in config:
        print("Missing [THEME] section in config. Using default theme.")
        return default_theme

    # Get theme_file setting
    theme_file = config["THEME"].get("theme_file", "darcula.json").strip()

    # Ensure it has the config/ prefix if not already present
    if not theme_file.startswith("config/"):
        theme_file = f"config/{theme_file}"

    # Verify the theme file exists
    if not os.path.exists(theme_file):
        print(f"Theme file {theme_file} does not exist. Using default theme.")
        return default_theme

    print(f"Using theme: {theme_file}")
    return theme_file


class MainApplication(ThemedApp):
    def __init__(self, window, height, width, theme_file, autoconnect, compact):
        super().__init__(window, theme_file, compact=compact)
        self.autoconnect = autoconnect
        self.nb = ttk.Notebook(window, height=height, width=width)
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.basefilepath = os.getcwd()
        self.controller = ClassController()

        try:  # NOTE: I think I get weird libpath / StopIteration things if I don't have this thing properly installed
            usb_dev = usbrelay_controller.find()
        except Exception as e:
            print(f"Can't locate USB_RELAY because of {e}")
            usb_dev = None
        self.controller.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        time.sleep(2)

        self.tab_names = []
        self.setTabs()

    def setTabs(self):
        print("Creating tab nav bar and initializing tab content")

        # setup autoconnect array
        if self.autoconnect:
            autoconnect = parse_autoconnect_config()
        else:
            autoconnect = [False for i in range(11)] # tag:HARDCODE (should be same in as one in `parse_autoconnect_config`


        # create Tab objects
        self.tab1 = guiTab_1_mainDashboard.TabMainDashboard(self.nb, self.controller, self.basefilepath,self.theme_config, autoconnect[0])
        self.tab2 = guiTab_2_DMM.TabDMM(self.nb, self.controller, self.basefilepath, self.theme_config, autoconnect[1])
        self.tab3 = guiTab_3_XDS110.tabXDS110(self.nb, self.controller, self.basefilepath, self.theme_config)
        self.tab4 = guiTab_4_USB.TabUSB(self.nb, self.controller, self.basefilepath, self.theme_config, autoconnect[3])
        self.tab5 = guiTab_5_PS.TabPS(self.nb, self.controller, self.basefilepath, self.theme_config, autoconnect[4])
        self.tab6 = guiTab_6_FG.TabFG(self.nb, self.controller, self.basefilepath, self.theme_config, autoconnect[5])
        self.tab7 = guiTab_7_ATE.TabATE(self.nb, self.controller, self.basefilepath, self.theme_config, autoconnect[6])
        self.tab8 = guiTab_8_LOG.TabLog(self.nb, self.controller, self.basefilepath, self.theme_config)
        self.tab9 = guiTab_9_GRAPH.TabGraph(self.nb, self.controller, self.basefilepath, self.theme_config)
        self.tab10 = guiTab_10_OSC.TabOSC(self.nb, self.controller, self.basefilepath, self.theme_config, autoconnect[9])

        # Define an array of tab names
        self.tab_names = ["MAIN", "DMM Control", "XDS110 JTAG", "USB COMM", "PS Control", "FG Control", "ATE", "Logger", "GRAPH", "OSC Control"]
        tabs = [self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6, self.tab7, self.tab8, self.tab9, self.tab10]

        # Add tabs dynamically using a loop
        for tab, name in zip(tabs, self.tab_names):
            self.nb.add(tab, text=name)

        self.nb.grid(column=0, row=0)
        return True

    def on_tab_changed(self, event):
        # Skip gui_refresh during active recording to prevent crashes
        if self.controller.recording:
            print("Skipping gui_refresh: recording in progress")
            return

        selected_tab = event.widget.tab(event.widget.select(), "text")
        if selected_tab == self.tab_names[0]:
            guiTab_1_mainDashboard.TabMainDashboard.gui_refresh(self.tab1, "auto")
        elif selected_tab == self.tab_names[1]:
            guiTab_2_DMM.TabDMM.gui_refresh(self.tab2, "auto")
        elif selected_tab == self.tab_names[3]:
            guiTab_4_USB.TabUSB.gui_refresh(self.tab4, "auto")
        elif selected_tab == self.tab_names[4]:
            guiTab_5_PS.TabPS.gui_refresh(self.tab5, "auto")
        elif selected_tab == self.tab_names[5]:
            guiTab_6_FG.TabFG.gui_refresh(self.tab6, "auto")
        elif selected_tab == self.tab_names[6]:
            guiTab_7_ATE.TabATE.gui_refresh(self.tab7, "auto")
        elif selected_tab == self.tab_names[7]:
            guiTab_8_LOG.TabLog.gui_refresh(self.tab8, "auto")
        elif selected_tab == self.tab_names[9]:
            guiTab_10_OSC.TabOSC.gui_refresh(self.tab10, "auto")


###########################################################
######################### MAIN ############################
###########################################################

# main function
def main(autoconnect, force_compact=False):
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
    ws = window.winfo_screenwidth()
    hs = window.winfo_screenheight()

    # Clamp desired size within screen (leave a margin for taskbar/titlebar)
    w = min(desired_w, max(300, ws - margin_w))
    h = min(desired_h, max(300, hs - margin_h))

    # dynamic sizing check
    if force_compact:
        compact = True
        print("Using compact sizing (forced by command-line argument)")
    elif (w < 0.8*desired_w) or (h < 0.8*desired_h):
        compact = True
        print("Using compact sizing (auto-detected from screen size)")
    else:
        print("Using standard window size")
        compact = False

    # Center placement
    # x = (ws / 2) - (w / 4) # NOTE: I think this was when I wanted to be like 3/4 of the way right?
    x = 20
    y = 20


    window.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # load theme configuration
    theme_file = parse_theme_config()

    # place main app
    app = MainApplication(window,
                          h,
                          w,
                          theme_file,
                          autoconnect,
                          compact)

    # run application
    window.mainloop()

    #### USER HAS CLOSED APPLICATION WHEN CODE REACHES PAST THIS POINT ####

    # perform shutdown activities
    print("TKINTER is shutting down!")

    # disconnect all active connections in `class_controller.py`
    if app.controller.ps is not None:
        print("Disconnect from power supply (and turning outputs off)")
        try:
            app.controller.ps.output_off(1)
            app.controller.ps.output_off(2)
        except COMMUNICATION_ERRORS:
            print("Failed to turn off power supply due to IO error")
        try:
            app.controller.ps.disconnect()
        except COMMUNICATION_ERRORS as e:
            print("Failed to disconnect from power supply due to IO error (see below line)")
            print(e)

    if app.controller.dmm is not None:
        print("Disconnect from DMM")
        app.controller.dmm.disconnect()

    if app.controller.fg is not None:
        print("Disconnect from FG")
        app.controller.fg.disconnect()

    if app.controller.osc is not None:
        print("Disconnect from OSC")
        try:
            app.controller.osc.disconnect()
        except COMMUNICATION_ERRORS as e:
            print(f"Failed to disconnect from OSC: {e}")

    if app.controller.relay is not None:
        app.controller.relay.open_all()

    return
