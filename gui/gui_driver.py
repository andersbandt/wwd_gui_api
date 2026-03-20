"""Creates the Tkinter window and launches the main notebook interface."""


# import needed packages
import logging
import tkinter as tk
from tkinter import ttk
import os
import time

logger = logging.getLogger(__name__)

# import ClassController
from class_controller import ClassController
from EEequipment.usbrelay import usbrelay_controller
from EEequipment.TestEquipment import set_visa_backend

# import tab classes
from common import path_helper
from services.config_service import ConfigService
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

NUM_TABS = 10 # tag:HARDCODE



class MainApplication(ThemedApp):
    def __init__(self, window, height, width, theme_file, autoconnect, compact, config_svc):
        super().__init__(window, theme_file, compact=compact)
        self.autoconnect = autoconnect
        self.config_svc = config_svc
        self.nb = ttk.Notebook(window, height=height, width=width)
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.basefilepath = os.getcwd()
        self.controller = ClassController()
        self.controller.config_svc = config_svc

        try:  # NOTE: I think I get weird libpath / StopIteration things if I don't have this thing properly installed
            usb_dev = usbrelay_controller.find()
        except Exception as e:
            logger.warning(f"Can't locate USB_RELAY because of {e}")
            usb_dev = None
        self.controller.set_relay(
            usbrelay_controller.USBRelayController(usb_dev)
        )
        time.sleep(2)

        self.tab_names = []
        self.setTabs()

    def setTabs(self):
        logger.info("Creating tab nav bar and initializing tab content")

        # setup autoconnect array
        if self.autoconnect:
            autoconnect = self.config_svc.get_autoconnect_flags()
        else:
            autoconnect = [False] * (NUM_TABS + 1)


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

        self.nb.grid(column=0, row=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.root.bind("<Shift-Right>", lambda e: self._shift_tab(1))
        self.root.bind("<Shift-Left>", lambda e: self._shift_tab(-1))

        return True

    def _shift_tab(self, direction):
        tabs = self.nb.tabs()
        current = self.nb.index(self.nb.select())
        next_idx = (current + direction) % len(tabs)
        self.nb.select(next_idx)

    def on_tab_changed(self, event):
        # Skip gui_refresh during active recording to prevent crashes
        if self.controller.recording:
            logger.debug("Skipping gui_refresh: recording in progress")
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
    logger.info("Executing main function of gui_driver.py")

    # Create centralized config service and wire into path_helper
    config_svc = ConfigService()
    path_helper.init_config_service(config_svc)

    # Configure PyVISA backend from master.ini before any instrument connections
    set_visa_backend(config_svc.get_visa_backend())

    # tag:HARDCODE
    desired_w = 1350
    desired_h = 900
    margin_w = 50
    margin_h = 125

    # setup window
    window = tk.Tk()
    window.title("WWD GUI API")

    # Set window/taskbar icon (works on Linux and Windows; Tk 8.6+ PNG support)
    try:
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'icon.png')
        _icon_img = tk.PhotoImage(file=icon_path)
        window.iconphoto(True, _icon_img)
    except Exception as e:
        logger.warning(f"Could not load app icon: {e}")

    # Get screen size
    ws = window.winfo_screenwidth()
    hs = window.winfo_screenheight()

    # Clamp desired size within screen (leave a margin for taskbar/titlebar)
    w = min(desired_w, max(300, ws - margin_w))
    h = min(desired_h, max(300, hs - margin_h))

    # dynamic sizing check
    if force_compact:
        compact = True
        logger.info("Using compact sizing (forced by command-line argument)")
    elif (w < 0.8*desired_w) or (h < 0.8*desired_h):
        compact = True
        logger.info("Using compact sizing (auto-detected from screen size)")
    else:
        logger.info("Using standard window size")
        compact = False

    # Center placement
    # x = (ws / 2) - (w / 4) # NOTE: I think this was when I wanted to be like 3/4 of the way right?
    x = 20
    y = 20

    window.geometry("%dx%d+%d+%d" % (w, h, x, y))

    # load theme configuration
    theme_file = config_svc.get_theme_file()

    # place main app
    app = MainApplication(window,
                          h,
                          w,
                          theme_file,
                          autoconnect,
                          compact,
                          config_svc)

    # run application
    window.mainloop()

    #### USER HAS CLOSED APPLICATION WHEN CODE REACHES PAST THIS POINT ####

    # perform shutdown activities
    logger.info("TKINTER is shutting down!")

    app.controller.shutdown()

    return
