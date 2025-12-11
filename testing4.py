
# import needed modules
import time
from time import localtime, strftime

# import user created modules
from analysis.csv_helper import CSVHelper
from EEequipment.E3640A.E3640A import E3640A
from EEequipment.fluke8842A.fluke8842A import Fluke8842A


# connect to power supply and DMM
ps = E3640A("GPIB0::5::INSTR")
dmm = Fluke8842A("GPIB0::2::INSTR")


### *IDN? TEST
print(f"PS ID query: {ps.test_conn()}")
# print(f"PS DMM query: {dmm.test_conn()}")


# SET UP CSV RECORDING STUFF
board = 10
pwm_freq = 32
ind = 68
temp = 25
recName = f"AREC_b{board}_{temp}_{pwm_freq}kHz_{ind}uH_{strftime('%m%d%H%M', localtime())}.csv"
print(f"Starting DMM/PS record ...")
data_dir = "data/data/"
csvh = CSVHelper(data_dir + recName)
csvh.initialize_file(["V_set", "I_in", "P_in", "V_out", "Load", "P_out"])


def thermopile_ramp():
    start_voltage = 0.0  # volts
    end_voltage = 0.45  # volts
    duration = 20  # seconds
    steps = 100  # number of increments

    # Calculate step size and delay
    voltage_step = (end_voltage - start_voltage) / steps
    delay = duration / steps

    # Ramp the voltage
    current_voltage = start_voltage
    for _ in range(steps + 1):
        ps.set_voltage(current_voltage)
        time.sleep(delay)
        current_voltage += voltage_step


# PERFORM TEST
# generate voltage level output in sequence
listMode = [0.25, 0.35, 0.45, 0.55, 0.65]
samples = 10
delay_between_samples = 0.01

print(f"Ramping thermopile")
ps.set_voltage(0)
#ps.output_on(1)
thermopile_ramp()
time.sleep(5)

# time.sleep(2)
# for v in listMode:
#     print(f"Writing test voltage ... {v}")
#     ps.set_voltage(v)
#     time.sleep(0.5)
#
#     load = input("Please enter load value: ")
#     if load == "q":
#         break
#
#     voltage_sum = 0.0
#     current_sum = 0.0
#     for _ in range(samples):
#         current = ps.get_current(1)  # Assuming ps has a get_current() method
#         voltage = dmm.read_value()  # Assuming ps has a get_voltage() method
#
#         voltage_sum += voltage
#         current_sum += current
#         time.sleep(delay_between_samples)
#
#     avg_voltage = voltage_sum / samples
#     avg_current = current_sum / samples
#     p_in = v * avg_current
#     p_out = (avg_voltage ** 2) / float(load)
#
#     csvh.add_row([v, avg_current, p_in, avg_voltage, load, p_out])


# Close Connection
print("Closing connections ...")
#ps.output_off(1)
ps.set_voltage(0)
ps.disconnect()
dmm.disconnect()