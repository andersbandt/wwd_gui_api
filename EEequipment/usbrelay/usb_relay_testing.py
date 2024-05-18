

#######################################################
########## METHOD 1: pyhid_usb_relay      #############
#######################################################

# import modules
# import pyhid_usb_relay
#
# try:
#     relay = pyhid_usb_relay.find()
# except pyhid_usb_relay.exceptions.DeviceNotFoundError as e:
#     print("Can't find device!")
#     raise(e)
#
#
# print(bin(relay.state))
# print("Toggling relay")
#
#
# for i in range(1, 9):
#     relay.toggle_state(i)
#
# print(bin(relay.state))



#######################################################
########## METHOD 2:     mine!!!!         #############
#######################################################

import usb.core
import usb.util


from EEequipment.usbrelay import usbrelay_controller


VENDOR_ID = 0x16C0
PRODUCT_ID = 0x05DF


def _get_backend():
    import os

    if os.name != "nt":
        return None

    import usb.backend.libusb1
    import libusb
    import pathlib

    # Manually find the libusb DLL and create a backend using it. I don't know
    # why Python can't find this on its own
    libpath = next(pathlib.Path(libusb.__file__).parent.rglob("x64/libusb-1.0.dll"))
    return usb.backend.libusb1.get_backend(find_library=lambda x: str(libpath))



class match_relay(object):
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
    custom_match=match_relay(),
)


usb_relay = usbrelay_controller.USBRelayController(devices)


print(usb_relay.state)

for i in range(1, 9):
    usb_relay.toggle_state(i)
    # usb_relay.set_state(i, 1)


print(usb_relay.state)



