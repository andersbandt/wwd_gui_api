"""
@file     main.py
@author   Anders Bandt
@date     March 2024
@brief    used for control of my WWD device through a GUI
"""

# needed modules
import argparse
import logging

# import user created modules
from gui import gui_driver


# NOTE: mainly added this because XDM1041 EEequipment code includes it?
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# TODO: review my `tag:HARDCODE` items


def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="A description of your script.")

    # Add command-line arguments
    parser.add_argument('-a', '--auto-connect', action='store_true', help='Enable auto-connect mode')
    parser.add_argument('-o', '--disable-auto', action='store_true', help='Enable other behavior')

    # Parse the arguments
    args = parser.parse_args()

    # Use the arguments to determine behavior
    autoconnect = True
    if args.auto_connect:
        print("Auto-connect enabled.")
        autoconnect = True
    if args.disable_auto:
        print("Auto-connect disabled")
        autoconnect = False

    # Call the main function of your GUI driver
    gui_driver.main(autoconnect)

    # quit if we reach this point
    quit()


##############################################################
################   MAIN     ##################################
##############################################################
if __name__ == '__main__':
    main()


