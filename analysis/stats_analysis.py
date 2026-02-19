"""Statistical analysis utilities: regression, accuracy metrics, and time-series helpers."""

from datetime import datetime
from scipy.stats import linregress
import numpy as np

from common import plotter


##############################################################
################   LINEAR REGRESSION      ####################
##############################################################

def _linregress_stats(x_arr, y_arr):
    """Fit a line to (x_arr, y_arr) and return regression stats + residuals.

    Returns:
        dict with keys: slope, intercept, r, standard_error, residuals.
    """
    slope, intercept, r_value, _p, std_err = linregress(x_arr, y_arr)
    predicted = slope * x_arr + intercept
    residuals = y_arr - predicted
    return {
        "slope": slope,
        "intercept": intercept,
        "r": r_value,
        "standard_error": std_err,
        "residuals": residuals,
    }


def linear_fit(x_arr, y_arr):
    """Fit a line y = m*x + b, print the equation, plot residuals, and return stats.

    Returns:
        dict from _linregress_stats.
    """
    stats = _linregress_stats(x_arr, y_arr)
    print(f"y=mx+b: {stats['slope']}*x + {stats['intercept']}")

    plotter.time_plot(x_arr, stats["residuals"], "x", "Linear best-fit residuals")

    return stats


##############################################################
################   ACCURACY / ERROR ANALYSIS  ################
##############################################################

def compute_accuracy_stats(set_values, measured_values):
    """Compute error statistics between setpoint and measured arrays.

    Args:
        set_values: Array-like of target/setpoint values.
        measured_values: Array-like of actual measured values.

    Returns:
        dict with keys: errors, mean_error, std_error, max_error, rms_error,
        full_scale, mean_error_pct, max_error_pct.
    """
    set_arr  = np.asarray(set_values,      dtype=float)
    meas_arr = np.asarray(measured_values, dtype=float)
    errors   = meas_arr - set_arr

    mean_error = np.mean(errors)
    std_error  = np.std(errors)
    max_error  = np.max(np.abs(errors))
    rms_error  = np.sqrt(np.mean(errors ** 2))

    full_scale = abs(float(set_arr[-1]) - float(set_arr[0]))
    if full_scale > 0:
        mean_error_pct = (abs(mean_error) / full_scale) * 100
        max_error_pct  = (max_error      / full_scale) * 100
    else:
        mean_error_pct = 0.0
        max_error_pct  = 0.0

    return {
        "errors":        errors,
        "mean_error":    mean_error,
        "std_error":     std_error,
        "max_error":     max_error,
        "rms_error":     rms_error,
        "full_scale":    full_scale,
        "mean_error_pct": mean_error_pct,
        "max_error_pct":  max_error_pct,
    }


def format_accuracy_report(stats, set_values, measured_values, config=None):
    """Build a formatted accuracy test report string.

    Args:
        stats: Dict returned by compute_accuracy_stats().
        set_values: Array-like of target/setpoint values.
        measured_values: Array-like of actual measured values.
        config: Optional dict with keys start_voltage, stop_voltage,
                num_steps, settling_time, ps_channel.

    Returns:
        Multi-line formatted report string.
    """
    errors     = stats["errors"]
    full_scale = stats["full_scale"]

    lines = [
        "=" * 80,
        "INSTRUMENT ACCURACY TEST RESULTS",
        "=" * 80,
    ]

    if config:
        lines += [
            f"\nTest Configuration:",
            f"  Voltage Range: {config.get('start_voltage', '?')}V to {config.get('stop_voltage', '?')}V",
            f"  Number of Steps: {config.get('num_steps', '?')}",
            f"  Settling Time: {config.get('settling_time', '?')}s",
            f"  PS Channel: {config.get('ps_channel', '?')}",
        ]

    lines += [
        f"\nStatistics:",
        f"  Mean Error:          {stats['mean_error']:>10.6f} V  ({stats['mean_error_pct']:>6.3f}% of full scale)",
        f"  Std Deviation:       {stats['std_error']:>10.6f} V",
        f"  RMS Error:           {stats['rms_error']:>10.6f} V",
        f"  Max Absolute Error:  {stats['max_error']:>10.6f} V  ({stats['max_error_pct']:>6.3f}% of full scale)",
        f"\nDetailed Measurements:",
        f"{'Step':<6} {'Set (V)':<12} {'Measured (V)':<12} {'Error (V)':<12} {'Error (%FS)':<12}",
        "-" * 80,
    ]

    for i in range(len(set_values)):
        error_pct = (abs(float(errors[i])) / full_scale) * 100 if full_scale > 0 else 0
        lines.append(
            f"{i+1:<6} {set_values[i]:<12.6f} {measured_values[i]:<12.6f} "
            f"{float(errors[i]):<12.6f} {error_pct:<12.3f}"
        )

    lines.append("=" * 80)
    return "\n".join(lines)


##############################################################
################   TIME-SERIES UTILITIES  ####################
##############################################################

# Expected timestamp format produced by the logger tab.
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


def create_datetime(timestamp_array):
    """Parse an array of timestamp strings into datetime objects.

    Args:
        timestamp_array: Iterable of strings matching DATETIME_FORMAT.

    Returns:
        List of datetime objects.
    """
    return [datetime.strptime(ts, DATETIME_FORMAT) for ts in timestamp_array]


def analyze_time(dtime_arr):
    """Compute duration and sample rate from an array of datetime objects.

    Args:
        dtime_arr: List of datetime objects, ordered in time.

    Returns:
        dict with keys: dur_sec, dur_min, samples, frequency (Hz).
    """
    duration    = dtime_arr[-1] - dtime_arr[0]
    dur_sec     = duration.total_seconds()
    num_samples = len(dtime_arr)

    return {
        "dur_sec":   dur_sec,
        "dur_min":   dur_sec / 60,
        "samples":   num_samples,
        "frequency": num_samples / dur_sec,
    }
