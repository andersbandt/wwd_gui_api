"""
@file     logger.py
@author   Anders Bandt
@date     April 2024
@brief    handle logging of application to output files
"""

# import needed modules
import logging
from analysis import csv_helper as csvh
import os
from time import strftime, localtime
from fpdf import FPDF
from datetime import datetime
from dataclasses import dataclass

from analysis.csv_helper import CSVHelper
from enum import Enum
import numpy as np

log_folder = "data" # master program folder for all output data. tag:hardcode


#################################
#### file stuff  ################
#################################

def build_log_name(prefix, file_str_ext):
    # FILENAME SETUP
    recName = prefix + "_" + strftime('%Y%m%d%H%M%S', localtime())
    if file_str_ext is not None:
        recName += "_" + file_str_ext
    recName += ".csv"
    return recName


# TODO: evaluate this function compared to the more recent one above
def get_filename(basefilepath, folder, name_ext, extension):
    current_datetime = datetime.now()
    date_strf = "%Y%m%d"
    formatted_datetime = current_datetime.strftime(date_strf)
    if name_ext is None:
        name_ext = ""
    filename = f"{basefilepath}/{log_folder}/{folder}/_{formatted_datetime}_{name_ext}.{extension}"
    return filename


#################################
#### .log (text_data)  ##########
#################################

def init_text(basefilepath, data_folder, start_msg):
    filename = get_filename(basefilepath, # basefilepath
                            data_folder, # (output folder)
                            None, # name_ext
                            "log") # .extension
    open_text(filename, start_msg)
    print("Text file output started!!!")
    print("\toutput started at file: ", filename)
    return filename


def open_text(filename, log_start_msg):
    with open(filename, mode='a', newline='') as file:
        file.write(log_start_msg)


def append_text(filename, data):
    with open(filename, mode='a', newline='') as file:
        file.write(data)


#################################################
#### AAL (advanced abstracted logging  ##########
#################################################

@dataclass
class RecordConfig:
    use_ser: bool = False
    use_dmm: bool = False
    use_ps: bool = False
    use_fg: bool = False
    ps_channels: int = 1  # will be set to 2 if user confirms and PS supports it
    serial_params: str = None


def create_record_config(use_ser, use_dmm, use_ps, use_fg, ps_channels, serial_params):
    config = RecordConfig(use_ser=use_ser, use_dmm=use_dmm, use_ps=use_ps, use_fg=use_fg, ps_channels=ps_channels, serial_params=serial_params)
    return config


#################################
#### STIMULUS LOGGING  ##########
#################################

class StimulusType(Enum):
    """Types of stimulus that can be swept"""
    NONE = "None"
    PS_VOLTAGE = "PS Voltage"
    FG_FREQUENCY = "FG Frequency"
    FG_DUTY_CYCLE = "FG Duty Cycle"


class SweepMode(Enum):
    """How the sweep progresses"""
    LINEAR = "Linear"
    LOGARITHMIC = "Logarithmic"


@dataclass
class StimulusConfig:
    """Configuration for stimulus-based logging"""
    enabled: bool = False
    stimulus_type: StimulusType = StimulusType.NONE
    sweep_mode: SweepMode = SweepMode.LINEAR
    start_value: float = 0.0
    stop_value: float = 0.0
    step_value: float = 0.0
    settling_time: float = 0.5  # Time to wait after changing stimulus before logging (seconds)
    ps_channel: int = 1  # Which PS channel to sweep (if PS_VOLTAGE)

    def validate(self):
        """Validate the stimulus configuration"""
        if not self.enabled:
            return True, ""

        if self.stimulus_type == StimulusType.NONE:
            return False, "Please select a stimulus type"

        if self.start_value == self.stop_value:
            return False, "Start and stop values cannot be the same"

        if self.step_value <= 0:
            return False, "Step value must be positive"

        if self.settling_time < 0:
            return False, "Settling time cannot be negative"

        # Check that step is reasonable
        if abs(self.stop_value - self.start_value) < self.step_value:
            return False, "Step size is larger than sweep range"

        return True, ""


class StimulusGenerator:
    """Generates stimulus values for a sweep"""

    def __init__(self, config: StimulusConfig):
        self.config = config
        self.values = self._generate_values()
        self.current_index = 0

    def _generate_values(self):
        """Generate array of stimulus values based on configuration"""
        if not self.config.enabled:
            return []

        start = self.config.start_value
        stop = self.config.stop_value
        step = self.config.step_value

        if self.config.sweep_mode == SweepMode.LINEAR:
            # Linear sweep
            num_steps = int(abs(stop - start) / step) + 1
            values = np.linspace(start, stop, num_steps)

        elif self.config.sweep_mode == SweepMode.LOGARITHMIC:
            # Logarithmic sweep
            if start <= 0 or stop <= 0:
                raise ValueError("Logarithmic sweep requires positive values")

            # Calculate number of steps in log space
            log_start = np.log10(start)
            log_stop = np.log10(stop)
            num_steps = int(abs(log_stop - log_start) / np.log10(1 + step/start)) + 1
            values = np.logspace(log_start, log_stop, num_steps)

        else:
            raise ValueError(f"Unknown sweep mode: {self.config.sweep_mode}")

        return values.tolist()

    def __iter__(self):
        """Make the generator iterable"""
        self.current_index = 0
        return self

    def __next__(self):
        """Get next stimulus value"""
        if self.current_index >= len(self.values):
            raise StopIteration

        value = self.values[self.current_index]
        self.current_index += 1
        return value

    def __len__(self):
        """Return total number of steps"""
        return len(self.values)

    def get_progress(self):
        """Get current progress (current step, total steps)"""
        return self.current_index, len(self.values)


def parse_serial_params(raw: str):
    """
    Parse comma-separated serial params. Raises ValueError if format is invalid.
    Rules:
      - No empty segments (no leading/trailing commas, no consecutive commas)
      - Whitespace around names is allowed and stripped
    """
    raw = (raw or "").strip()
    if not raw:
        # Let caller decide how to warn; return empty list to keep logic simple.
        return []

    parts = [p.strip() for p in raw.split(",")]
    if any(p == "" for p in parts):
        raise ValueError(
            "Invalid serial parameter format. "
            "No consecutive or leading/trailing commas allowed. Example: SN,BoardRev,FW"
        )
    return parts


def build_headers(record_config: RecordConfig, stimulus_config: StimulusConfig = None):
    # SETUP CSV HEADER PARAMETERS
    headers = ["Time"]

    # Serial/user-entered metadata (if selected)
    if record_config.use_ser:
        parts = parse_serial_params(record_config.serial_params)
        if parts is None:
            return False
        headers += parts

    # DMM selected?
    if record_config.use_dmm:
        # dmm_params = ["DMM_Range", "DMM_Func1", "DMM_Meas1"]
        dmm_params = ["DMM_Meas1"]
        headers += dmm_params

    # Power Supply selected?
    if record_config.use_ps:
        ps_params = ["PS_Vset1", "PS_Vmeas1", "PS_Imeas1"]

        # TODO: have to get creative about detecting status
        # if self.cc.get_ps_status():
        if 1:
            if record_config.ps_channels > 1:
                ps_params += ["PS_Vset2", "PS_Vmeas2", "PS_Imeas2"]

        headers += ps_params

    # Function Generator selected?
    if record_config.use_fg:
        fg_params = ["FG_Freq", "FG_Waveform"]
        headers += fg_params

    # Stimulus columns (if stimulus mode enabled)
    if stimulus_config and stimulus_config.enabled:
        headers += ["Stimulus_Value", "Stimulus_Step"]

    return headers


# ---------------------------
# Orchestrator (single call)
# ---------------------------

def setup_recording(data_dir: str, prefix: str, ext_text: str, config: RecordConfig, stimulus_config: StimulusConfig = None):
    """
    High-level setup that:
      1) Creates the filename
      2) Builds the headers (may alert/confirm via callbacks)
      3) Initializes the CSV file
    Returns: (filename, headers, csv_helper, updated_config)
    """
    rec_name = build_log_name(prefix, ext_text)
    headers = build_headers(config, stimulus_config)
    csvobj = csvh.init_csvh(data_dir, rec_name, headers)
    return rec_name, csvobj


def start_recording(csvobj: CSVHelper):
    csvobj.initialize_file()
