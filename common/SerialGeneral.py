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
        # initialize serial connection
        self.serObj = serial.Serial(port, baud_rate)
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
        print("Stopping serial data processing")
        self.serObj.close()
        self.serStatus = False


