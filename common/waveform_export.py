"""Write downloaded oscilloscope waveforms to disk as CSV or MATLAB .mat.

Input is what the scope drivers' get_waveform_data() returns, one per channel:

    {channel_number: {"x": [...], "y": [...], "preamble": {...}}}

Channels on one acquisition normally share a time base, so they get one time
column (CSV) or one `t` vector (.mat). If they don't -- different record
lengths or sample intervals -- each channel gets its own time axis instead of
being forced onto a shared one that would misplace samples.
"""

import numpy as np
import pandas as pd
from scipy.io import savemat

FORMATS = ("csv", "mat")


def shares_time_base(waves):
    """True if every channel has the same length, start time and sample interval."""
    first = None
    for wave in waves.values():
        p = wave["preamble"]
        key = (len(wave["y"]), p["x_origin"], p["x_increment"])
        if first is None:
            first = key
        elif key != first:
            return False
    return True


def write(path, waves, fmt, meta=None):
    """Write `waves` to `path` in `fmt` ("csv" or "mat"). Returns the path."""
    if not waves:
        raise ValueError("No waveforms to write")
    if fmt == "csv":
        write_csv(path, waves)
    elif fmt == "mat":
        write_mat(path, waves, meta)
    else:
        raise ValueError(f"Unknown waveform format '{fmt}' (expected one of {FORMATS})")
    return path


def write_csv(path, waves):
    """Columns: time_s, CH1, CH2, ... -- or time_CHn_s, CHn pairs if time bases differ.

    Values are in the channel's vertical units (volts, or amps on a current
    probe), so column names carry no unit. Unequal-length channels are padded
    with blanks.
    """
    columns = {}
    if shares_time_base(waves):
        columns["time_s"] = np.asarray(next(iter(waves.values()))["x"], dtype=float)
        for ch in sorted(waves):
            columns[f"CH{ch}"] = np.asarray(waves[ch]["y"], dtype=float)
    else:
        for ch in sorted(waves):
            columns[f"time_CH{ch}_s"] = np.asarray(waves[ch]["x"], dtype=float)
            columns[f"CH{ch}"] = np.asarray(waves[ch]["y"], dtype=float)

    # Series (not a dict of arrays) so channels of different length pad with NaN.
    df = pd.DataFrame({name: pd.Series(values) for name, values in columns.items()})
    # 10 significant digits keeps sub-ns time resolution on a ms-scale record
    # without writing 17 digits of float noise per value.
    df.to_csv(path, index=False, float_format="%.10g", na_rep="")


def write_mat(path, waves, meta=None):
    """Variables: t (or t_CHn), CH1..CHn, fs (sample rate, Hz), and a `meta` struct.

    `meta` holds the capture details (model, name, user fields) so the file is
    self-describing once it leaves the run folder.
    """
    data = {}
    shared = shares_time_base(waves)
    for ch in sorted(waves):
        wave = waves[ch]
        data[f"CH{ch}"] = np.asarray(wave["y"], dtype=float).reshape(-1, 1)
        if not shared:
            data[f"t_CH{ch}"] = np.asarray(wave["x"], dtype=float).reshape(-1, 1)
        data[f"CH{ch}_y_increment"] = float(wave["preamble"]["y_increment"])

    first = waves[min(waves)]
    if shared:
        data["t"] = np.asarray(first["x"], dtype=float).reshape(-1, 1)
    x_inc = float(first["preamble"]["x_increment"])
    data["fs"] = 1.0 / x_inc if x_inc else 0.0
    data["channels"] = np.array(sorted(waves), dtype=float)
    # MATLAB struct fields must be strings; None isn't representable.
    data["meta"] = {k: ("" if v is None else str(v)) for k, v in (meta or {}).items()}

    savemat(path, data, do_compression=True)
