"""Themed Tkinter GUI component classes and utilities."""


# import modules
import tkinter as tk
import xml.etree.ElementTree
from tkinter import ttk
from tkinter import Text, INSERT
from tkinter import scrolledtext

import json
import threading
import concurrent.futures
import copy
import xml.etree.ElementTree as ET
from datetime import datetime

# import user created modules
from gui import gui_helper as guih
from common import serial_api


def scale_theme(theme_cfg: dict, factor: float, *key_paths: str) -> dict:
    """
    Scale numeric values at given key paths by 'factor' and round to integers.

    Args:
        theme_cfg: The theme configuration dictionary
        factor: Scaling factor to apply
        *key_paths: Dot-notation paths to scale (e.g., "pad.xpad_s", "size.h_button")

    Returns:
        A new dictionary with scaled values

    Example:
        scaled = scale_theme(config, 0.75, "pad.xpad_s", "pad.ypad_s", "size.w_prompt")
    """
    scaled = copy.deepcopy(theme_cfg)

    for path in key_paths:
        keys = path.split('.')

        # Navigate to the parent dict
        current = scaled
        for key in keys[:-1]:
            if not isinstance(current, dict) or key not in current:
                break  # Path doesn't exist, skip
            current = current[key]
        else:
            # Successfully navigated to parent, now scale the leaf value
            leaf_key = keys[-1]
            if leaf_key in current:
                try:
                    current[leaf_key] = int(round(float(current[leaf_key]) * factor))
                except (ValueError, TypeError):
                    pass  # Non-numeric value, leave as-is

    return scaled


# TODO: (GUI updates)
#   1- if not in compact mode make sure the prompt goes to the bottom row with columnspan across the whole thing?
#   2- evaluate using pack on certain tabs


# TODO: should I remove the prompt width and height things now? because I reference the actual frame width and height now ya know?


##########################################
### APP AND FRAMES       #################
##########################################

class ThemedApp:
    def __init__(self, root, theme_file, compact):
        self.root = root
        self.style = ttk.Style(self.root)
        self.theme_config = None

        # Set the theme to use (optional, 'clam' is a common choice for consistency)
        self.style.theme_use('clam')

        # Load and apply the theme
        self.load_theme(theme_file, compact=compact)
        self.apply_theme()

    def load_theme(self, theme_file, compact=False):
        with open(theme_file, 'r') as f:
            self.theme_config = json.load(f)

        # Store compact mode flag so tabs can check it
        self.theme_config["compact"] = compact

        # Save original font size for notebook tabs (before any scaling)
        self.tab_font_size = self.theme_config["font"]["size"]

        if compact:
            # Scale padding and prompt sizes to 75%
            self.theme_config = scale_theme(
                self.theme_config, 0.75,
                "pad.xpad_s",
                "pad.ypad_s",
                "pad.frame_x",
                "pad.frame_y",
                # "size.w_prompt",
                # "size.h_prompt",
                #"size.w_prompt_s",
                "font.size_prompt"
            )

            # Scale general font size to 60% for labels, buttons, etc.
            # NOTE: Notebook tabs are exempt - they use self.tab_font_size
            self.theme_config = scale_theme(
                self.theme_config, 0.60,
                "font.size",
                "h1.size"
            )

            # Scale button height more aggressively to 45%
            self.theme_config = scale_theme(
                self.theme_config, 0.45,
                "size.h_button"
            )

    def apply_theme(self):
        """Apply the current theme configuration to all UI elements."""
        # Configure notebook and tab styles
        self.style.configure('TNotebook', background=self.theme_config["bg_dark"])
        self.style.configure('TNotebook.Tab',
                             background=self.theme_config["tab_background"],
                             foreground=self.theme_config["tab_foreground"],
                             font=(self.theme_config["font"]["family"],
                                   self.tab_font_size,  # Use original unscaled font size
                                   self.theme_config["font"]["style"]),
                             padding=(self.theme_config["pad"]["horizontal"],
                                      self.theme_config["pad"]["vertical"]))
        self.style.map("TNotebook.Tab",
                       background=[("selected", self.theme_config["selected_tab_background"])],
                       foreground=[("selected", self.theme_config["selected_tab_foreground"])])

        # Configure button styles
        self.style.configure('TButton',
                             background=self.theme_config["button"]["background"],
                             foreground=self.theme_config["button"]["foreground"],
                             font=(self.theme_config["font"]["family"],
                                   self.theme_config["font"]["size"],
                                   self.theme_config["font"]["style"]))


        self.style.configure("TButtonOn.TButton", background=self.theme_config["success"])
        self.style.configure("TButtonOff.TButton", background=self.theme_config["error"])


        # Configure label styles
        # generic label
        self.style.configure('TLabel',
                             background=self.theme_config["label"]["background"],
                             foreground=self.theme_config["label"]["foreground"],
                             font=(self.theme_config["font"]["family"],
                                   self.theme_config["font"]["size"],
                                   self.theme_config["font"]["style"]))

        # small label
        self.style.configure('TSpunkLabel.TLabel',
                             background=self.theme_config["dark_1"],
                             foreground=self.theme_config["fg_light"],
                             font=(self.theme_config["font"]["family"],
                                   self.theme_config["font"]["size_s"],
                                   self.theme_config["font"]["style"]))

        # header labels
        self.style.configure('TPinkLabel.TLabel',
                             background=self.theme_config["light_1"],
                             foreground="white",
                             font=(self.theme_config["h1"]["family"],
                                   self.theme_config["h1"]["size"],
                                   self.theme_config["h1"]["style"]))


# NOTE: this thing is mainly used for the tabs and the stuff in `gui_class.py`
#   it's not currently used for many of of the sub-Frames in tabs
class ThemedFrame(tk.Frame):
    def __init__(self, root, theme_config, *args, **kwargs):
        super().__init__(root, *args, **kwargs)
        self.root = root
        self.theme_config = theme_config
        self.set_bg(bg=self.theme_config["bg_dark"])

    def set_bg(self, bg):
        self.configure(bg=bg)



# TODO: with my new column configure and expand stuff how do I get that to reflect in the text box width?
#   also, how can I make it so it doesn't expand past the window edge and get cut off ever?
class Prompt(ThemedFrame):
    def __init__(self, master, theme_config, title, height, width):
        super().__init__(master, theme_config, height=height, width=width)
        self.height = height
        self.width = width
        self.set_bg(self.theme_config["light_4"])
        self.show_timestamps = True

        ttk.Label(self, text=title, style="TPinkLabel.TLabel").grid(row=0, column=0, pady=5, padx=10)

        # clear button
        clear_button = tk.Button(self, text="Clear console", command=self.clear,
                                 bg=self.theme_config["dark_3"], fg=self.theme_config["fg_light"])
        clear_button.grid(row=0, column=1, padx=7, pady=4, sticky="ew")

        # toggle timestamps button
        self.toggle_timestamp_btn = tk.Button(self,
                                               text="Timestamps: ON",
                                               command=self.toggle_timestamp,
                                 bg=self.theme_config["dark_3"], fg=self.theme_config["fg_light"])
        self.toggle_timestamp_btn.grid(row=0, column=1, padx=7, pady=4, sticky="ew")

        # set up text_data box for user communication
        self.prompt = scrolledtext.ScrolledText(self,
                                                font=(self.theme_config["font"]["family"], self.theme_config["font"]["size_prompt"]),
                                                height=height,
                                                width=width,
                                                bg=self.theme_config["dark_2"],
                                                fg=self.theme_config["fg_light"],
                                                borderwidth=10)
        self.prompt.tag_configure("error", foreground=self.theme_config["error"])
        self.prompt.tag_configure("normal", foreground=self.theme_config["fg_light"])
        self.prompt.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="nsew")

        # make it so ScrolledText will stretch
        self.grid_rowconfigure(1, weight=1)       # row=1 holds the ScrolledText
        self.grid_columnconfigure(0, weight=1)    # column=0 should stretch
        self.grid_columnconfigure(1, weight=1)    # since you used columnspan=2


    # gui_print: prints a message on a Tkinter frame
    def print(self, message, print_type=None, timestamp=None):
        # function arg override
        if timestamp is not None:
            self.toggle_timestamp(state=timestamp)

        if self.show_timestamps:
            time_str = datetime.now().strftime("%H:%M:%S")
            prefix = f"[{time_str}]>>> "
        else:
            prefix = ">>> "

        message = prefix + message + "\n"
        if print_type == "error":
            self.prompt.insert(INSERT, message, "error")  # Apply 'error' tag
        else:
            self.prompt.insert(INSERT, message, "normal")  # Apply 'normal' tag

        self.prompt.see("end")  # Auto-scroll to the end
        return True

    def toggle_timestamp(self, state=None):
        if state is not None:
            self.show_timestamps = state
        else:
            self.show_timestamps = not self.show_timestamps
        state = "ON" if self.show_timestamps else "OFF"
        self.toggle_timestamp_btn.config(text=f"Timestamps: {state}")


    def clear(self):
        self.prompt.delete("1.0", "end")  # basically line index from


##########################################
### CANVAS               #################
##########################################

class ColorCircle(tk.Canvas):
    def __init__(self, master, width, height, bg, *args, **kwargs):
        super().__init__(master, width=width, height=height, bg=bg, *args, **kwargs)
        self.status_oval = self.create_oval(width * .25, width * .25, width * .75, width * 0.75)  # x0, y0, x1, y1

    def set_color(self, color):
        self.itemconfig(self.status_oval, fill=color)


##########################################
### TOOLTIP                      #########
##########################################

class Tooltip:
    """Hover tooltip for any Tkinter widget.

    Usage:
        Tooltip(some_widget, "This is the help text")
    """
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)

    def _schedule(self, event=None):
        self._after_id = self.widget.after(self.delay, self._show)

    def _show(self):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 4
        y = self.widget.winfo_rooty()
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("TkDefaultFont", "9", "normal"),
                         wraplength=250)
        label.pack()

    def _hide(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


##########################################
### CONNECTION FRAMES            #########
##########################################

class ConnFrame(ThemedFrame):
    def __init__(self, master, theme_config, name, connect_cmd, disconnect_cmd, status_cmd=None):
        super().__init__(master, theme_config)
        self.master = master
        self.name = name
        self.connect_cmd = connect_cmd
        self.disconnect_cmd = disconnect_cmd
        self.status_cmd = status_cmd

        self.port = None

        self.status = False
        self.status_oval = ColorCircle(self, 50, 50, bg=self.theme_config["bg_dark"])

        self.set_bg(self.theme_config["light_4"])
        self.init_base_fr()

    def init_base_fr(self):
        label = ttk.Label(self, text=self.name, style="TSpunkLabel.TLabel")
        label.grid(row=0, column=1, pady=2)

    def connect(self):
        self.status = self.connect_cmd()
        print(f"Connect with {self.port} had status: {self.status} !\n")
        self.gui_refresh()
        return self.status

    def disconnect(self):
        self.disconnect_cmd()
        self.status = False
        self.gui_refresh()

    def set_status(self, status):
        if status:
            self.status_oval.set_color(self.theme_config["success"])
        else:
            self.status_oval.set_color(self.theme_config["error"])

    def gui_refresh(self):
        if self.status_cmd is not None:
            self.status = self.status_cmd()
        self.set_status(self.status)

    def set_color(self, color):
        self.status_oval.set_color(color)


class SerialConnFrame(ConnFrame):
    def __init__(self, master, theme_config, class_controller, name, connect_cmd, disconnect_cmd, port_func=None, status_cmd=None):
        super().__init__(master, theme_config, name, connect_cmd, disconnect_cmd, status_cmd=status_cmd)
        self.cc = class_controller

        # set up connection options
        self.port_func = port_func  # NONE defaults to OS detection method. 1=Windows, 2=Linux, 3=PyVISA
        self.port_func_options = {
            "Auto (OS detection)": 0,
            "Windows (COM ports)": 1,
            "Linux (/dev/tty*)": 2,
            "PyVISA": 3,
        }

        # GUI elements
        self.port_func_drop = None
        self.com_drop = None
        self.baud_drop = None

        self.initialize_fr()

    def initialize_fr(self):
        # initialize port connection method dropdown
        self.port_func_drop = guih.generate_drop_down(
            self,
            list(self.port_func_options.keys()),
            callback_func=self.set_port_func
        )
        self.port_func_drop[0].grid(row=1, column=1, padx=3, pady=1)

        # initialize port list dropdown
        self.com_drop = guih.generate_drop_down(
            self,
            serial_api.get_ports(method=self.port_func)
        )
        self.com_drop[0].grid(row=2, column=1, columnspan=1, padx=3, pady=1)
        self.refresh_ports(first_run=True)

        # add Button for refreshing port list
        refresh_button = tk.Button(self, text="Refresh Ports",
                                   command=self.refresh_ports,
                                   fg=self.theme_config["fg_light"], bg=self.theme_config["light_1"])
        refresh_button.grid(row=2, column=2, pady=1)

        # add Buttons for Connect / Disconnect
        btn_connect_serial = tk.Button(self, text="Connect to COM", command=self.connect,
                                       fg=self.theme_config["fg_light"], bg=self.theme_config["light_6"],
                                       font=(self.theme_config["font"]["family"], self.theme_config["font"]["size_s"], "bold"),
                                       height=1, width=15)
        btn_connect_serial.grid(row=3, column=1, padx=15, pady=1)
        btn_disconnect_serial = tk.Button(self, text="Disconnect COM", command=self.disconnect,
                                       fg=self.theme_config["error"], bg=self.theme_config["dark_3"],
                                    font=(self.theme_config["font"]["family"], self.theme_config["font"]["size_s"], "bold"),
                                          height=1, width=15)
        btn_disconnect_serial.grid(row=4, column=1, padx=15, pady=1)

        # place CONNECT button and STATUS indicator
        self.status_oval.grid(row=3, column=2, rowspan=2, padx=15, pady=3)

    def connect(self, set_used_port=True):
        # Get the selected port
        self.port = self.get_port()

        # Check if port is already actively connected
        is_active, active_usage = self.cc.is_port_active(self.port)
        if is_active:
            message = f"ERROR: Port {self.port} is already in use by {active_usage}"
            print(message)
            guih.alert_user("Port already in use", message, "error")
            self.status = False
            self.gui_refresh()
            return False

        # Proceed with connection
        super().connect()

        # If connection successful, track it
        if self.status:
            self.cc.add_active_connection(self.port, self.name)
            if set_used_port:
                self.cc.set_used_port(self.port, self.name)

        return self.status

    def disconnect(self):
        # Remove from active connections if we have a port
        if self.port:
            self.cc.remove_active_connection(self.port)

        # Call parent disconnect
        super().disconnect()

    def set_port_func(self):
        selected_label = self.port_func_drop[1].get()
        self.port_func = self.port_func_options[selected_label]
        self.refresh_ports(first_run=True)

    def refresh_ports(self, first_run=False, timeout=5):
        menu = self.com_drop[0]["menu"]
        menu.delete(0, "end")

        # update port list (with timeout to prevent GUI freeze)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(serial_api.get_ports, method=self.port_func)
            try:
                ports = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                ports = []
                print(f"WARNING: Port scan timed out after {timeout}s")

        # add each port name to the drop-down menu
        for string in ports:
            menu.add_command(label=string,
                             command=lambda value=string: self.com_drop[1].set(value))

        # if we aren't connected, adjust the port
        if not self.status:
            if self.com_drop[1].get() not in ports:
                try:
                    self.com_drop[1].set(ports[0])
                except IndexError:
                    self.com_drop[1].set(None)

        # set value to previously used port (if available)
        if first_run:
            prev_port = self.get_previous_port()
            if prev_port in ports:
                self.com_drop[1].set(prev_port)

    def get_port(self):
        self.port = self.com_drop[1].get()
        return self.port

    def get_previous_port(self):
        # Create the root element
        root = ET.Element("PortsUsed")
        try:
            tree = ET.ElementTree(root, file="config/ports_used.xml")
        except xml.etree.ElementTree.ParseError:
            return False

        port_elem = tree.find(self.name)
        if port_elem is not False:
            if port_elem is not None:
                return port_elem.text
        else:
            return None

    def connect_previous_port(self):
        self.port = self.get_previous_port()
        self.com_drop[1].set(self.port)
        if self.port is not None:
            print(f"Connect to previous port for {self.name} @ {self.port}")
            self.connect(set_used_port=False)
        return self.status


class AutoConnFrame(ConnFrame):
    def __init__(self, master, theme_config, name, connect_cmd, disconnect_cmd, status_cmd=None):
        self.master = master
        super().__init__(self.master, theme_config, name, connect_cmd, disconnect_cmd, status_cmd=status_cmd)

    def init_fr(self):
        self.status_oval.grid(row=1, column=2, padx=15, pady=22)

        tk.Button(
            self, text=f"Auto-connect", fg=self.theme_config["fg_dark"], bg=self.theme_config["light_3"],
            command=self.connect_cmd
        ).grid(row=0, column=1, padx=5, pady=5)

        # RELAY STATUS INDICATOR
        ttk.Label(self, text=f"{self.name} status", style="TLabel").grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(self, text=f"{self.name} config", style="TLabel").grid(row=2, column=1, padx=5, pady=5)

        self.gui_refresh()


##########################################
### THREADS             ##################
##########################################

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.args = args
        self.kwargs = kwargs

    # def run(self):
    # while not self.stopped():
    # self.function(*self.args, **self.kwargs)
    # break  # If you want to run only once, remove this if you need continuous execution

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
