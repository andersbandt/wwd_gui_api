



# import user created modules
from EEequipment import SCPI


# 1. �����к�afEd5�豸�ĵ�һ·�̵���
# CommandApp_USBRelay  afEd5 open 01
# 2. �����к�afEd5�豸�����м̵���
# CommandApp_USBRelay  afEd5 open 255
# 3. �ر����к�afEd5�豸�ĵ�һ·�̵���
# CommandApp_USBRelay  afEd5 close 01
# 4. �ر����к�afEd5�豸�����м̵���
# CommandApp_USBRelay  afEd5 close 255


USB_RELAY_NUM_CHANNEL = 8


usb_relay = SCPI.SCPI("COM3", 9600)

def open_relay(index):
    usb_relay.sendcmd(f"relay {index} on", getdata=True)


def close_relay(index):
    usb_relay.sendcmd(f"relay {index} off", getdata=True)


def open_all_relay():
    for i in range(0, USB_RELAY_NUM_CHANNEL):
        open_relay(i)


def close_all_relay():
    for i in range(0, USB_RELAY_NUM_CHANNEL):
        close_relay(i)



# status bit: High --> Low 0000 0000 0000 0000 0000 0000 0000 0000, one bit indicate a relay status.
# the lowest bit 0 indicate relay one status, 1 -- means open status, 0 -- means closed status.
# bit 0/1/2/3/4/5/6/7/8 indicate relay 1/2/3/4/5/6/7/8 status
# @returns: 0 -- success; 1 -- error
def get_status_relay():
    pass



