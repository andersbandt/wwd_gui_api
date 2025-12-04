
# import needed modules
import time
import numpy as np
import matplotlib.pyplot as plt
from time import localtime, strftime

# import user created modules
from analysis.csv_helper import CSVHelper
from EEequipment.E3640A.E3640A import E3640A
from EEequipment.fluke8842A.fluke8842A import Fluke8842A
from EEequipment.Agilent33120A.Agilent33120A import Agilent33120A


# connect to power supply and DMM
ps = E3640A("GPIB0::5::INSTR")
dmm = Fluke8842A("GPIB0::2::INSTR")
fg = Agilent33120A("GPIB0::10::INSTR")



### *IDN? TEST
print(f"PS ID query: {ps.test_conn()}")
print(f"FG ID query: {fg.test_conn()}")

fg.clear()


# Parameters
freq = 155000
duty = 70
tp = 0.4


# start = 20       # starting value
# stop = 80      # ending value
# step = 1        # increment (x)
start = 40000
stop = 220000
samples = 30


ps.output_on(1)
ps.set_voltage(tp)

fg.set_frequency(freq)
fg.set_duty(70)

# Generate array to sweep
arr = np.linspace(start, stop, samples)  # evenly spaced values
print(arr)


vdds = []
for v in arr:
    #fg.set_duty(v)
    fg.set_frequency(v)
    time.sleep(2)
    vdds.append(dmm.read_value())


# make final plot
plt.figure(figsize=(8, 5))
plt.plot(arr, vdds, marker='o', linestyle='-', color='b')

#plt.title(f'Duty Cycle vs Output Voltage at TP={tp} and F={freq}')
#plt.xlabel('Duty Cycle (%)')

plt.title(f"Frequency vs VCC at TP={tp} and D={duty}")
plt.xlabel("Frequency (Hz)")

plt.ylabel('Output Voltage (V)')
plt.grid(True)
plt.show()



# Close Connection
print("Closing connections ...")
ps.output_off(1)
ps.disconnect()
dmm.disconnect()
fg.disconnect()