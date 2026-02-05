# TODO: ask claude to go around and add these to every file (can I do it on my main Linux PC to get actual dates?)

"""
@file     main.py
@author   Anders Bandt
@date     March 2024
@brief    used for control of my WWD device through a GUI
"""

# needed modules
import argparse


# import user created modules
from gui import gui_driver


# TODO: add back those notes about tkinter installation on Linux and what not to README.md
# TODO: give the README a solid review



def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="A description of your script.")

    # Add command-line arguments
    parser.add_argument('-a', '--auto-connect', action='store_true', help='Enable auto-connect mode')

    # Parse the arguments
    args = parser.parse_args()

    # Use the arguments to determine behavior
    autoconnect = False
    if args.auto_connect:
        print("Auto-connect enabled.")
        autoconnect = True

    # Call the main function of your GUI driver
    gui_driver.main(autoconnect)

    # quit if we reach this point
    print("calling quit()")
    quit()


##############################################################
################   MAIN     ##################################
##############################################################
if __name__ == '__main__':
    main()


