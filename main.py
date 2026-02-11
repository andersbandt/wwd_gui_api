"""Entry point for the WWD GUI application."""

# needed modules
import argparse


# import user created modules
from gui import gui_driver


# TODO: give the README a solid review



def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="A description of your script.")

    # Add command-line arguments
    parser.add_argument('-a', '--auto-connect', action='store_true', help='Enable auto-connect mode')
    parser.add_argument('-c', '--compact', action='store_true', help='Force compact mode (overrides automatic screen size detection)')

    # Parse the arguments
    args = parser.parse_args()

    # Use the arguments to determine behavior
    autoconnect = False
    if args.auto_connect:
        print("Auto-connect enabled.")
        autoconnect = True

    force_compact = False
    if args.compact:
        print("Compact mode forced.")
        force_compact = True

    # Call the main function of your GUI driver
    gui_driver.main(autoconnect, force_compact)

    # quit if we reach this point
    print("calling quit()")
    quit()


##############################################################
################   MAIN     ##################################
##############################################################
if __name__ == '__main__':
    main()


