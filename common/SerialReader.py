"""
@file     SerialReader.py
@author   Anders Bandt
@date     March 2024
@brief    read data from serial (COM) port
"""

# import needed modules
from datetime import datetime
import serial
from drawnow import *

# import user created modules
from common import SerialGeneral
from common import logger


class SerialReader(SerialGeneral.SerialGeneral):
    def __init__(self, port, baudrate, log=True):
        super().__init__(port, baudrate)

        if log:
            # logger.init_log("USB_LOG", f"log/{filename}.log")
            self.logfilename = logger.init_text("log/", "\n\n\n===================================\n"
                                                        "=======INFO: USB LOG START=========\n"
                                                        "===================================\n")
        else:
            self.logfilename = None


    def init_data_process(self, basefilepath, parameters, filename_ext=None):
        filename = logger.init_csv(basefilepath, parameters, filename_ext)
        status = True
        while status:
            try:
                data_array = self.get_data("data", printmode=False)
                if data_array is not None:
                    print(data_array)
                    logger.append_csv(filename, data_array)
            except Exception:
                status = False
        return

    # TODO: compare this to the one its overriding in Serial parent class
    def get_data(self, data_mode, printmode=False):
        # serStrDatp = self.serObj.read_until()
        bytes_to_read = self.serObj.inWaiting()
        serStrDatp = self.serObj.read(bytes_to_read)

        try:
            serStrDat = serStrDatp.decode('utf-8').strip().strip('\n')
        except UnicodeDecodeError as e:
            # serStrDat = serStrDatp.hex()
            raise e

        # set timestamp and print mode
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        if printmode:
            print(serStrDat)

        # VARIABLE RETURN BASED ON @data_mode
        if data_mode == "timestamp":
            serStrDat = "\n" + timestamp + " --->   " + serStrDat
            logger.append_text(self.logfilename, serStrDat)
        elif data_mode == "data":
            if "DATA," in serStrDat:
                data_array = serStrDat.split(',')
                data_array.append(timestamp)
                # TODO: how can I log to .csv file right here?
        else:
            raise Exception("ERROR: undefined data mode for SerialReader")

        return serStrDat


    def close(self):
        print("Stopping serial data processing")
        plt.close()
        self.serObj.close()

    # Create a function that makes our desired plot
    def makeFig(self):
        plt.title('Sensor data')  # Set the title
        plt.grid(True)  # Set The grid
        plt.ylabel('Axis Acceleration')  # Label the y axis
        plt.plot(self.afe_adc, 'ro-', label='AFE data')  # Set the line plot

    def live_plot(self, data):
        plt.ion()
        update_frequency = 10

        # Ensure that index is not out of range
        if len(data) > 1:
            adc = int(data[2])
            self.afe_adc.append(adc)

            # trim array
            self.plot_cnt = self.plot_cnt + 1
            if self.plot_cnt > 100:
                self.afe_adc.pop(0)

        if self.plot_cnt % update_frequency == 0:
            drawnow(self.makeFig)
            # self.makeFig() # GPT suggested not using drawnow() but I haven't gotten this to work
            plt.pause(.00000001)
