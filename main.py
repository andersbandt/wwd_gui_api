"""
@file     main.py
@author   Anders Bandt
@date     March 2024
@brief    used for control of my WWD device through a GUI
"""

# import user created modules
from gui import gui_driver


## TODO: somehow add some command line switch when calling to enable / disable auto-connect


##############################################################
################   MAIN     ##################################
##############################################################
if __name__ == '__main__':
    gui_driver.main()





