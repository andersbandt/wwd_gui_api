

import pandas as pd
import numpy as np




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
                return np.nan
        else:
            return np.nan  # Convert to NaN for other cases




##############################################################
################   DATA and .csv FUNCS   #####################
##############################################################

### data loading functions
# TODO: maybe edit this function to read the first line some other way and use that as the headers
def load_csv_pandas(filepath, columns=None):
    # DEFAULT COLUMNS (only for AFE)
    if columns is None:
        columns = ['timestamp', 'fifo', 'data']
    print(f"Attempting to open a .csv using columns: \n\t{columns}")
    print(f"\tusing path --> {filepath}")

    #  laod in data
    try:
        # Load data from CSV file
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        print("Pandas says data is empty! No columns to parse from file")
        return None
    # # Extract columns
    pandas_data = df[columns]
    if len(pandas_data[columns[0]].tolist()) == 0:
        print("File seems to be .csv but there is no data!")
        return None
    return pandas_data


def load_mul_csv_pandas(basefilepath, file_list, columns):
    filepath = basefilepath + file_list[0]
    train_file = file_list[1:]
    data_frame = load_csv_pandas(filepath, columns=["timestamp", "ms"])
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
