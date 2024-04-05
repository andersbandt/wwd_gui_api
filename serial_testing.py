from time import sleep

from common.Serial import Serial
from common import xds110_api


# ser_obj = Serial("COM13", 115200)

result = xds110_api.xds110_jtag_reset()
print(result)

while True:
    pass
    # print("... heartbeat ...")
    # if ser_obj.serObj.inWaiting() > 0: # Wait here until there is data
    # ser_obj.get_data(printmode=True)
    # ser_obj.send_data("DADA")
    # sleep(1)



