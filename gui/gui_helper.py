"""
@file     gui_helper.py
@author   Anders Bandt
@date     March 2024
@brief    A tkinter GUI helper class
"""

# import needed modules
from tkinter import *
from tkinter import messagebox


##############################################################################
####      GUI OBJECT GENERATION FUNCTIONS           ##########################
##############################################################################

def generate_drop_down(frame, options, callback_func=None):
    clicked_opt = StringVar()  # datatype of menu text_data
    try:
        clicked_opt.set(options[0])  # initial menu text_data (CAUSES ISSUES IF NO COM PORTS AVAILABLE)
    except Exception as e:
        clicked_opt.set("NA")
        options = ["NA"]

    def callback(*args):
        callback_func()

    if callback_func is not None:
        clicked_opt.trace("w", callback)

    drop = OptionMenu(frame, clicked_opt, *options)  # create drop down menu of years
    drop.config(width=15, font=('Arial', 10), bg="#2B2B2B", fg='#F8F8F2')
    return drop, clicked_opt


##############################################################################
####      PROMPT/ALERT FUNCTIONS           ###################################
##############################################################################

# promptYesNo: prompts the user for a yes or no response with a certain 'message' prompt
def promptYesNo(title, message):
    response = messagebox.askquestion(title, message)

    if response == "yes":
        return True
    else:
        return False


# alert_user: alerts the user with a prompt that flashes on the screen
#   kind can be of type {"error", "warning", and "info"}
def alert_user(title, message, kind):
    if kind not in ('error', 'warning', 'info'):
        raise ValueError('Unsupported alert kind.')

    show_method = getattr(messagebox, 'show{}'.format(kind))
    show_method(title, message)



