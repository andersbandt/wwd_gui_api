"""Serial port detection and enumeration utilities."""

# import needed modules
import time
import serial
from serial.tools import list_ports
import pyvisa
import glob
import platform


# TODO: evaluate the need for this "auto" (method=None or 0). It's kind of confusing even to me
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
    # TODO: shouldn't I bundle the below stuff into show_ports_linux() method?
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
        # TODO: do I need to get clever about which one I'm using? At work I need just (), at home I might need @py
        #   previously this was just () but somehow worked with the ConnectionHandler being @py. Now that behavior is no longer true
        # rm = pyvisa.ResourceManager('@py')
        rm = pyvisa.ResourceManager()
        # ports = rm.list_resources()
        # TODO: document that I'm not printing ASRL instruments (what are they even?)
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
    # TODO: syntax warning: invalid escape sequence `\s`
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

    return devices


