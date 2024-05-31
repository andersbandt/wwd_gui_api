# Copyright 2021 Joshua Watt <JPEWhacker@gmail.com>
#
# SPDX-License-Identifier: MIT

import array
import os
import usb.core
import usb.util
# import xdg
# import yaml
import configparser

USB_TYPE_CLASS = 0x20
USB_ENDPOINT_OUT = 0x00
USB_ENDPOINT_IN = 0x80
USB_RECIP_DEVICE = 0x00
GET_REPORT = 0x1
SET_REPORT = 0x9
USB_HID_REPORT_TYPE_FEATURE = 3
MAIN_REPORT = 0


def xor(a, b):
    return bool(a) != bool(b)


VENDOR_ID = 0x16C0
PRODUCT_ID = 0x05DF

NUM_RELAY = 8


def find():
    def _get_backend():
        import os

        if os.name != "nt":
            print("OS is sufficent. Not bothering with finding libusb")
            return None

        import usb.backend.libusb1
        import libusb
        import pathlib

        # Manually find the libusb DLL and create a backend using it. I don't know
        # why Python can't find this on its own
        libpath = next(pathlib.Path(libusb.__file__).parent.rglob("x64/libusb-1.0.dll"))
        return usb.backend.libusb1.get_backend(find_library=lambda x: str(libpath))

    class MatchUSBRelay(object):
        def __call__(self, device):
            manufacturer = usb.util.get_string(device, device.iManufacturer)
            product = usb.util.get_string(device, device.iProduct)
            if manufacturer != "www.dcttech.com":
                return False

            if not product.startswith("USBRelay"):
                return False

            return True

    # device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
    devices = usb.core.find(
        backend=_get_backend(),
        find_all=False,
        idVendor=VENDOR_ID,
        idProduct=PRODUCT_ID,
        custom_match=MatchUSBRelay(),
    )
    return devices


# 1. �����к�afEd5�豸�ĵ�һ·�̵���
# CommandApp_USBRelay  afEd5 open 01
# 2. �����к�afEd5�豸�����м̵���
# CommandApp_USBRelay  afEd5 open 255
# 3. �ر����к�afEd5�豸�ĵ�һ·�̵���
# CommandApp_USBRelay  afEd5 close 01
# 4. �ر����к�afEd5�豸�����м̵���
# CommandApp_USBRelay  afEd5 close 255

# status bit: High --> Low 0000 0000 0000 0000 0000 0000 0000 0000, one bit indicate a relay status.
# the lowest bit 0 indicate relay one status, 1 -- means open status, 0 -- means closed status.
# bit 0/1/2/3/4/5/6/7/8 indicate relay 1/2/3/4/5/6/7/8 status
# @returns: 0 -- success; 1 -- error
# def get_status_relay():
#     pass


class USBRelayController(object):
    def __init__(self, device, timeout=5000):
        self.device = device
        self.timeout = timeout

        if self.device is not None:
            self.product = usb.util.get_string(device, device.iProduct)
            self.num_relays = int(self.product[8:])
            self._update_status()
            self.status = True
        else:
            self.product = None
            self.num_relays = None
            self.status = False

        self.aliases = {}
        self.defaults = {}
        self.relay_mapping = {}

        # set relay mapping / configuration
        config_file_path = "EEequipment/usbrelay/config.ini"
        if os.path.exists(config_file_path):
            self.read_relay_config(config_file_path)
            self.print_relay_mappings()
        else:
            print(f"Configuration file {config_file_path} does not exist.")
            raise BaseException

    # TODO: really understand the following code. Why is there a for loop? Can I just not read every channel instance?
    def read_relay_config(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)

        for i in range(1, 9):
            channel_key = f'channel_{i}'
            if config.has_option('RELAY_CHANNELS', channel_key):
                self.relay_mapping[channel_key] = config.get('RELAY_CHANNELS', channel_key)
            if config.has_option('RELAY_CONNECT', channel_key):
                self.relay_mapping[f"state_{i}"] = config.get('RELAY_CONNECT', channel_key)

    def print_relay_mappings(self):
        for channel, connection in self.relay_mapping.items():
            if connection:
                print(f"{channel}: {connection}")
            else:
                print(f"{channel}: Not configured")

    def get_relay_mapping(self, relay):
        return self.relay_mapping[f'channel_{relay}']

    def get_relay_map_state(self, relay):
        return self.relay_mapping[f'state_{relay}']

    def return_channel(self, mapping):
        # returns the channel number for a certain "mapping" string
        channel = next((channel for channel, device in self.relay_mapping.items() if device == mapping), None)
        print(f'The channel for {mapping} is: {channel}')
        return int(channel[-1])

    def get_property(self, relay, name, default=None):
        value = self.defaults.get(name, default)
        if relay != "all" and relay in self.aliases:
            value = self.aliases[relay].get(name, value)
        return value

    def set_serial(self, new_serial):
        buf = array.array("B")
        buf.append(0xFA)
        serial = new_serial.encode("utf-8")
        for i in range(5):
            if i < len(serial):
                buf.append(serial[i])
        self._set_hid_report(MAIN_REPORT, buf)

        self._update_status()

    def _update_status(self):
        data = self._get_hid_report(MAIN_REPORT, 8)
        try:
            self.serial = data[0:5].tobytes().rstrip(b"\x00").decode("utf-8")
        except UnicodeDecodeError:
            self.serial = "".join("%02x" % b for b in data[0:5])
        self.state = data[7]

    def _name_to_number(self, relay):
        # NO IDEA WHAT THIS FUNCTION DOES
        def convert():
            invert = self.defaults.get("invert", False)

            try:
                if relay in self.aliases:
                    return (
                        int(self.aliases[relay]["relay"]),
                        self.aliases[relay].get("invert", invert),
                    )
                return int(relay), invert
            except ValueError:
                pass

            raise ValueError("'%s' is not a valid relay descriptor" % relay)

        relay_num, invert = convert()
        if relay_num < 1 or relay_num > self.num_relays:
            raise IndexError(
                "Index %r is outside range [1..%d]" % (relay_num, self.num_relays)
            )
        return relay_num

    def _name_to_index(self, relay):
        relay_num = self._name_to_number(relay)
        return relay_num - 1

    def get_state(self, relay):
        self._update_status()
        idx = self._name_to_index(relay)
        invert = self.get_property(relay, "invert", False)

        if self.state & (1 << idx):
            return xor(True, invert)
        return xor(False, invert)

    def get_state_state(self, relay):
        state_tf = self.get_state(relay)

        # if relay is being driven
        relay_wiring = self.get_relay_map_state(relay)
        if state_tf:
            if relay_wiring == "NO":
                return True
        else:
            if relay_wiring == "NC":
                return True

        return False

    def set_state(self, relay, state):
        buf = array.array("B")
        invert = self.get_property(relay, "invert", False)
        if relay == "all":
            buf.append(0xFE if xor(state, invert) else 0xFC)
        else:
            relay_num = self._name_to_number(relay)
            buf.append(0xFF if xor(state, invert) else 0xFD)
            buf.append(relay_num)

        self._set_hid_report(MAIN_REPORT, buf)

    def toggle_state(self, relay):
        if relay == "all":
            for i in range(1, self.num_relays + 1):
                self.set_state(i, not self.get_state(i))
        else:
            self.set_state(relay, not self.get_state(relay))

    def open_all(self):
        for i in range(1, NUM_RELAY + 1):
            self.set_state(i, 0)

    def close_all(self):
        for i in range(1, NUM_RELAY + 1):
            self.set_state(i, 1)

    def __getitem__(self, relay):
        return self.get_state(relay)

    def __setitem__(self, relay, state):
        self.set_state(relay, state)

    def _get_hid_report(self, report, size):
        return self.device.ctrl_transfer(
            USB_TYPE_CLASS | USB_RECIP_DEVICE | USB_ENDPOINT_IN,
            GET_REPORT,
            (USB_HID_REPORT_TYPE_FEATURE << 8) | report,
            0,
            size,
            self.timeout,
        )

    def _set_hid_report(self, report, data):
        data = data[:]
        while len(data) < 8:
            data.append(0x00)

        return self.device.ctrl_transfer(
            USB_TYPE_CLASS | USB_RECIP_DEVICE | USB_ENDPOINT_OUT,
            SET_REPORT,
            (USB_HID_REPORT_TYPE_FEATURE << 8) | report,
            0,
            data,
            self.timeout,
        )
