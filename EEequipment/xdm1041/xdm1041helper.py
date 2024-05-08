
import re


# sample_input: '00.760mVDC\r\n'
def parse_voltage_str(voltage_str):
    # Strip out non-numeric characters
    numeric_part = re.sub(r'[^\d.]', '', voltage_str)
    # Convert the numeric part to a float
    voltage_float = float(numeric_part)
    # Scale the float value based on the unit
    if "mV" in voltage_str:
        scaled_voltage = voltage_float / 1000
    else:
        scaled_voltage = voltage_float
    return scaled_voltage
