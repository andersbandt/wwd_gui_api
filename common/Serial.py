"""
@file     Serial.py
@author   Anders Bandt
@date     March 2024
@brief    Python class for managing data with a serial connection
"""


# import needed modules
from datetime import datetime
import serial


class Serial:
    def __init__(self, port, baud_rate):
        # initialize serial connection
        self.serObj = serial.Serial(port, baud_rate)

        # set up some variables
        self.afe_adc = []
        self.plot_cnt = 0

    def get_data(self, printmode=False):
        # serStrDat = self.serObj.read_until().decode('utf-8').strip().strip('\n')
        bytes_to_read = self.serObj.inWaiting()
        serStrDat = self.serObj.read(bytes_to_read)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        if printmode:
            print(serStrDat)
        return serStrDat


    def send_data(self, data):
        self.serObj.write(data.encode('utf-8'))

