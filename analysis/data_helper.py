"""Data scaling and processing utilities."""

import pandas as pd
import numpy as np
import csv
# from sklearn.preprocessing import MinMaxScaler


def scale_array(arr, low, high):
    scaler = MinMaxScaler(feature_range=(low, high))
    # Fit and transform the data
    scaled_arr = scaler.fit_transform(arr)
    # If you want to convert the scaled array back to a 1D array
    scaled_arr = scaled_arr.flatten()
    return scaled_arr


def convert_to_int(value):
    try:
        # Try converting to float
        return int(value)
    except ValueError:
        # If conversion fails (e.g., value is a string with '-'), handle accordingly
        if isinstance(value, str) and value.startswith('-'):
            if len(value[1:]) > 0: # empty value check
                return -1*int(value[1:])  # Convert to negative float
            else:
                # return np.nan
                return 0
        else:
            # return np.nan  # Convert to NaN for other cases
            return 0


def convert_to_float(value):
    try:
        # Try converting to float
        return float(value)
    except ValueError:
        # If conversion fails (e.g., value is a string with '-'), handle accordingly
        if isinstance(value, str) and value.startswith('-'):
            if len(value[1:]) > 0: # empty value check
                return -float(value[1:])  # Convert to negative float
            else:
                # return np.nan
                return 0
        else:
            # return np.nan  # Convert to NaN for other cases
            return 0



# converts an array to a pandas Series full of float values
def arr_float(arr):
    arr_float = [convert_to_float(val) for val in arr]
    arr_float = pd.Series(arr_float)
    return arr_float


def df_float(df, column):
    error_style = "raise"
    # error_style = "coerce"
    df[column] = pd.to_numeric(df[column], errors=error_style)
    return df


# def PrettyFloat(num):
#     # Handle sign
#     sign = '+' if num >= 0 else '-'
#     num = abs(num)
#
#     if num >= 100:
#         # Format numbers >= 100 with E notation and one decimal point before the E
#         formatted = f"{num:.5E}"
#     elif num >= 1:
#         # Format numbers between 1 and 100 with fixed decimal places
#         formatted = f"{num:.6f}".rstrip('0').rstrip('.')
#     else:
#         # Format numbers < 1 with E notation for precision
#         formatted = f"{num:.5E}"
#
#     return sign + formatted


##############################################################
################   DATA and .csv FUNCS   #####################
##############################################################


def get_first_row_csv(file_path):
    """
    Reads the first row of a CSV file and returns it as a list.

    :param file_path: The path to the CSV file.
    :return: A list containing the values of the first row.
    """
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        # Get the first row
        first_row = next(csv_reader, None)  # Returns None if the file is empty
    return first_row


def load_csv_pandas(filepath, columns=None, read_columns=False):
    # SETUP FILE INFORMATION (column headers)
    if read_columns or columns is None:
        columns = get_first_row_csv(filepath)

    print(f"\nINFO: Attempting to open a .csv using columns: \n\t{columns}")
    print(f"\tusing path --> {filepath}\n")

    # LOAD DATA
    try:
        # Load data from CSV file
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        print("Pandas says data is empty! No columns to parse from file")
        return None
    # Extract columns
    pandas_data = df[columns]

    if len(pandas_data[columns[0]].tolist()) == 0:
        print("File seems to be .csv but there is no data!")
        return None
    return pandas_data


def load_mul_csv_pandas(basefilepath, file_list, columns):
    filepath = basefilepath + file_list[0]
    train_file = file_list[1:]
    data_frame = load_csv_pandas(filepath, columns=columns)
    for file in train_file:
        filepath = basefilepath + file
        data_frame = data_frame.append(
            load_csv_pandas(filepath, columns=columns),
            ignore_index=True
        )
    return data_frame


def load_csv_numpy(file_path):
    # Load CSV file into a NumPy array
    # data = np.genfromtxt(file_path, delimiter=',', skip_header=1)
    # data = np.genfromtxt(file_path, delimiter=',', dtype=None, names=True, encoding=None)
    data = np.genfromtxt(file_path, delimiter=',', dtype=None, encoding=None, skip_header=2)
    return data


def summarize_dataframe(df):
    """Compute summary statistics for all numeric columns in a DataFrame.

    Args:
        df: pandas DataFrame.

    Returns:
        dict of {column_name: {"mean": float, "std": float, "min": float, "max": float}}.
        Empty dict if no numeric columns.
    """
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_cols) == 0:
        return {}

    result = {}
    for col in numeric_cols:
        result[col] = {
            "mean": df[col].mean(),
            "std": df[col].std(),
            "min": df[col].min(),
            "max": df[col].max(),
        }
    return result


def load_dataset():
    pass
