
import re




def parse_voltage_str(voltage_str):
    # Strip out non-numeric characters
    numeric_part = re.sub(r'[^\d.]', '', voltage_str)
    # Convert the numeric part to a float
    voltage_float = float(numeric_part)
    # Scale the float value based on the unit (mV in this case)
    scaled_voltage = voltage_float * 1000  # Since 1 mV = 0.001 V
    return scaled_voltage
