"""Butterworth lowpass filter implementation."""

import logging
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, freqz
from collections import deque



logger = logging.getLogger(__name__)


# compute the frequency response of a digital filter
# returns
#   w: frequencies at which h was computed, in the same units as fs
#   h: frequency response, as complex numbers
def freq_response(b, a, fs, worN=8000):
    w, h = freqz(b, a, fs=fs, worN=worN)
    return w, h


#     cutoff  : desired cutoff frequency of the filter, Hz
#     fs      : sample rate, Hz (estimated this based on a period of 0.11 seconds between samples)
#     order   : ???
def butter_filter(cutoff, fs, order=5):
    return butter(order, cutoff, fs=fs, btype='low', analog=False)


def lowpass_filter(b, a, data):
    y = lfilter(b, a, data)
    return y


def moving_average_causal(y, N: int):
    """
    Causal moving average over the previous N samples.
    y can be shape (N,) or (N,1). Returns same shape as y.
    """
    y1d = y.reshape(-1).astype(np.float64)
    # Uniform kernel of length N
    k = np.ones(N, dtype=np.float64) / N
    # Convolve causally: pad on the left with N-1 zeros (or with first value)
    # Here we use zero-pad which biases the initial few samples low; see variant below to pad with first value.
    y_pad = np.pad(y1d, (N-1, 0), mode='constant', constant_values=0.0)
    ma = np.convolve(y_pad, k, mode='valid')  # length equals original
    return ma.reshape(y.shape)


def ema_causal(y, alpha: float):
    """
    Causal EMA: y_ema[t] = alpha*y[t] + (1-alpha)*y_ema[t-1]
    y can be (N,) or (N,1). Returns same shape.
    """
    y1d = y.reshape(-1).astype(np.float64)
    out = np.empty_like(y1d)
    out[0] = y1d[0]
    a = float(alpha)
    for i in range(1, len(y1d)):
        out[i] = a*y1d[i] + (1.0 - a)*out[i-1]
    return out.reshape(y.shape)


def baseline_ma_freeze(var4, loop, window=20, min_samples=5, skip_first_after_fall=True):
    """
    Baseline = moving average of var4 while loop==0; frozen during loop==1.
    Additionally, skip updating the MA on the first sample after a falling edge (1->0) if enabled.
    Returns (baseline, baseline_valid, baseline_filled, delta).
    """
    var4 = np.asarray(var4, dtype=np.float64).reshape(-1)
    loop = np.asarray(loop, dtype=np.int8).reshape(-1)
    N = len(var4)

    baseline = np.full(N, np.nan, dtype=np.float64)
    running_vals = deque(maxlen=window)
    last_baseline = np.nan
    have_enough = False

    prev_loop = 0
    cooldown = 0  # 1 sample cooldown after falling edge

    for i in range(N):
        cur = int(loop[i])

        # Detect falling edge: 1 -> 0
        if skip_first_after_fall and prev_loop == 1 and cur == 0:
            cooldown = 1

        if cur == 0:
            if cooldown > 0:
                # Skip updating MA on the first 0 after a fall
                cooldown -= 1
            else:
                # Normal MA update while inactive
                running_vals.append(var4[i])
                if len(running_vals) >= min_samples:
                    last_baseline = float(np.mean(running_vals))
                    have_enough = True
            # While inactive, baseline stays NaN (we “use” it only during active)
        else:
            # Active: freeze the last computed baseline
            if have_enough:
                baseline[i] = last_baseline

        prev_loop = cur

    baseline_valid  = (~np.isnan(baseline)).astype(np.float64)
    baseline_filled = np.where(np.isnan(baseline), var4, baseline)
    delta           = baseline_filled - var4
    return baseline, baseline_valid, baseline_filled, delta



def baseline_ema_freeze(var4, loop, alpha=0.1):
    """
    Baseline = EMA of var4 while loop==0; frozen during loop==1.
    Returns (baseline, baseline_valid, baseline_filled, delta).
    """
    var4 = np.asarray(var4, dtype=np.float64).reshape(-1)
    loop = np.asarray(loop, dtype=np.int8).reshape(-1)
    N = len(var4)

    baseline = np.full(N, np.nan, dtype=np.float64)
    ema_val = var4[0]
    have_ema = False

    for i in range(N):
        if loop[i] == 0:
            # update EMA
            ema_val = alpha * var4[i] + (1.0 - alpha) * ema_val
            have_ema = True
            # keep baseline NaN while inactive (we only "use" it during active)
        else:
            if have_ema:
                baseline[i] = ema_val   # freeze the last EMA while active

    baseline_valid  = (~np.isnan(baseline)).astype(np.float64)
    baseline_filled = np.where(np.isnan(baseline), var4, baseline)
    delta           = baseline_filled - var4
    return baseline, baseline_valid, baseline_filled, delta


