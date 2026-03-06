# Analysis

Offline data analysis modules for post-processing CSV data collected by the GUI logger.

## Structure

```
analysis/
    data_helper.py          # CSV/DataFrame loading, type conversion, scaling
    stats_analysis.py       # Linear regression, accuracy metrics, time-series utilities
    specific/
        clock_analysis.py   # MCU clock drift analysis (least-squares model of timer vs wall clock)
        clamp_analysis.py   # Clamp loop analysis (least-squares model of TP_O from sensor signals)
        filter_analysis.py  # Digital filters: Butterworth, moving average, EMA, baseline-freeze
        imu_analysis.py     # IMU (accelerometer/gyroscope) data visualization and filtering
        least_squares.py    # Least-squares solver, residual computation, LASSO/proximal GD
        afe_analysis.py     # Analog front-end analysis: FFT, peak detection, heart rate
```

## Core Modules

### `data_helper.py`
General-purpose data loading and type conversion. Most analysis scripts use this to load CSVs into pandas DataFrames.

Key functions:
- `load_csv_pandas(filepath, columns)` — Load a CSV with optional column selection
- `load_mul_csv_pandas(basepath, files, columns)` — Load and concatenate multiple CSVs
- `df_float(df, column)` — Cast a DataFrame column to numeric
- `scale_array(arr, low, high)` — Min-max normalization
- `summarize_dataframe(df)` — Compute mean/std/min/max for numeric columns

### `stats_analysis.py`
Statistical utilities used across multiple analysis scripts.

Key functions:
- `linear_fit(x, y)` — Fit y = mx + b, plot residuals, return stats
- `compute_accuracy_stats(set_values, measured_values)` — Error metrics (mean, std, max, RMS, %FS)
- `format_accuracy_report(stats, ...)` — Formatted accuracy test report string
- `create_datetime(timestamp_array)` — Parse logger timestamp strings into datetime objects
- `analyze_time(dtime_arr)` — Compute duration and sample rate

## Domain-Specific Modules (`specific/`)

### `clock_analysis.py`
Analyzes MCU clock drift relative to the host PC's wall clock. Builds a least-squares model using MCU timer values and temperature as predictors of the time offset (ms).

Also contains shared data-cleaning helpers (`clean_data`, `get_filtered_data`) used by other analysis modules.

```bash
python -m analysis.specific.clock_analysis
```

### `clamp_analysis.py`
Models the clamp loop voltage (TP_O) from sensor signals (TP, MV, BO) using least-squares regression with baseline-freeze features. The baseline tracks TP via EMA while BO=0 and freezes during BO=1 activation.

```bash
python -m analysis.specific.clamp_analysis
```

### `filter_analysis.py`
Digital filter implementations:
- **Butterworth lowpass** — `butter_filter()` + `lowpass_filter()`
- **Moving average** — `moving_average_causal(y, N)` (causal, zero-padded)
- **EMA** — `ema_causal(y, alpha)`
- **Baseline-freeze filters** — `baseline_ma_freeze()` and `baseline_ema_freeze()`: track a baseline while a control signal is inactive, freeze it during activation. Matches the MCU's `BaselineEMA_Update()` logic.

### `least_squares.py`
Core linear algebra:
- `least_squares(A, d)` — Solve Aw = d via `numpy.linalg.lstsq`
- `generate_residual(calculated, truth)` — Compute residual and Euclidean norm
- `ista_solve_hot(A, d, lambdas)` — LASSO via iterative soft-thresholding (hot start)
- `prxgraddescent_l2(A, d, lambdas)` — L2 proximal gradient descent

### `imu_analysis.py`
IMU data visualization and simple filtering:
- `analyze_imu(file_path)` — Load CSV, plot accel/gyro, demonstrate lowpass at various alphas
- `analyze_ICM_42670(dig_temp_arr)` — Convert ICM-42670 digital temperature to Fahrenheit
- `c_lowpass(x, xm1, a)` — C-compatible lowpass filter for MCU validation

### `afe_analysis.py`
Analog front-end signal analysis: FFT computation, peak detection, heart rate calculation, Chebyshev/Butterworth bandpass filtering. (Note: this module has some broken imports and experimental commented-out code that needs cleanup.)

## Data Flow

Analysis scripts expect CSV files produced by the GUI's Logger tab (Tab 8), typically stored in `data/`. The standard workflow:

1. Record data using the Logger tab (writes timestamped CSVs to `data/`)
2. Copy/move training files to `data_shared/` (or adjust the path in the script)
3. Run the analysis script: `python -m analysis.specific.clock_analysis`

## Dependencies

- `numpy`, `pandas` — core data handling
- `scipy` — signal processing (filters, regression, FFT)
- `matplotlib` — plotting (via `common/plotter.py` wrapper)
- `sklearn` — MinMaxScaler (used in `data_helper.py`)
