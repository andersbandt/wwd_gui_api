"""General-purpose data loading and type-conversion utilities for offline analysis."""

import csv

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


##############################################################
################   TYPE CONVERSION        ####################
##############################################################

def scale_array(arr, low, high):
    """Scale arr to [low, high] using min-max normalization."""
    scaler = MinMaxScaler(feature_range=(low, high))
    scaled_arr = scaler.fit_transform(arr)
    return scaled_arr.flatten()


def convert_to_int(value):
    """Coerce value to int, returning 0 on failure instead of raising."""
    try:
        return int(value)
    except ValueError:
        if isinstance(value, str) and value.startswith('-') and len(value) > 1:
            return -1 * int(value[1:])
        return 0


def convert_to_float(value):
    """Coerce value to float, returning 0.0 on failure instead of raising."""
    try:
        return float(value)
    except ValueError:
        if isinstance(value, str) and value.startswith('-') and len(value) > 1:
            return -float(value[1:])
        return 0.0


def arr_float(arr):
    """Convert an iterable to a pandas Series of floats using convert_to_float."""
    return pd.Series([convert_to_float(val) for val in arr])


def df_float(df, column):
    """Cast a DataFrame column to numeric in-place, raising on unparseable values."""
    df[column] = pd.to_numeric(df[column], errors="raise")
    return df


##############################################################
################   CSV / DATAFRAME LOADING   #################
##############################################################

def get_first_row_csv(file_path):
    """Return the first row of a CSV file as a list (i.e. the header row)."""
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        first_row = next(csv.reader(csvfile), None)
    return first_row


def load_csv_pandas(filepath, columns=None, read_columns=False):
    """Load a CSV into a pandas DataFrame, optionally reading column names from the header.

    Args:
        filepath: Path to the CSV file.
        columns: List of column names to extract. If None or read_columns=True,
                 column names are read from the first row of the file.
        read_columns: Force re-reading column names from the file header.

    Returns:
        DataFrame containing the requested columns, or None if the file is empty.
    """
    if read_columns or columns is None:
        columns = get_first_row_csv(filepath)

    print(f"\nINFO: Attempting to open a .csv using columns: \n\t{columns}")
    print(f"\tusing path --> {filepath}\n")

    try:
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        print("Pandas says data is empty! No columns to parse from file")
        return None

    pandas_data = df[columns]

    if len(pandas_data[columns[0]].tolist()) == 0:
        print("File seems to be .csv but there is no data!")
        return None

    return pandas_data


def load_mul_csv_pandas(basefilepath, file_list, columns):
    """Load and concatenate multiple CSV files into one DataFrame.

    Args:
        basefilepath: Directory prefix prepended to each filename.
        file_list: List of CSV filenames (relative to basefilepath).
        columns: Column names to extract from each file.

    Returns:
        Concatenated DataFrame.
    """
    frames = [load_csv_pandas(basefilepath + f, columns=columns) for f in file_list]
    return pd.concat(frames, ignore_index=True)


def load_csv_numpy(file_path):
    """Load a CSV into a NumPy array, skipping the first two header rows."""
    return np.genfromtxt(file_path, delimiter=',', dtype=None, encoding=None, skip_header=2)


def summarize_dataframe(df):
    """Compute mean/std/min/max for every numeric column in a DataFrame.

    Returns:
        dict of {column_name: {"mean", "std", "min", "max"}}.
        Empty dict if no numeric columns exist.
    """
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_cols) == 0:
        return {}

    return {
        col: {
            "mean": df[col].mean(),
            "std":  df[col].std(),
            "min":  df[col].min(),
            "max":  df[col].max(),
        }
        for col in numeric_cols
    }
