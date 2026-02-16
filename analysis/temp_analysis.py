"""Temperature sensor data conversion."""


def analyze_ICM_42670(dig_temp_arr):
    temp_fahr = []
    for temp in dig_temp_arr:
        temp_f = ((temp/128) + 25)*1.8 + 32
        temp_fahr.append(temp_f)
    return temp_fahr


