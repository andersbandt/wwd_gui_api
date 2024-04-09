"""
@file     gui_helper.py
@author   Anders Bandt
@date     March 2024
@brief    A tkinter GUI helper class
"""

# import needed modules
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter import messagebox
import math


##############################################################################
####      GUI OBJECT GENERATION FUNCTIONS           ##########################
##############################################################################

def generate_drop_down(frame, options):
    clicked_opt = StringVar()  # datatype of menu text
    try:
        clicked_opt.set(options[0])  # initial menu text (CAUSES ISSUES IF NO COM PORTS AVAILABLE)
    except Exception as e:
        print(f"{e} when running generate_drop_down")
        clicked_opt.set("COM[DUMMY]")
        options = ["COM[DUMMY]"]
    drop = OptionMenu(frame, clicked_opt, *options)  # create drop down menu of years
    return drop, clicked_opt



##############################################################################
####      PROMPT/ALERT FUNCTIONS           ###################################
##############################################################################

# promptYesNo: prompts the user for a yes or no response with a certain 'message' prompt
def promptYesNo(message):
    response = messagebox.askquestion('ALERT', message)

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

# TODO: get this angle matrix generation function working properly
#   has to be some component of odd/even in the for loop...
# generate_tree_angles: generates an array of the different angles to plot children node from a parent
def generate_tree_angles(num_children, max_angle):
    if num_children == 0:
        return [0]

    if num_children == 1:
        return [0]

    if num_children == 2:
        return [max_angle / 2, -max_angle / 2]

    if num_children == 3:
        return [max_angle, 0, -max_angle]

    if num_children == 4:
        return [max_angle, max_angle * 1 / 2, -max_angle * 1 / 2, -max_angle]

    if num_children == 5:
        return [max_angle, max_angle * 3 / 5, 0, -max_angle * 3 / 5, -max_angle]

    if num_children == 6:
        return [max_angle, max_angle * 4 / 5, max_angle * 2 / 5, -max_angle * 2 / 5, -max_angle * 4 / 5, -max_angle]

    print("Uh oh, this statement shouldn't be reached! No angle matrix was found!")
    print("ERROR: can't generate angle matrix for number of children: " + str(num_children))


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
