
# import needed modules
from common.logger import StimulusConfig
from common.serial_api import SerialProcessor

# set up connection to oven controller
oven = OvenController # NOTE: this is not setup but assume it works
ser = SerialProcessor()


ramp = StimulusConfig


# NOTE: will be interesting how I manage transfering this custom array into commands formatted properly for the oven controller?
ramp.CUSTOM_POINTS = {
    "SET", 5, 10 # HOLD at 5 degrees for 10 minutes
    "RAMP", 70, 30, # RAMP to 70 degrees over 30 minutes
    "SET", 70, 10,
    "RAMP", 220, 30 # RAMP to 220 degrees over 30 minutes
}


for item in ramp.CUSTOM_POINTS:
    # do ramp points
    # take serial data the whole time as well





