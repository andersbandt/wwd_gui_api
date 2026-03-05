"""Serial port detection, enumeration, and communication utilities."""

# import needed modules
import logging
import serial
from serial.tools import list_ports
import pyvisa
import glob
import platform
from datetime import datetime
import queue
import os

_logger = logging.getLogger(__name__)

# import user created modules
from common import logger
from common import csv_helper as csvh
from common import path_helper


# method=None (or 0) = auto: detects OS and picks method 1 (Windows) or 2 (Linux).
# Explicit int lets callers override, e.g. to force PyVISA (3) regardless of OS.
def get_ports(method=None, exclude_ports=None):
    if method is None or method == 0:
        os_name = platform.system()
        if os_name == "Windows":
            method = 1
        elif os_name == "Linux":
            method = 2

    # METHOD 1: worked best on windows
    if method == 1:
        ports = [port.device for port in list_ports.comports()]

    # METHOD 2: glob /dev/tty* and probe each port. Different from show_ports_linux()
    # which uses lsusb subprocess — that lists USB buses, not tty devices.
    elif method == 2:
        temp_ports = glob.glob('/dev/tty[A-Za-z]*')

        ports = []
        for a_port in temp_ports:
            # Skip ports with active connections - opening them at default
            # 9600 baud would corrupt the existing connection's baud rate
            if exclude_ports and a_port in exclude_ports:
                ports.append(a_port)
                continue

            try:
                s = serial.Serial(a_port)
                s.close()
                ports.append(a_port)
            except serial.SerialException:
                pass  # Port exists but can't be opened (in use or no permission)

    elif method == 3:
        svc = path_helper._config_svc
        backend = svc.get_visa_backend() if svc is not None else None
        rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
        # ASRL (serial/RS-232) resources are excluded — we enumerate those via method 1/2 instead.
        ports = [r.replace('\x00', '') for r in rm.list_resources() if not r.startswith('ASRL')]
    else:
        ports = None

    return ports


def show_ports():
    # Get a list of all available serial ports
    ports = serial.tools.list_ports.comports()

    # Print information about each port
    for port in ports:
        logger.info(f"Device: {port.device}, Description: {port.description}")


def show_ports_linux():
    import re
    import subprocess
    device_re = re.compile(rb"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output("lsusb")
    devices = []
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                devices.append(dinfo)

    return devices


# ============================================================================
# Serial communication classes
# ============================================================================

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
            logger.error(f"Can't reopen port --> {self.port}")
            return

        logger.info(f"Reopened port {self.port}")
        self.serStatus = True

    def get_data(self, printmode=False):
        bytes_to_read = self.serObj.inWaiting()
        serStrDat = self.serObj.read(bytes_to_read)
        if printmode:
            logger.debug(serStrDat)
        return serStrDat

    def send_data(self, data):
        self.serObj.write(data.encode('utf-8'))

    def read_line(self):
        line = self.serObj.readline()
        return line

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
        _logger.info("SerialProcessor data initialization")
        if data_mode == "data":
            self.logfile = csvh.CSVHelper(self.basefilepath, parameters)
            _logger.info(f"path is at: {self.logfile.file_path}")
        elif data_mode == "raw" or data_mode == "timestamp":
            logname = logger.build_log_name("SER", "", "log", date_strf='%Y%m%d')
            self.logfile = os.path.join(self.basefilepath, logname)
            logger.append_text(self.logfile, "\n\n\n===================================\n"
                                             "=======INFO: USB LOG START=========\n"
                                             "===================================\n")
            _logger.info(f"path is at: {self.logfile}")
        else:
            self.logfile = None

    def get_data(self, printmode=False):
        serStrDat = 0
        while self.serStatus:  # Loop until serial status becomes False
            try:
                bytes_to_read = self.serObj.inWaiting()
                if bytes_to_read > 0:
                    ser_bytes = self.serObj.read(bytes_to_read)

                    if printmode:
                        _logger.debug(ser_bytes)

                    try:
                        serStrDat = ser_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        _logger.error(f"DECODE ERROR ON SerialReader DATA: [{serStrDat}")
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
                _logger.error(e)

    # TODO: need to add back allowing a certain filename
    def process_data(self, basefilepath, data_folder, data_mode, parameters=None, gui_callback=None):
        # If gui_callback is provided, display on GUI instead of logging to file
        if gui_callback:
            _logger.info("Starting to display data on GUI")
            self.procStatus = True
            self.num_lines = 0
            while self.serStatus and self.procStatus:
                try:
                    data = self.r_buf.get(timeout=0.1)
                    self.num_lines += 1
                    gui_callback(data[0], data[1])
                except queue.Empty:
                    continue
            _logger.info("SerialProcessor finished GUI display")
            return

        # File logging mode
        self.basefilepath = os.path.join(basefilepath, data_folder)
        self.init_data(data_mode, parameters)

        _logger.info(f"Starting to process data with mode: {data_mode}")
        self.procStatus = True
        self.num_lines = 0
        while self.serStatus and self.procStatus:
            try:
                data = self.r_buf.get(timeout=0.1)
            except queue.Empty:
                continue

            self.num_lines += 1
            if data_mode == "timestamp":
                serStrDat = "\n" + data[0] + " --->   " + data[1]
                logger.append_text(self.logfile, serStrDat)
            elif data_mode == "data":
                data_array = [data[0]]
                split = data[1].split(',')
                data_array.extend(split)
                self.logfile.add_row(data_array)
            elif data_mode == "raw":
                logger.append_text(self.logfile, data[1])
            else:
                raise BaseException("ERROR: undefined data mode for SerialReader")

        _logger.info("SerialProcessor finished process_data()")

    def stop_process(self):
        if self.procStatus:
            self.procStatus = False
            self.close()
            try:
                logger.append_text(self.logfile, "\n\n\n==================== USB LOG ENDED !!!!!  ====================\n")
            except TypeError:
                _logger.debug("SerialProcessor: logfile not writable (GUI display mode)")
            return self.num_lines
        else:
            return 0
