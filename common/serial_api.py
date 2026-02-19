"""Serial port detection and enumeration utilities."""

# import needed modules
import serial
from serial.tools import list_ports
import pyvisa
import glob
import platform


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
        # Default ResourceManager works with NI-VISA backend. Use '@py' for pyvisa-py (no NI-VISA required).
        # See EEequipment docs for backend selection guidance.
        rm = pyvisa.ResourceManager()
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
        print(f"Device: {port.device}, Description: {port.description}")


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


