"""Clock drift analysis — least-squares model of MCU timer drift vs wall clock."""

from __future__ import annotations

import logging
import os
from pprint import pformat

import numpy as np
import pandas as pd

from analysis import data_helper as datah
from analysis import stats_analysis
from analysis.specific import imu_analysis
from analysis.specific import least_squares
from common import plotter
from common.plotter import show_plots


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Data cleaning / loading helpers (shared with clamp_analysis)
# ---------------------------------------------------------------------------

def clean_data(df, column, column2=None):
    """Drop NaN rows, filter out non-monotonic decreases in column, and zero-base the column.

    Applies the monotonic filter three times to handle consecutive outliers.
    If column2 is provided, also removes rows where column2 jumps by more than 10 between samples.
    """
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
    """Remove rows whose local z-score exceeds a threshold (rolling window outlier filter)."""
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


# ---------------------------------------------------------------------------
# Clock drift helpers
# ---------------------------------------------------------------------------

def create_time_offset(mcu_time_arr, real_time):
    """Compute per-sample drift (ms) between MCU timer and wall clock, zeroed at the first sample."""
    offset = -1 * (mcu_time_arr[0]) + real_time[0] * pow(10, 3)

    # calculate time delta
    i = 0
    time_diff = []
    for mcu_time in mcu_time_arr:
        time_diff.append(mcu_time - real_time[i] * pow(10, 3) + offset)
        i += 1

    return time_diff


def full_create_time_offset(df_tmp):
    """Convenience wrapper: extract timestamp/ms columns from a DataFrame and compute time offset."""
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
    """Fit a linear model and log the results."""
    _logger.info("Creating linear fit ....")
    stats = stats_analysis.linear_fit(x_arr, y_arr)
    _logger.info(pformat(stats))
    return stats


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Data loading
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


# ---------------------------------------------------------------------------
# Train / Verify
# ---------------------------------------------------------------------------

def _train_model(train_file):
    train_df = pd.DataFrame()
    time_offset = []

    for tr_file in train_file:
        if ".csv" in tr_file:
            _logger.info(f"Loading in file: {tr_file}")
            df_tmp = _get_clock_drift_data(tr_file, ["timestamp", "ms", "temp"], ["temp"], ["ms"])
            dt_tmp = stats_analysis.create_datetime(df_tmp["timestamp"])
            dt_seconds = [date.timestamp() for date in dt_tmp]

            time_offset.extend(
                create_time_offset(
                    np.array(df_tmp["ms"]),
                    dt_seconds)
            )

            train_df = pd.concat([train_df, df_tmp], ignore_index=True)

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

    w = least_squares.least_squares(A, d)
    w = np.array(w)
    y = A @ w

    _logger.info(f"coefs w are of shape: {w.shape}")
    _logger.info(f"shape of output y is: {y.shape}")
    [residual, e_norm] = least_squares.generate_residual(y, d)
    _logger.info(f"coefficients (w) found from data; computed output values (y) and formed residual")
    _logger.info(f"w: {w}")
    _logger.info(f"Euclidean norm of this training data is: {e_norm}")

    _plot_clock_drift_results(train_df, time_offset, residual, "Train")

    return train_df


def _verify(ver_file, columns):
    df_ver = _get_clock_drift_data(ver_file, columns, ["temp"], ["ms"])
    ver_toff = np.array(
        create_time_offset(
            np.array(df_ver["ms"]),
            df_ver["dtsecond"].tolist())
    )

    df_ver["time_offset"] = ver_toff.reshape(-1, 1)
    [res, ver_e_norm] = least_squares.generate_residual(df_ver["dtsecond"], df_ver["time_offset"])
    _logger.info(f"Euclidean norm of this verification data is: {ver_e_norm}")

    _logger.info("Generating verification plots...")
    df_ver["dtsecond_zero"] = df_ver["dtsecond"] - df_ver["dtsecond"].min()
    _plot_clock_drift_results(df_ver, df_ver["time_offset"], res, "Verify")

    return df_ver


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

COLUMNS = ["timestamp", "ms", "temp"]


def run():
    basefilepath_train = os.getcwd() + "/data_shared/"
    training_files = []
    for file in os.listdir(basefilepath_train):
        training_files.append(basefilepath_train + file)

    ver_file = training_files[0]

    df = _train_model(training_files)
    _verify(ver_file, COLUMNS)
    time_dict = stats_analysis.analyze_time(stats_analysis.create_datetime(df["timestamp"]))
    _logger.info(pformat(time_dict))

    show_plots()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    run()
