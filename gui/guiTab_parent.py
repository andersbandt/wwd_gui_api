import json
import tkinter as tk
from tkinter import ttk


class ThemedApp:
    def __init__(self, root, theme_file):
        self.root = root
        self.style = ttk.Style(self.root)

        # Set the theme to use (optional, 'clam' is a common choice for consistency)
        self.style.theme_use('clam')

        # Load the initial theme
        self.load_theme(theme_file)

    def load_theme(self, theme_file):
        """Load and apply theme from a JSON file."""
        with open(theme_file, 'r') as f:
            self.theme_config = json.load(f)
        self.apply_theme()

    def apply_theme(self):
        """Apply the current theme configuration."""
        # Configure styles for notebook and tabs
        self.style.configure('TNotebook', background=self.theme_config["background"])
        self.style.configure('TNotebook.Tab',
                             background=self.theme_config["tab_background"],
                             foreground=self.theme_config["tab_foreground"],
                             font=(self.theme_config["font"]["family"],
                                   self.theme_config["font"]["size"],
                                   self.theme_config["font"]["style"]),
                             padding=(self.theme_config["padding"]["horizontal"],
                                      self.theme_config["padding"]["vertical"]))

        self.style.map("TNotebook.Tab",
                       background=[("selected", self.theme_config["selected_tab_background"])],
                       foreground=[("selected", self.theme_config["selected_tab_foreground"])])

    def update_theme(self, new_theme_file):
        """Update the theme from a different theme file."""
        self.load_theme(new_theme_file)


# TODO: major refactoring. Have this inherit from tk.Frame?
class ThemedFrame:
    def __init__(self, root, theme_file):
        self.root = root
        self.style = ttk.Style(self.root)
        self.theme_config = None
        # Load the initial theme
        self.load_theme(theme_file)

        self.frame = tk.Frame(root, bg=self.theme_config["background"])

        # Set the theme to use (optional, 'clam' is a common choice for consistency)
        # self.style.theme_use('clam')


    def load_theme(self, theme_file):
        """Load and apply theme from a JSON file."""
        with open(theme_file, 'r') as f:
            self.theme_config = json.load(f)
        self.apply_theme()

    def apply_theme(self):
        """Apply the theme to the current frame."""
        # Configure Button styles
        self.style.configure('TButton',
                             background=self.theme_config["button"]["background"],
                             foreground=self.theme_config["button"]["foreground"],
                             font=(self.theme_config["font"]["family"],
                                   self.theme_config["font"]["size"],
                                   self.theme_config["font"]["style"]))
        self.style.map('TButton',
                       background=[('active', self.theme_config["button"]["active_background"])],
                       foreground=[('active', self.theme_config["button"]["active_foreground"])])

        # Configure Label styles
        self.style.configure('TLabel',
                             background=self.theme_config["label"]["background"],
                             foreground=self.theme_config["label"]["foreground"],
                             font=(self.theme_config["font"]["family"],
                                   self.theme_config["font"]["size"],
                                   self.theme_config["font"]["style"]))



    def update_theme(self, new_theme_file):
        """Update the theme from a different theme file."""
        self.load_theme(new_theme_file)