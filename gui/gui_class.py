import tkinter as tk
from tkinter import Text, INSERT, Label


class Prompt:
    def __init__(self, frame, title, bg_color, height, width):
        self.frame = frame
        self.height = height
        self.width = width
        self.bg_color = bg_color

        # set up text box for user communication
        Label(frame, text=title).grid(row=0, column=0, pady=3)
        clear_button = tk.Button(frame, text="Clear console", command=self.clear, bg="black", fg="white")
        clear_button.grid(row=0, column=1, padx=7, pady=3, sticky="ew")
        self.prompt = Text(frame,
                           height=height, width=width,
                           bg=bg_color, fg="white",
                           borderwidth=10)
        self.prompt.grid(row=1, column=0, columnspan=2, padx=5, pady=3)

    # gui_print: prints a message on a Tkinter frame
    def print(self, message, print_type=None):
        if print_type == "error":
            fg_color = "red"
        else:
            fg_color = "white"  # Default color

        message = ">>>" + message
        self.prompt.configure(fg=fg_color)  # Configure text color
        self.prompt.insert(INSERT, message + "\n")
        self.prompt.see("end")  # auto-scroll to the end
        return True

    def clear(self):
        self.prompt.delete("1.0", "end")  # basically line index from

