"""
@file     main.py
@author   Anders Bandt
@date     March 2024
@brief    used for control of my WWD device through a GUI
"""

# needed modules
import argparse
from gui import gui_driver


def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="A description of your script.")

    # Add command-line arguments
    parser.add_argument('-a', '--auto-connect', action='store_true', help='Enable auto-connect mode')
    parser.add_argument('-o', '--disable-auto', action='store_true', help='Enable other behavior')

    # Parse the arguments
    args = parser.parse_args()

    # Use the arguments to determine behavior
    # TODO; finish implementing function control based on arguments
    if args.auto_connect:
        print("Auto-connect enabled.")
    if args.disable_auto:
        print("Auto-connect disabled")

    # Call the main function of your GUI driver
    gui_driver.main()


##############################################################
################   MAIN     ##################################
##############################################################
if __name__ == '__main__':
    main()


