"""
@file     gui_helper.py
@author   Anders Bandt
@date     March 2024
@brief    A tkinter GUI helper class
"""

# import needed modules
from tkinter import *
from tkinter import messagebox
import math


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
    drop.config(width=15, font=('Arial', 10), bg="#2B2B2B", fg='#F8F8F2') # tag:hardcode
    return drop, clicked_opt


##############################################################################
####      DATA VERIFICATION FUNCTIONS           ##############################
##############################################################################

def is_int(integer_maybe):
    try:
        int(integer_maybe)
    except Exception:
        return False
    return True


def is_float(float_maybe):
    try:
        float(float_maybe)
    except Exception:
        return False
    return True


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


# initialize an empty string
def convertTuple(tup):
    string = ''
    for item in tup:
        string = string + item
    return string


##############################################################################
####      TREE FUNCTIONS           ###########################################
##############################################################################

# drawLine: draws a line between coordinates (x1, y1) and (x2, y2) on 'canvas'
def drawLine(canvas, x1, y1, x2, y2):
    canvas.create_line(x1, y1, x2, y2, tags="line")

def paintBranch(canvas, depth, x1, y1, length, angle):
    if depth >= 0:
        x2 = x1 + int(math.cos(angle) * length)
        y2 = y1 + int(math.sin(angle) * length)

        # Draw the line
        drawLine(canvas, x1, y1, x2, y2)

        angleFactor = math.pi / 5
        sizeFactor = 0.58

        # Draw the left branch
        paintBranch(canvas, depth - 1, x2, y2, length * sizeFactor, angle + angleFactor)
        # Draw the right branch
        paintBranch(canvas, depth - 1, x2, y2, length * sizeFactor, angle - angleFactor)
