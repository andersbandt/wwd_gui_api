"""Clamp loop analysis — least-squares model of TP_O from TP, MV, BO signals."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pprint import pformat

import numpy as np
import pandas as pd

from analysis import data_helper as datah
from analysis.specific import least_squares
from analysis.specific import filter_analysis
from analysis.specific.clock_analysis import clean_data
from common import plotter
from common.plotter import show_plots


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Preset
# ---------------------------------------------------------------------------

@dataclass
class ClampPreset:
    name: str
    columns: list
    float_cols: list | None
    clean_cols: list | None
    truth_col: list | None


PRESET = ClampPreset(
    name="clamp_loop",
    columns=["PV", "MV", "BO", "TP", "TP_O"],
    float_cols=None,
    clean_cols=None,
    truth_col=["TP_O"],
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def get_train_data(
    file,
    col_str,
    float_cols=None,
    clean_cols=None,
    *,
    loop_col="BO",
    volt_col="TP",
    window=5,
    min_samples=3,
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
    df = datah.load_csv_pandas(file, columns=col_str)

    if float_cols:
        for col in float_cols:
            df = datah.df_float(df, col)

    if clean_cols:
        for col in clean_cols:
            df = clean_data(df, col)

    for col in (loop_col, volt_col):
        if col not in df.columns:
            raise KeyError(f"Column '{col}' not found. Available: {list(df.columns)}")

    loop = df[loop_col].to_numpy().astype(np.int8)
    var4 = df[volt_col].to_numpy().astype(np.float64)

    # Rising edges: indices where loop changes 0 -> 1
    rising = np.flatnonzero((loop[1:] == 1) & (loop[:-1] == 0)) + 1
    df["_rising_idx"] = 0
    if len(rising) > 0:
        df.loc[rising, "_rising_idx"] = 1

    loop = df["BO"].to_numpy()

    # Choose ONE:
    #baseline, baseline_valid, baseline_filled, delta = filter_analysis.baseline_ma_freeze(var4, loop, window=window, min_samples=min_samples)
    baseline, baseline_valid, baseline_filled, delta = filter_analysis.baseline_ema_freeze(var4, loop, alpha=1.0)  # alpha=1.0 must match MCU calib_init()

    df["_baseline"] = baseline
    df["_baseline_valid"] = baseline_valid
    df["_baseline_filled"] = baseline_filled
    df["_delta"] = delta

    return df


def get_truth_data(file, col_str):
    df = datah.load_csv_pandas(file, columns=col_str)
    truth = df[col_str]
    return truth


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot_clamp_results(df, res, phase):
    """Shared plot helper for clamp loop — call with phase='Train' or 'Verify'."""
    idx = list(range(len(df)))
    plotter.plot_subplots(
        idx,
        channels=[
            (res,         "Residual"),
            #(df["TP"],  "TP ADC reading"),
            #(df["TP_O"],    "TP (mV)"),
            #(df["BO"],    "Boosting"),
            (df["MV"], "main valve"),
        ],
        xlabel="Sample",
        title=f"{phase}: Clamp Loop Results",
        show_plot=False,
    )


# ---------------------------------------------------------------------------
# Train / Verify
# ---------------------------------------------------------------------------

def _train_model(train_file, columns, float_col, clean_col, truth_col):
    train_df = pd.DataFrame()
    truth_df = pd.DataFrame()

    for tr_file in train_file:
        if ".csv" in tr_file:
            _logger.info(f"Loading in file: {tr_file}")
            df_train_tmp = get_train_data(tr_file, columns, float_col, clean_col)
            df_truth_tmp = get_truth_data(tr_file, truth_col)

            train_df = pd.concat([train_df, df_train_tmp], ignore_index=True)
            truth_df = pd.concat([truth_df, df_truth_tmp], ignore_index=True)

    _logger.info(f"Loaded columns: {list(train_df.columns)}")
    if _logger.isEnabledFor(logging.DEBUG):
        train_df.info()

    A = np.column_stack((
        np.ones(len(train_df)),
        train_df["TP"],
        train_df["TP"] ** 2,
        train_df["MV"],
        train_df["MV"] * train_df["TP"],
        train_df["BO"] * train_df["_baseline_filled"],
        train_df["BO"],
    ))

    d = np.array(truth_df)
    d = d.reshape(-1, 1)
    _logger.debug("MATRIX A:\n%s", pformat(A))
    _logger.debug("MATRIX d:\n%s", pformat(d))
    _logger.info(f"Computing least squares with A matrix of shape={A.shape} dtype={A.dtype}")
    _logger.info(f"and d of shape={d.shape} dtype={d.dtype}")

    w = least_squares.least_squares(A, d)
    w = np.array(w)
    y = A @ w

    mov_average_window = 15
    y = filter_analysis.moving_average_causal(y, mov_average_window)

    _logger.info(f"coefs w are of shape: {w.shape}")
    _logger.info(f"shape of output y is: {y.shape}")
    _logger.info(f"coefficients (w) found from data; computed output values (y) and formed residual")
    _logger.info(f"w: {w}")

    [res, ver_e_norm] = least_squares.generate_residual(y, d)

    res[0:mov_average_window] = 0  # tag:HARDCODE to manually set first value to 0. Otherwise moving average will cause havoc

    _logger.info(f"Euclidean norm: {ver_e_norm}")
    _logger.debug("residual:\n%s", pformat(res))

    _plot_clamp_results(train_df, res, "Train")

    return train_df, y, w


def _verify(ver_file, columns, float_col, clean_col, truth_col, w):
    df_ver = get_train_data(ver_file, columns, float_col, clean_col)

    A_ver = np.column_stack((
        np.ones(len(df_ver)),
        df_ver["TP"],
        df_ver["MV"] * df_ver["TP"],
        df_ver["BO"] * df_ver["_baseline_filled"],
        df_ver["BO"],
        df_ver["BO"] * df_ver["MV"],
        df_ver["BO"] * df_ver["MO"],
        (1 - df_ver["BO"]) * df_ver["MO"]
    ))

    y_ver = A_ver @ w
    d_ver = df_ver[truth_col].to_numpy().reshape(-1, 1)

    [res, ver_e_norm] = least_squares.generate_residual(y_ver, d_ver)
    _logger.info(f"Euclidean norm of this verification data is: {ver_e_norm}")

    _logger.info("Generating verification plots...")
    _plot_clamp_results(df_ver, res, "Verify")

    return df_ver


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run():
    cfg = PRESET

    basefilepath_train = os.getcwd() + "/data_shared/"
    training_files = []
    for file in os.listdir(basefilepath_train):
        training_files.append(basefilepath_train + file)

    ver_file = training_files[0]

    df, y, w = _train_model(training_files, cfg.columns, cfg.float_cols, cfg.clean_cols, cfg.truth_col)
    #_verify(ver_file, cfg.columns, cfg.float_cols, cfg.clean_cols, cfg.truth_col, w)

    show_plots()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    run()
