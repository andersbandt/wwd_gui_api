
# import needed modules
import time
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
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


ps.output_on(1)
ps.set_voltage(0.4)


# Sweep parameters
freq_start, freq_stop, freq_samples = 40000, 220000, 30
duty_start, duty_stop, duty_samples = 20, 80, 20

# Generate arrays
freq_arr = np.linspace(freq_start, freq_stop, freq_samples)
duty_arr = np.linspace(duty_start, duty_stop, duty_samples)

# Simulated output voltage (replace with actual measurements)
vdds = []
for f in freq_arr:
    fg.set_frequency(f)
    time.sleep(1)
    row = []
    for d in duty_arr:
        fg.set_duty(d)
        time.sleep(1.5)
        voltage = dmm.read_value()
        row.append(voltage)
    vdds.append(row)

vdds = np.array(vdds)

# Meshgrid for plotting
FREQ, DUTY = np.meshgrid(duty_arr, freq_arr)

# 3D plot
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection='3d')
surf = ax.plot_surface(FREQ, DUTY, vdds, cmap='viridis')

ax.set_title('Frequency vs Duty Cycle vs Output Voltage')
ax.set_xlabel('Duty Cycle (%)')
ax.set_ylabel('Frequency (Hz)')
ax.set_zlabel('Output Voltage (V)')
fig.colorbar(surf, shrink=0.5, aspect=10, label='Voltage (V)')


plt.show()

# Close Connection
print("Closing connections ...")
ps.output_off(1)
ps.disconnect()
dmm.disconnect()
fg.disconnect()