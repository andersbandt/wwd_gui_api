

# import needed modules
import numpy as np
import time


# set up power supply
ps = # somehow grab model ?? User has to manually specify?


# parameters
Vfinal = 5
tau = 37.5
N = 100

t = np.linspace(0, 1, N)
V = Vfinal * (1 - np.exp(-t / tau))


# TODO: somehow correlate the tau value to


# increment through voltages
for voltage in V:
    ps.set_voltage(voltage)
    time.sleep(0.01)









