"""Statistical analysis utilities."""

# import needed modules
from pprint import pprint
from scipy.stats import linregress
import numpy as np


# import user created modules
from common import plotter


####################################
###   STATS analysis    ############
####################################

def calculate_statistics(x_arr, y_arr):
    # Calculate linear regression parameters
    slope, intercept, r_value, p_value, std_err = linregress(x_arr, y_arr)

    # Calculate predicted values using the linear model
    predicted_values = slope * x_arr + intercept
    pprint(predicted_values)

    # Calculate residuals (difference between observed and predicted values)
    residuals = y_arr - predicted_values

    return {
        "slope": slope,
        "intercept": intercept,
        "r": r_value,
        "standard error": std_err,
        "residuals": residuals
    }


# get linear fit in the form of y = m*x + b
def linear_fit(x_arr, y_arr):
    # Calculate linear regression parameters
    slope, intercept, r_value, p_value, std_err = linregress(x_arr, y_arr)
    print(f"y=mx+b <<< --- >>>   {slope}*[x] + {intercept}")

    stats = calculate_statistics(x_arr, y_arr)

    # make a plot of residuals
    plotter.time_plot(
        x_arr,
        stats["residuals"],
        "Time series",
        "Linear best fit residuals"
    )

    return stats


def compute_accuracy_stats(set_values, measured_values):
    """Compute accuracy statistics between set and measured values.

    Args:
        set_values: Array-like of target/setpoint values.
        measured_values: Array-like of actual measured values.

    Returns:
        dict with keys: errors, mean_error, std_error, max_error, rms_error,
        full_scale, mean_error_pct, max_error_pct.
    """
    set_arr = np.asarray(set_values, dtype=float)
    meas_arr = np.asarray(measured_values, dtype=float)
    errors = meas_arr - set_arr

    mean_error = np.mean(errors)
    std_error = np.std(errors)
    max_error = np.max(np.abs(errors))
    rms_error = np.sqrt(np.mean(errors**2))

    full_scale = abs(float(set_arr[-1]) - float(set_arr[0]))
    if full_scale > 0:
        mean_error_pct = (abs(mean_error) / full_scale) * 100
        max_error_pct = (max_error / full_scale) * 100
    else:
        mean_error_pct = 0.0
        max_error_pct = 0.0

    return {
        "errors": errors,
        "mean_error": mean_error,
        "std_error": std_error,
        "max_error": max_error,
        "rms_error": rms_error,
        "full_scale": full_scale,
        "mean_error_pct": mean_error_pct,
        "max_error_pct": max_error_pct,
    }


def format_accuracy_report(stats, set_values, measured_values, config=None):
    """Build a multi-line formatted accuracy test report string.

    Args:
        stats: Dict returned by compute_accuracy_stats().
        set_values: Array-like of target/setpoint values.
        measured_values: Array-like of actual measured values.
        config: Optional dict with keys start_voltage, stop_voltage,
                num_steps, settling_time, ps_channel.

    Returns:
        Formatted report string.
    """
    errors = stats["errors"]
    full_scale = stats["full_scale"]

    lines = []
    lines.append("=" * 80)
    lines.append("INSTRUMENT ACCURACY TEST RESULTS")
    lines.append("=" * 80)

    if config:
        lines.append(f"\nTest Configuration:")
        lines.append(f"  Voltage Range: {config.get('start_voltage', '?')}V to {config.get('stop_voltage', '?')}V")
        lines.append(f"  Number of Steps: {config.get('num_steps', '?')}")
        lines.append(f"  Settling Time: {config.get('settling_time', '?')}s")
        lines.append(f"  PS Channel: {config.get('ps_channel', '?')}")

    lines.append(f"\nStatistics:")
    lines.append(f"  Mean Error:          {stats['mean_error']:>10.6f} V  ({stats['mean_error_pct']:>6.3f}% of full scale)")
    lines.append(f"  Std Deviation:       {stats['std_error']:>10.6f} V")
    lines.append(f"  RMS Error:           {stats['rms_error']:>10.6f} V")
    lines.append(f"  Max Absolute Error:  {stats['max_error']:>10.6f} V  ({stats['max_error_pct']:>6.3f}% of full scale)")

    lines.append(f"\nDetailed Measurements:")
    lines.append(f"{'Step':<6} {'Set (V)':<12} {'Measured (V)':<12} {'Error (V)':<12} {'Error (%FS)':<12}")
    lines.append("-" * 80)

    for i in range(len(set_values)):
        error_pct = (abs(float(errors[i])) / full_scale) * 100 if full_scale > 0 else 0
        lines.append(f"{i+1:<6} {set_values[i]:<12.6f} {measured_values[i]:<12.6f} {float(errors[i]):<12.6f} {error_pct:<12.3f}")

    lines.append("=" * 80)
    return "\n".join(lines)