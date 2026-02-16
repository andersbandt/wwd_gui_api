"""Serial port detection and enumeration utilities."""

# import needed modules
import time
import serial
from serial.tools import list_ports
import pyvisa
import glob
import platform


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

    # METHOD 2: trying to get Linux to work. Search for serial ports in /dev/
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
                pass

    elif method == 3:
        rm = pyvisa.ResourceManager('@py')
        ports = [r.replace('\x00', '') for r in rm.list_resources() if not r.startswith('ASRL')]
    else:
        ports = None

    # METHOD 4: output of "lsbusb" command
    # testing. one last print
    # devices = show_ports_linux()
    # ports = []
    # for device in devices:
    #     ports.append(device["device"])
    #
    # ports = ["/dev/bus/usb/001/029"]

    return ports


def show_ports():
    # Get a list of all available serial ports
    ports = serial.tools.list_ports.comports()

    # Print information about each port
    for port in ports:
        print(f"Device: {port.device}, Description: {port.description}")


def show_ports_linux():
    import re
    import subprocess
    device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
    df = subprocess.check_output("lsusb")
    devices = []
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                devices.append(dinfo)

    # print(devices)
    return devices


