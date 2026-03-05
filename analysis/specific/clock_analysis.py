"""Clock and time-domain analysis."""

from __future__ import annotations

# import needed modules
import logging
import os
import shutil
from dataclasses import dataclass
from pprint import pformat

import numpy as np
import pandas as pd

# import user created modules
from analysis import data_helper as datah
from analysis import stats_analysis
from analysis.specific import imu_analysis
from analysis.specific import least_squares
from common import plotter
from common.plotter import show_plots


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Data cleaning / loading helpers
# ---------------------------------------------------------------------------

def clean_data(df, column, column2=None):
    _logger.info("Cleaning data ....")
    _logger.debug(f"data starting with row count: {df.shape[0]}")
    # drop out nAn values
    df = df.replace('', np.nan)
    df = df.dropna()

    # Filter out data points that fall below the lower threshold or above the upper threshold
    # NOTE: the .shift() command moves towards the end of the series by default
    df = df[df[column] >= df[column].shift(1)]
    df = df[df[column] >= df[column].shift(1)]
    df = df[df[column] >= df[column].shift(1)]

    _logger.debug(f"filter on column '{column}' yields row count: {df.shape[0]}")

    temp_shift = 10  # max shift between temp samples allowed
    if column2:
        df = df[df[column2] - df[column2].shift(1) <= temp_shift]
        df = df[df[column2] - df[column2].shift(1) <= temp_shift]
        _logger.debug(f"filter on column '{column2}' yields row count: {df.shape[0]}")

    # reset the starting value to be at 0
    min_value = df[column].min()
    result = df[column] - min_value
    df[column] = result

    return df


def get_filtered_data(data_arr, interest_column):
    interest_arr = data_arr[interest_column]
    interest_arr = np.array(interest_arr)

    filtered_indices = []

    # calculate z scores
    window_size = 10
    for i in range(len(interest_arr)):
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(interest_arr), i + window_size // 2 + 1)
        window = interest_arr[start_idx:end_idx]

        local_mean = np.mean(window)
        local_std = np.std(window)

        z_score = np.abs((interest_arr[i] - local_mean) / local_std)
        _logger.debug(z_score)

        # If the z-score exceeds the threshold, mark the index for removal
        threshold = 0.01
        if z_score > threshold:
            filtered_indices.append(i)

    # Remove rows with filtered indices
    data_arr_f = data_arr.drop(filtered_indices)

    return data_arr_f


def get_train_data(
    file,
    col_str,                # list[str]: columns to load
    float_cols=None,        # list[str] to cast to float
    clean_cols=None,        # list[str] to clean with your clean_data()
    *,
    loop_col="BO",          # str: binary 0/1 column for clamp
    volt_col="TP",          # str: continuous voltage column
    window=30,              # int: pre-activation samples for baseline
    min_samples=10,         # int: minimum samples to accept baseline
    use_median=True         # bool: use median (robust) or mean
):
    """
    Load and prepare a DataFrame with baseline features for a clamp loop.

    Adds columns:
      _baseline          : baseline computed from pre-activation window (NaN if not active/insufficient)
      _baseline_filled   : baseline filled with var4 when NaN
      _baseline_valid    : 1 if baseline valid for that row, else 0
      _delta             : _baseline_filled - var4
      _rising_idx        : 1 at 0->1 rising edge rows, else 0
    """
    # 0) Load & prep
    df = datah.load_csv_pandas(file, columns=col_str)

    if float_cols:
        for col in float_cols:
            df = datah.df_float(df, col)

    if clean_cols:
        for col in clean_cols:
            df = clean_data(df, col)

    # 1) Sanity checks
    for col in (loop_col, volt_col):
        if col not in df.columns:
            raise KeyError(f"Column '{col}' not found. Available: {list(df.columns)}")

    # 2) Extract arrays
    loop = df[loop_col].to_numpy().astype(np.int8)        # (N,)
    var4 = df[volt_col].to_numpy().astype(np.float64)     # (N,)
    N = len(df)

    # 3) Rising edges: indices where loop changes 0 -> 1
    rising = np.flatnonzero((loop[1:] == 1) & (loop[:-1] == 0)) + 1

    # 4) Compute baseline per active episode
    baseline = np.full(N, np.nan, dtype=np.float64)

    for idx in rising:
        start = max(0, idx - window)
        window_vals = var4[start:idx]
        if window_vals.size >= min_samples:
            base = np.median(window_vals) if use_median else np.mean(window_vals)
            # forward-fill while loop is active
            end = idx
            while end < N and loop[end] == 1:
                end += 1
            baseline[idx:end] = base
        # else: leave as NaN (insufficient pre-samples)

    # 5) Fill/flags/derived
    baseline_valid = (~np.isnan(baseline)).astype(np.float64)
    baseline_filled = np.where(np.isnan(baseline), var4, baseline)
    delta = baseline_filled - var4

    # 6) Attach to df
    df["_baseline"] = baseline
    df["_baseline_filled"] = baseline_filled
    df["_baseline_valid"] = baseline_valid
    df["_delta"] = delta
    df["_rising_idx"] = 0
    if len(rising) > 0:
        df.loc[rising, "_rising_idx"] = 1

    return df


def get_truth_data(file, col_str):
    df = datah.load_csv_pandas(file, columns=col_str)
    truth = df[col_str]
    return truth


def _plot_clamp_results(df, res, phase):
    """Shared plot helper for clamp loop — call with phase='Train' or 'Verify'."""
    idx = list(range(len(df)))
    plotter.plot_subplots(
        idx,
        channels=[
            (res,         "Residual"),
            (df["TP_O"],  "TP_O"),
            (df["TP"],    "TP (V)"),
            (df["BO"],    "BO (0/1)"),
        ],
        xlabel="Sample",
        title=f"{phase}: Clamp Loop Results",
        show_plot=False,
    )


def _plot_clock_drift_results(df, time_offset_arr, residual, phase):
    """Shared plot helper for clock drift — call with phase='Train' or 'Verify'.

    Uses datetime x-axis when available (verify), falls back to sample index (train).
    """
    temp_f_arr = imu_analysis.analyze_ICM_42670(df["temp"])

    if "dtsecond_zero" in df.columns:
        x_offset, xlabel_offset = df["dtsecond_zero"], "Datetime seconds"
    else:
        x_offset, xlabel_offset = list(range(len(df))), "Sample"

    if "datetime" in df.columns:
        x_dt, xlabel_dt = df["datetime"], "Datetime"
    else:
        x_dt, xlabel_dt = list(range(len(df))), "Sample"

    color      = "red"    if phase == "Verify" else None
    temp_color = "orange" if phase == "Verify" else "purple"

    plotter.plot(x_offset, time_offset_arr, xlabel=xlabel_offset, ylabel="Offset (ms)",    title=f"{phase}: Time offset (MCU vs wall clock)", color=color,      show_plot=False)
    plotter.plot(x_dt,     temp_f_arr,      xlabel=xlabel_dt,     ylabel="Temp (°F)",      title=f"{phase}: Temperature (ICM-42670)",         color=temp_color, show_plot=False)
    plotter.plot(x_dt,     residual,        xlabel=xlabel_dt,     ylabel="Residual (ms)",  title=f"{phase}: Residual (ms)",                   color=color,      show_plot=False)


def create_time_offset(mcu_time_arr, real_time):
    # calculate offset for x=0 to be y=0
    offset = -1 * (mcu_time_arr[0]) + real_time[0] * pow(10, 3)

    # calculate time delta
    i = 0
    time_diff = []
    for mcu_time in mcu_time_arr:
        time_diff.append(mcu_time - real_time[i] * pow(10, 3) + offset)
        i += 1

    return time_diff


def full_create_time_offset(df_tmp):
    time_offset = []
    dt_tmp = stats_analysis.create_datetime(df_tmp["timestamp"])
    dt_seconds = [date.timestamp() for date in dt_tmp]
    time_offset.extend(
        create_time_offset(
            np.array(df_tmp["ms"]),
            dt_seconds)
    )
    return time_offset


def linear_fit_train(x_arr, y_arr):
    # spit out linear fit
    _logger.info("Creating linear fit ....")
    stats = stats_analysis.linear_fit(x_arr, y_arr)
    _logger.info(pformat(stats))
    return stats


# ---------------------------------------------------------------------------
# Preset system
# ---------------------------------------------------------------------------

@dataclass
class AnalysisPreset:
    name: str
    columns: list
    float_cols: list | None
    clean_cols: list | None
    truth_col: list | None  # None for clock_drift (truth is computed, not a column)


PRESETS = {
    "clamp_loop": AnalysisPreset(
        name="clamp_loop",
        columns=["PV", "MV", "BO", "TP", "TP_O"],
        float_cols=None,
        clean_cols=None,
        truth_col=["TP_O"],
    ),
    "clock_drift": AnalysisPreset(
        name="clock_drift",
        columns=["timestamp", "ms", "temp"],
        float_cols=["temp"],
        clean_cols=["ms"],
        truth_col=None,  # truth is computed from timestamp vs ms
    ),
}


# ---------------------------------------------------------------------------
# Clamp loop analysis
# ---------------------------------------------------------------------------

def _train_model_clamp_loop(train_file, columns, float_col, clean_col, truth_col):
    train_df = pd.DataFrame()
    truth_df = pd.DataFrame()

    # LOAD IN AND FORMAT TRAIN DATA
    for tr_file in train_file:
        if ".csv" in tr_file:
            _logger.info(f"Loading in file: {tr_file}")
            df_train_tmp = get_train_data(tr_file, columns, float_col, clean_col)
            df_truth_tmp = get_truth_data(tr_file, truth_col)

            # concatenate new DataFrame into training data
            train_df = pd.concat([train_df, df_train_tmp], ignore_index=True)
            truth_df = pd.concat([truth_df, df_truth_tmp], ignore_index=True)

    _logger.info(f"Loaded columns: {list(train_df.columns)}")
    if _logger.isEnabledFor(logging.DEBUG):
        train_df.info()

    # VARIABLE SETUP
    A = np.column_stack((
        np.ones(len(train_df)),                                    # 1) intercept
        train_df["TP"],                                            # 2) loaded voltage (primary predictor for BO=0)
        train_df["MV"] * train_df["TP"],                          # 3) MV resistive load: scales with TP, not additive
        train_df["BO"] * train_df["_baseline_filled"],            # 4) pre-activation TP as proxy for TP_O during clamping
        train_df["BO"],                                            # 5) constant current offset from boost converter
        train_df["BO"] * train_df["MV"],                          # 6) MV interaction during clamping
    ))

    d = np.array(truth_df)
    d = d.reshape(-1, 1)
    _logger.debug("MATRIX A:\n%s", pformat(A))
    _logger.debug("MATRIX d:\n%s", pformat(d))
    _logger.info(f"Computing least squares with A matrix of shape={A.shape} dtype={A.dtype}")
    _logger.info(f"and d of shape={d.shape} dtype={d.dtype}")

    # RUN ANALYSIS
    w = least_squares.least_squares(A, d)
    w = np.array(w)
    y = A @ w  # apply A matrix to newly found coefficients

    _logger.info(f"coefs w are of shape: {w.shape}")
    _logger.info(f"shape of output y is: {y.shape}")
    _logger.info(f"coefficients (w) found from data; computed output values (y) and formed residual")
    _logger.info(f"w: {w}")

    [res, ver_e_norm] = least_squares.generate_residual(y, d)
    _logger.info(f"Euclidean norm: {ver_e_norm}")
    _logger.debug("residual:\n%s", pformat(res))

    _plot_clamp_results(train_df, res, "Train")

    return train_df, y, w


def _verify_clamp_loop(ver_file, columns, float_col, clean_col, truth_col, w):
    #####################################
    ### VERIFICATION SECTION  ###########
    #####################################
    df_ver = get_train_data(ver_file, columns, float_col, clean_col)

    A_ver = np.column_stack((
        np.ones(len(df_ver)),
        df_ver["TP"],
        df_ver["MV"] * df_ver["TP"],
        df_ver["BO"] * df_ver["_baseline_filled"],
        df_ver["BO"],
        df_ver["BO"] * df_ver["MV"],
    ))

    y_ver = A_ver @ w
    d_ver = df_ver[truth_col].to_numpy().reshape(-1, 1)

    [res, ver_e_norm] = least_squares.generate_residual(y_ver, d_ver)
    _logger.info(f"Euclidean norm of this verification data is: {ver_e_norm}")

    # GENERATE VERIFICATION PLOTS
    _logger.info("Generating verification plots...")
    _plot_clamp_results(df_ver, res, "Verify")

    return df_ver


# ---------------------------------------------------------------------------
# Clock drift analysis (merged from clock_analysis_old.py)
# ---------------------------------------------------------------------------

def _get_clock_drift_data(file, col_str, float_col, clean_col):
    """Load timestamp/ms/temp data for clock drift analysis."""
    df = datah.load_csv_pandas(file, columns=col_str)

    for col in float_col:
        df = datah.df_float(df, col)

    for col in clean_col:
        df = clean_data(df, col)

    if "timestamp" in col_str:
        df["datetime"] = stats_analysis.create_datetime(df["timestamp"])
        df["dtsecond"] = [date.timestamp() for date in df["datetime"]]

    return df


def _train_model_clock_drift(train_file):
    train_df = pd.DataFrame()
    time_offset = []

    # LOAD IN AND FORMAT TRAIN DATA
    for tr_file in train_file:
        if ".csv" in tr_file:
            _logger.info(f"Loading in file: {tr_file}")
            df_tmp = _get_clock_drift_data(tr_file, ["timestamp", "ms", "temp"], ["temp"], ["ms"])
            dt_tmp = stats_analysis.create_datetime(df_tmp["timestamp"])
            dt_seconds = [date.timestamp() for date in dt_tmp]

            # extend training time offset array
            time_offset.extend(
                create_time_offset(
                    np.array(df_tmp["ms"]),
                    dt_seconds)
            )

            # concatenate new DataFrame into training data
            train_df = pd.concat([train_df, df_tmp], ignore_index=True)

    # VARIABLE SETUP
    A = np.column_stack((
        np.ones(len(train_df)),
        train_df["ms"],
        train_df["temp"],
    ))
    d = np.array(time_offset)
    d = d.reshape(-1, 1)
    _logger.debug("MATRIX A:\n%s", pformat(A))
    _logger.debug("MATRIX d:\n%s", pformat(d))
    _logger.info(f"Computing least squares with A matrix of shape={A.shape} dtype={A.dtype}")
    _logger.info(f"and d of shape={d.shape} dtype={d.dtype}")

    # RUN ANALYSIS
    w = least_squares.least_squares(A, d)
    w = np.array(w)
    y = A @ w  # apply A matrix to newly found coefficients

    _logger.info(f"coefs w are of shape: {w.shape}")
    _logger.info(f"shape of output y is: {y.shape}")
    [residual, e_norm] = least_squares.generate_residual(y, d)
    _logger.info(f"coefficients (w) found from data; computed output values (y) and formed residual")
    _logger.info(f"w: {w}")
    _logger.info(f"Euclidean norm of this training data is: {e_norm}")

    _plot_clock_drift_results(train_df, time_offset, residual, "Train")

    return train_df


def _verify_clock_drift(ver_file, columns):
    #####################################
    ### VERIFICATION SECTION  ###########
    #####################################
    df_ver = _get_clock_drift_data(ver_file, columns, ["temp"], ["ms"])
    ver_toff = np.array(
        create_time_offset(
            np.array(df_ver["ms"]),
            df_ver["dtsecond"].tolist())
    )

    df_ver["time_offset"] = ver_toff.reshape(-1, 1)
    [res, ver_e_norm] = least_squares.generate_residual(df_ver["dtsecond"], df_ver["time_offset"])
    _logger.info(f"Euclidean norm of this verification data is: {ver_e_norm}")

    # GENERATE VERIFICATION PLOTS
    _logger.info("Generating verification plots...")
    df_ver["dtsecond_zero"] = df_ver["dtsecond"] - df_ver["dtsecond"].min()
    _plot_clock_drift_results(df_ver, df_ver["time_offset"], res, "Verify")

    return df_ver


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _clear_folder(folder):
    """Remove all files and subdirectories within folder."""
    _logger.info(f"clearing {folder} ...")
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            _logger.error('Failed to delete %s. Reason: %s', file_path, e)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(preset_name: str):
    cfg = PRESETS[preset_name]
    #_clear_folder("analysis/tmp")

    # set up training data
    basefilepath_train = os.getcwd() + "/../../data_shared/"
    training_files = []
    for file in os.listdir(basefilepath_train):  # NOTE: don't need file extension check here because training function handles it
        training_files.append(basefilepath_train + file)

    # set up verification data
    ver_file = training_files[0]

    if preset_name == "clamp_loop":
        df, y, w = _train_model_clamp_loop(training_files, cfg.columns, cfg.float_cols, cfg.clean_cols, cfg.truth_col)
        _verify_clamp_loop(ver_file, cfg.columns, cfg.float_cols, cfg.clean_cols, cfg.truth_col, w)
    elif preset_name == "clock_drift":
        df = _train_model_clock_drift(training_files)
        _verify_clock_drift(ver_file, cfg.columns)
        time_dict = stats_analysis.analyze_time(stats_analysis.create_datetime(df["timestamp"]))
        _logger.info(pformat(time_dict))

    show_plots()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logging.getLogger("PIL").setLevel(logging.WARNING)  # suppress PIL/Pillow image chunk noise
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    PRESET = "clamp_loop"  # change to "clock_drift" for clock drift analysis
    run(PRESET)
