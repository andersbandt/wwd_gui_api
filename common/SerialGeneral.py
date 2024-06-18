"""
@file     SerialGeneral.py
@author   Anders Bandt
@date     March 2024
@brief    Python class for managing data with a serial connection
"""

# import needed modules
from datetime import datetime
import serial


class SerialGeneral:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        # initialize serial connection
        self.serObj = serial.Serial(self.port, self.baud_rate)
        self.serStatus = True

    def reopen(self):
        try:
            self.serObj = serial.Serial(self.port, self.baud_rate)
        except serial.serialutil.SerialException:
            self.serStatus = False
            print(f"Can't reopen port --> {self.port}")
            return

        print("Opened! Yay!")
        self.serStatus = True

    def get_data(self, printmode=False):
        bytes_to_read = self.serObj.inWaiting()
        serStrDat = self.serObj.read(bytes_to_read)
        if printmode:
            print(serStrDat)
        return serStrDat

    def send_data(self, data):
        self.serObj.write(data.encode('utf-8'))

    def close(self):
        self.serObj.close()
        self.serStatus = False


