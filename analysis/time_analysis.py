
# import needed modules
from datetime import datetime



####################################
###   Time stuff       #############
####################################

datetime_format = "%Y-%m-%d %H:%M:%S.%f"  # need to add an extra space at the end because of my printout?


def create_datetime(timestamp_array):
    datetime_arr = []
    for timestamp_str in timestamp_array:
        tmp = datetime.strptime(timestamp_str, datetime_format)
        datetime_arr.append(tmp)
    return datetime_arr



def analyze_time(dtime_arr):
    duration = dtime_arr[-1] - dtime_arr[0]

    num_samples = len(dtime_arr)

    return {
        "dur_sec": duration.total_seconds(),
        "dur_min": duration.total_seconds() / 60,
        "samples": num_samples,
        "frequency": num_samples / duration.total_seconds(),
    }