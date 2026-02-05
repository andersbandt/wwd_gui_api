"""
@file     serial_helper.py
@author   Anders Bandt
@date     March 2024
@brief    Python class for managing data with a serial connection
"""

# import needed modules
import serial
from datetime import datetime
import queue
import time
import os

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
        # Using queue.Queue for thread-safe producer/consumer pattern
        # Previously used collections.deque(maxlen=200) but it wasn't fully thread-safe
        self.r_buf = queue.Queue(maxsize=200)  # Thread-safe read buffer

    def init_data(self, data_mode, parameters):
        print("SerialProcessor data initialization")
        if data_mode == "data":
            self.logfile = csvh.CSVHelper(self.basefilepath, parameters)
            print(f"\tpath is at: {self.logfile.file_path}")
        elif data_mode == "raw" or data_mode == "timestamp":
            logname = logger.build_log_name("SER","","log", date_strf='%Y%m%d')
            self.logfile = os.path.join(self.basefilepath, logname)
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

                    # Use put_nowait to avoid blocking if queue is full (drops oldest behavior)
                    try:
                        self.r_buf.put_nowait([timestamp, serStrDat])
                    except queue.Full:
                        # Queue is full, drop oldest by getting one item then putting new one
                        try:
                            self.r_buf.get_nowait()  # Remove oldest
                            self.r_buf.put_nowait([timestamp, serStrDat])  # Add new
                        except queue.Empty:
                            pass  # Race condition, queue emptied, skip
            except (serial.serialutil.SerialException, OSError) as e:  # NOTE errors are for (Windows, Linux)
                self.serStatus = False
                print(e)

    def process_data(self, basefilepath, data_folder, data_mode, parameters=None, gui_callback=None):
        # If gui_callback is provided, display on GUI instead of logging to file
        if gui_callback:
            print("Starting to display data on GUI")
            self.procStatus = True
            self.num_lines = 0
            while self.serStatus and self.procStatus:
                try:
                    # Non-blocking get with timeout to allow loop to check status flags
                    data = self.r_buf.get(timeout=0.1)
                    self.num_lines += 1
                    # Call GUI callback with timestamp and data
                    gui_callback(data[0], data[1])
                except queue.Empty:
                    continue  # No data available, continue looping
            print("SerialProcessor finished GUI display")
            return

        # File logging mode (original behavior)
        # INIT OF LOG FILE
        self.basefilepath = os.path.join(basefilepath, data_folder)
        self.init_data(data_mode, parameters)

        # Loop while serial status is True and buffer is not empty
        print(f"Starting to process data with mode: {data_mode}")
        self.procStatus = True
        self.num_lines = 0
        while self.serStatus and self.procStatus:
            try:
                # Non-blocking get with timeout to allow loop to check status flags
                data = self.r_buf.get(timeout=0.1)
            except queue.Empty:
                continue  # No data available, continue looping

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
            # TODO: this below append fails if we selected print to screen mode. Hacking it now with TypeError catch
            try:
                logger.append_text(self.logfile, "\n\n\n==================== USB LOG ENDED !!!!!  ====================\n")
            except TypeError:
                pass
            return self.num_lines
        else:
            return 0
