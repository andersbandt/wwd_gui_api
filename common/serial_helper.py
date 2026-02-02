"""
@file     serial_helper.py
@author   Anders Bandt
@date     March 2024
@brief    Python class for managing data with a serial connection
"""

# import needed modules
import serial
from datetime import datetime
import collections
import queue
import time

# import user created modules
from common import logger
from common import csv_helper as csvh



class SerialGeneral:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
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



class SerialProcessor(SerialGeneral):
    def __init__(self, port, baudrate):
        super().__init__(port, baudrate)
        self.procStatus = False
        self.logfile = None
        self.num_lines = 0
        # TODO: CLAUDE should see if I should use collections or Queue here!
        self.r_buf = collections.deque(
            maxlen=200)  # read circular buffer
        # self.r_buf = queue.Queue()



    def init_data(self, data_mode, parameters):
        print("SerialProcessor data initialization")
        if data_mode == "data":
            self.logfile = csvh.CSVHelper(self.basefilepath, parameters)
            print(f"\tpath is at: {self.logfile.file_path}")
        elif data_mode == "raw" or data_mode == "timestamp":
            logname = logger.build_log_name("SER","","log", date_strf='%Y%m%d')
            self.logfile = f"{self.basefilepath}\\{logname}"
            logger.append_text(self.logfile, "\n\n\n===================================\n"
                                                                   "=======INFO: USB LOG START=========\n"
                                                                   "===================================\n")
            print(f"\tpath is at: {self.logfile}")
        else:
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
            except (serial.serialutil.SerialException, OSError) as e:  # NOTE errors are for (Windows, Linux)
                self.serStatus = False
                print(e)

    def process_data(self, basefilepath, data_folder, data_mode, parameters=None):
        # INIT OF LOG FILE
        self.basefilepath = f"{basefilepath}\\{data_folder}"
        self.init_data(data_mode, parameters)

        # Loop while serial status is True and buffer is not empty
        print(f"Starting to process data with mode: {data_mode}")
        self.procStatus = True
        self.num_lines = 0
        while self.serStatus and self.procStatus:
            if self.r_buf:
                data = self.r_buf.pop()

                # VARIABLE RETURN BASED ON @data_mode
                self.num_lines += 1
                if data_mode == "timestamp":
                    serStrDat = "\n" + data[0] + " --->   " + data[1]
                    logger.append_text(self.logfile, serStrDat)
                elif data_mode == "data":
                    data_array = [data[0]]
                    split = data[1].split(',')
                    data_array.extend(split)
                    self.logfile.add_row(data_array) # NOTE: this should be a CSVHelper object
                elif data_mode == "raw":
                    logger.append_text(self.logfile, data[1])
                else:
                    raise BaseException("ERROR: undefined data mode for SerialReader")

        # self.stop_process()
        print("SerialProcessor finished process_data()")

    def stop_process(self):
        if self.procStatus:
            self.procStatus = False
            self.close()
            logger.append_text(self.logfile, "\n\n\n==================== USB LOG ENDED !!!!!  ====================\n")
            return self.num_lines
        else:
            return 0
