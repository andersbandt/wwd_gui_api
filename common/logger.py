"""
@file     logger.py
@author   Anders Bandt
@date     April 2024
@brief    handle logging of application to output files
"""

# import needed modules
from common import csv_helper as csvh
from time import strftime, localtime
from dataclasses import dataclass

from common.csv_helper import CSVHelper
from enum import Enum
import numpy as np


#################################
#### file stuff  ################
#################################

def build_log_name(prefix, file_name_ext, extension, date_strf='%Y%m%d%H%M%S'):
    """
    Build a timestamped log filename.

    Args:
        prefix: Prefix for the filename (e.g., "SER", "DMM")
        file_name_ext: Optional extension to add to filename (can be None or empty string)
        extension: File extension without dot (e.g., "csv", "log", "txt")
        date_strf: Date format string for timestamp

    Returns:
        str: Formatted filename (e.g., "SER_20250203_143022_test.log")

    Note: This function only generates the filename, not the full path.
          Use path_helper.get_full_data_path() to get the directory path.
    """
    # FILENAME SETUP
    recName = prefix + "_" + strftime(date_strf, localtime())
    if file_name_ext is not None:
        if file_name_ext != '':
            recName += "_" + file_name_ext
    recName += "." + extension # NOTE: this is the file type (.txt, .csv, .log, etc)
    return recName


#################################
#### .log (text_data)  ##########
#################################


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

    def pretty(self) -> str:
        """
        Return a human-friendly, aligned summary of the configuration.
        """
        # Build display dictionary (you can rename keys for clarity)
        display = {
            "Use Serial (SER)": self.use_ser,
            "Use DMM": self.use_dmm,
            "Use Power Supply (PS)": self.use_ps,
            "Use Function Generator (FG)": self.use_fg,
            "PS Channels": self.ps_channels,
            "Serial Params": self.serial_params or "(not set)",
        }

        # Compute column width for neat alignment
        key_width = max(len(k) for k in display.keys())
        lines = ["Record Configuration".upper(), "-" * (key_width + 24)]
        for k, v in display.items():
            # Pretty format booleans as On/Off
            if isinstance(v, bool):
                v_fmt = "On" if v else "Off"
            else:
                v_fmt = str(v)
            lines.append(f"{k:<{key_width}} : {v_fmt}")
        return "\n".join(lines)

    def print(self) -> None:
        """Print the pretty summary to stdout."""
        print(self.pretty())


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


class StepMode(Enum):
    """How to specify the step size"""
    INCREMENT = "Increment"  # User specifies step_value (increment amount)
    NUM_STEPS = "Number of Steps"  # User specifies total number of steps


@dataclass
class StimulusConfig:
    """Configuration for stimulus-based logging"""
    enabled: bool = False
    stimulus_type: StimulusType = StimulusType.NONE
    sweep_mode: SweepMode = SweepMode.LINEAR
    step_mode: StepMode = StepMode.INCREMENT  # How to specify steps
    start_value: float = 0.0
    stop_value: float = 0.0
    step_value: float = 0.0  # Used when step_mode = INCREMENT
    num_steps: int = 10  # Used when step_mode = NUM_STEPS
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

        # Validate based on step mode
        if self.step_mode == StepMode.INCREMENT:
            if self.step_value <= 0:
                return False, "Step value must be positive"
            # Check that step is reasonable
            if abs(self.stop_value - self.start_value) < self.step_value:
                return False, "Step size is larger than sweep range"
        elif self.step_mode == StepMode.NUM_STEPS:
            if self.num_steps < 2:
                return False, "Number of steps must be at least 2"

        if self.settling_time < 0:
            return False, "Settling time cannot be negative"

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

        # Determine number of steps based on step_mode
        if self.config.step_mode == StepMode.INCREMENT:
            # Calculate num_steps from step_value (increment)
            step = self.config.step_value
            num_steps = int(abs(stop - start) / step) + 1
        elif self.config.step_mode == StepMode.NUM_STEPS:
            # Use user-specified num_steps
            num_steps = self.config.num_steps
        else:
            raise ValueError(f"Unknown step mode: {self.config.step_mode}")

        # Generate values based on sweep_mode
        if self.config.sweep_mode == SweepMode.LINEAR:
            # Linear sweep
            values = np.linspace(start, stop, num_steps)

        elif self.config.sweep_mode == SweepMode.LOGARITHMIC:
            # Logarithmic sweep
            if start <= 0 or stop <= 0:
                raise ValueError("Logarithmic sweep requires positive values")

            log_start = np.log10(start)
            log_stop = np.log10(stop)
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


@dataclass
class DualStimulusConfig:
    """Configuration for dual-parameter stimulus sweeps (nested loops)"""
    enabled: bool = False
    outer_loop: StimulusConfig = None  # Outer loop parameter
    inner_loop: StimulusConfig = None  # Inner loop parameter

    def validate(self):
        """Validate the dual stimulus configuration"""
        if not self.enabled:
            return True, ""

        if self.outer_loop is None or self.inner_loop is None:
            return False, "Both outer and inner loop configurations are required"

        # Validate outer loop
        valid, error_msg = self.outer_loop.validate()
        if not valid:
            return False, f"Outer loop error: {error_msg}"

        # Validate inner loop
        valid, error_msg = self.inner_loop.validate()
        if not valid:
            return False, f"Inner loop error: {error_msg}"

        # Check that stimulus types are different
        if self.outer_loop.stimulus_type == self.inner_loop.stimulus_type:
            return False, "Outer and inner loop must use different stimulus types"

        return True, ""


class DualStimulusGenerator:
    """Generates stimulus values for a dual-parameter sweep (nested loops)"""

    def __init__(self, config: DualStimulusConfig):
        self.config = config
        self.outer_gen = StimulusGenerator(config.outer_loop)
        self.inner_gen = StimulusGenerator(config.inner_loop)
        self.total_steps = len(self.outer_gen) * len(self.inner_gen)
        self.current_step = 0

    def __iter__(self):
        """Make the generator iterable, yielding (outer_value, inner_value) tuples"""
        self.current_step = 0
        for outer_val in self.outer_gen:
            # Reset inner generator for each outer value
            self.inner_gen = StimulusGenerator(self.config.inner_loop)
            for inner_val in self.inner_gen:
                self.current_step += 1
                yield (outer_val, inner_val)

    def __len__(self):
        """Return total number of steps (outer * inner)"""
        return self.total_steps

    def get_progress(self):
        """Get current progress (current step, total steps)"""
        return self.current_step, self.total_steps


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


def get_stimulus_column_name(stimulus_type: StimulusType) -> str:
    """
    Convert a StimulusType to a descriptive column name for CSV headers.

    Args:
        stimulus_type: The type of stimulus

    Returns:
        String column name (e.g., "PS_Voltage", "FG_Frequency", "FG_Duty_Cycle")
    """
    column_map = {
        StimulusType.PS_VOLTAGE: "PS_Voltage",
        StimulusType.FG_FREQUENCY: "FG_Frequency",
        StimulusType.FG_DUTY_CYCLE: "FG_Duty_Cycle",
        StimulusType.NONE: "Stimulus_Value"  # Fallback
    }
    return column_map.get(stimulus_type, "Stimulus_Value")


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

        if record_config.ps_channels > 1:
            ps_params += ["PS_Vset2", "PS_Vmeas2", "PS_Imeas2"]

        headers += ps_params

    # Function Generator selected?
    if record_config.use_fg:
        fg_params = ["FG_Freq", "FG_Waveform"]
        headers += fg_params

    # Stimulus columns (if stimulus mode enabled)
    if stimulus_config:
        if isinstance(stimulus_config, DualStimulusConfig) and stimulus_config.enabled:
            # Dual stimulus: use actual parameter names for outer and inner loops
            outer_name = get_stimulus_column_name(stimulus_config.outer_loop.stimulus_type)
            inner_name = get_stimulus_column_name(stimulus_config.inner_loop.stimulus_type)
            headers += [outer_name, inner_name, "Stimulus_Step"]
        elif isinstance(stimulus_config, StimulusConfig) and stimulus_config.enabled:
            # Single stimulus: use actual parameter name
            param_name = get_stimulus_column_name(stimulus_config.stimulus_type)
            headers += [param_name, "Stimulus_Step"]

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
    rec_name = build_log_name(prefix, ext_text, "csv")
    headers = build_headers(config, stimulus_config)
    csvobj = csvh.init_csvh(data_dir, rec_name, headers)
    return rec_name, csvobj


def start_recording(csvobj: CSVHelper):
    csvobj.initialize_file()
