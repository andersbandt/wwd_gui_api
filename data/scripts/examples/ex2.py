

# import needed modules
import time
from common.csv_helper import CSVHelper
from common.serial_api import SerialProcessor

# set up equipment connections
ps = # somehow grab model ?? User has to manually specify?
serial = SerialProcessor


# set up CSV data path
filepath = datapath_helper("serial_data")
csv = CSVHelper(filepath, ["voltage", "tp_o"])


voltages = [0.35, 0.45, 0.55, 0.65]
NUM_SAMPLES = 100


for v in voltages:
    ps.set_voltage(v)
    time.sleep(0.1)
    for i in range(0, NUM_SAMPLES):

