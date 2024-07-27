

import pandas as pd
import numpy as np
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


# TODO: this function is dogshit. Needs usage evaluated or a ChatGPT improvement. And to get out of here
def PrettyFloat(v):
    """
        A crude but functional formatter that shows floating
        points in engineering format

        Input                result
                             1234567890

       +1234567800        to +1.23456E9
        +123456780        to +123.456E6
        +12345678         to +12.3456E6
        +1234567.8        to +1.23456E6
        +123456.78        to +123.456E3
        +12345.678        to +12.3456E3
        +1234.5678        to +1.23456E3
        +123.45678        to   +123.456
        +12.345678        to   +12.3456
        +1.2345678        to   +1.23456
        +0.12345678       to +123.45E-3
        +0.012345678      to +12.345E-3
        +0.0012345678     to +1.2345E-3
        +0.00012345678    to +123.45E-6
        +0.000012345678   to +12.345E-6
        +0.0000012345678  to +1.2345E-6
        +0.00000012345678 to +123.45E-9
        +0.00000001234567 to +12.345E-9
        +0.00000000123456 to +1.2345E-9

    """
    av = abs(v)
    if av < 1:
        v = v * 1000
        if av >= 1E-1:
            vs = '{:+7.2f}E-3'.format(v)
        elif av >= 1E-2:
            vs = '{:+7.3f}E-3'.format(v)
        elif av >= 1E-3:
            vs = '{:+7.4f}E-3'.format(v)
        else:
            v = v * 1000
            if av >= 1E-4:
                vs = '{:+7.2f}E-6'.format(v)
            elif av >= 1E-5:
                vs = '{:+7.3f}E-6'.format(v)
            elif av >= 1E-6:
                vs = '{:+7.4f}E-6'.format(v)
            else:
                v = v * 1000
                if av >= 1E-7:
                    vs = '{:+7.2f}E-9'.format(v)
                elif av >= 1E-8:
                    vs = '{:+7.3f}E-9'.format(v)
                else:
                    vs = '{:+7.4f}E-9'.format(v)
    else:
        if av < 1E1:
            vs = ' {:+8.4f}'.format(v)
        elif av < 1E2:
            vs = ' {:+8.3f}'.format(v)
        elif av < 1E3:
            vs = ' {:+8.2f}'.format(v)
        else:
            v = v / 1000
            if av < 1E4:
                vs = '{:+8.5f}E3'.format(v)
            elif av < 1E5:
                vs = '{:+8.4f}E3'.format(v)
            elif av < 1E6:
                vs = '{:+8.3f}E3'.format(v)
            else:
                v = v / 1000
                if av < 1E7:
                    vs = '{:+8.5f}E6'.format(v)
                elif av < 1E8:
                    vs = '{:+8.4f}E6'.format(v)
                elif av < 1E9:
                    vs = '{:+8.3f}E6'.format(v)
                else:
                    v = v / 1000
                    vs = '{:+8.5f}E9'.format(v)
    return vs


##############################################################
################   DATA and .csv FUNCS   #####################
##############################################################

def get_first_row_csv(filepath):
    # TODO: complete this function to extract first row as array
    return ["timestamp", "fifo", "data"]


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


def load_dataset():
    pass
