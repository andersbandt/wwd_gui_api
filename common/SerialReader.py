"""
@file     SerialReader.py
@author   Anders Bandt
@date     March 2024
@brief    read data from serial (COM) port
"""
import queue
# import needed modules
from datetime import datetime
import serial
import collections
import time

# import user created modules
from common import SerialGeneral
from common import logger


class SerialReader(SerialGeneral.SerialGeneral):
    def __init__(self, port, baudrate):
        super().__init__(port, baudrate)
        self.procStatus = False
        self.r_buf = collections.deque(maxlen=200)  # read circular buffer # TODO: the key to allowing print in my main allocation is to process this there
        # self.r_buf = queue.Queue()  # TODO: is this better option (thread-safe ?????)
        self.logfile = None

    def get_data(self, printmode=False):
        serStrDat = 0
        while self.serStatus:  # Loop until serial status becomes False
            try:
                bytes_to_read = self.serObj.inWaiting()
                if bytes_to_read > 0:
                    ser_bytes = self.serObj.read(bytes_to_read)

                    # If printmode is True, print the raw bytes
                    if printmode:
                        print(ser_bytes)

                    # Decode bytes to string if needed
                    try:
                        serStrDat = ser_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        print(f"DECODE ERROR ON SerialReader DATA: [{serStrDat}")
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    self.r_buf.append([timestamp, serStrDat])
            except (serial.serialutil.SerialException, OSError) as e:  # (Windows, Linux)
                self.serStatus = False
                print(e)
                break  # Exit the loop on serial exception

    def process_data(self, basefilepath, name_ext, data_mode, data_folder, parameters=None):
        print(f"Starting to process data with mode: {data_mode}")
        self.procStatus = True

        # INIT OF LOG FILE
        if data_mode == "data":
            log_text = logger.init_csv(basefilepath, data_folder, name_ext, parameters)
        elif data_mode == "raw" or data_mode == "timestamp":
            log_text = logger.init_text(basefilepath, data_folder, "\n\n\n===================================\n"
                                                "=======INFO: USB LOG START=========\n"
                                                "===================================\n")
            self.logfile = log_text

        # Loop while serial status is True and buffer is not empty
        # while self.serStatus and self.procStatus:
        while self.procStatus:
            if self.r_buf:
                data = self.r_buf.pop()

                # VARIABLE RETURN BASED ON @data_mode
                if data_mode == "timestamp":
                    serStrDat = "\n" + data[0] + " --->   " + data[1]
                    logger.append_text(log_text, serStrDat)
                elif data_mode == "data":
                    data_array = [data[0]]
                    split = data[1].split(',')
                    data_array.extend(split)
                    logger.append_csv(log_text, data_array)
                elif data_mode == "raw":
                    logger.append_text(log_text, data[1])
                else:
                    raise BaseException("ERROR: undefined data mode for SerialReader")
        print("Stop processing data.")


    # TODO: this really shouldn't have things specific to text processing in it ...
    def stop_process(self):
        if self.procStatus:
            self.procStatus = False
            self.close()
            logger.append_text(self.logfile, "\n\n\n==================== USB LOG ENDED !!!!!  ====================\n")


