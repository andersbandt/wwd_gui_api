

import usb
import usb.core
import usb.util

print(usb.core.find())


# print all found devices?
dev = usb.core.find(find_all=True)
if dev is None:
    raise ValueError("device not found")
else:
    print(dev)

# Find USB device by vendor ID and product ID
vendor_id = 0x1A86  # Replace with your device's vendor ID
product_id = 0x7523  # Replace with your device's product ID

device = usb.core.find(idVendor=vendor_id, idProduct=product_id)

# if device is None:
#     raise ValueError("Device not found.")

# Set up the USB device
dev.set_configuration()
# device.set_configuration()

while (True):
    # Read data from the USB device
    endpoint = dev[0][(0, 0)][0]
    data = dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize)

    # Process the received data
    # ...

    # Print the received data
    print("Received data:", data)



