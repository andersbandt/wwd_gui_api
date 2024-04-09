

from common import subprocessor
from common import plotter

basefilepath = "C:/Users/ander/Downloads/"
filename = "test2.csv"
filepath = basefilepath + filename


pd_frame = subprocessor.load_csv(filepath, columns=['timestamp', 'ms'])
time_series = subprocessor.create_datetime(pd_frame["timestamp"])


time_diff = []

offset = time_series[0].timestamp()
print(f"Time offset is: {offset}")

i = 0
for mcu_time in pd_frame['ms']:
    time_diff.append(mcu_time/1000 - time_series[i].timestamp() + offset)
    i += 1


plotter.time_plot(time_series, time_diff)





print("I'm fucking done!!!")



