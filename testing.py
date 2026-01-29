
# import needed modules
import time
from time import localtime, strftime
import pyvisa

# import user created modules
from analysis.csv_helper import CSVHelper
from EEequipment.E3640A.E3640A import E3640A
from EEequipment.fluke8842A.fluke8842A import Fluke8842A
from EEequipment.hp3478A.hp3478A import HP3478A

from EEequipment.TestEquipment import SerialHandler


# pyvisa stuff
rm = pyvisa.ResourceManager()
print(rm.list_resources())


# connect to power supply and DMM
ps = E3640A("GPIB0::5::INSTR")
dmm1 = Fluke8842A("GPIB0::2::INSTR")
dmm2 = HP3478A("GPIB0::23::INSTR")
ser = SerialHandler()
ser.connect("COM8", None)
ser.set_timeout(None)


time.sleep(5)


### *IDN? TEST
print(f"PS ID query: {ps.test_conn()}")
# print(f"PS DMM query: {dmm.test_conn()}")
print(f"PS DMM2 read: {dmm2.read_value()}")


# SET UP CSV RECORDING STUFF
board = 12
ind = 68
temp = 25
load = 500
recName = f"AREC_b{board}_{temp}_{ind}uH_{strftime('%m%d%H%M', localtime())}.csv"
print(f"Starting DMM/PS record ...")
data_dir = "data/data/"
csvh = CSVHelper(data_dir + recName)
csvh.initialize_file(["V_set", "V_tp", "I_in", "P_in", "V_out", "P_out", "Load", "PWM", "Duty", "Deadtime", "ADC_V_out", "ADC_VCC"])


# SET UP PARAMETERS
listMode = [0.35]
samples = 3
delay_between_samples = 0


# PERFORM TEST
# generate voltage level output in sequence
ps.output_off(1)
time.sleep(5)
ps.set_voltage(0.55)
ps.output_on(1)


for v in listMode:
    print(f"Starting test at voltage: {v}")
    ps.set_voltage(v)
    time.sleep(1)

    line = ""
    while line != "EXIT":
        line = ser.read(decode=True)
        print(line)
        part = line.split(",")

        v1_sum = 0.0
        v2_sum = 0.0
        current_sum = 0.0
        for _ in range(samples):
            current = ps.get_current(1)  # Assuming ps has a get_current() method
            v1 = dmm1.read_value()  # Assuming ps has a get_voltage() method
            v2 = dmm2.read_value()

            v1_sum += v1
            v2_sum += v2
            current_sum += current
            time.sleep(delay_between_samples)

        avg_v1 = v1_sum / samples
        avg_v2 = v2_sum / samples
        avg_current = current_sum / samples
        p_in = v * avg_current
        p_out = (avg_v1 ** 2) / float(load)

        try:
            csvh.add_row([v, avg_v2, avg_current, p_in, avg_v1, p_out, load, part[0], part[1], part[2], part[3], part[4]])
        except IndexError:
            print(f"Couldn't add a sample with parts looking like: {part}")


# Close Connection
print("Closing connections ...")
ps.output_off(1)
ps.disconnect()
dmm1.disconnect()
dmm2.disconnect()

