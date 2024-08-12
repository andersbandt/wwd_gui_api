"""
@file     clock_analysis.py
@author   Anders Bandt
@date     April 2024
@brief    perform clocking and time-domain analysis
"""

# import needed modules
import pandas as pd
import numpy as np
from pprint import pprint

import os
import shutil
from matplotlib import pyplot as plt

# import user created modules
from analysis import least_squares, data_helper as datah
from analysis import time_analysis
from analysis import stats_analysis
from analysis import temp_analysis
from common import plotter
from common import logger


# TODO: plots have y-axis labeled but add some TITLES
# TODO: is there something wrong with my verification data method? I get a large residual


# TODO: another cleaning method I realized is my erroneous data has two entries for the same timestamp
def clean_data(df, column, column2=None):
    print("INFO: Cleaning data ....")
    print(f"\tdata starting with row count: {df.shape[0]}")
    # drop out nAn values
    df = df.replace('', np.nan)
    df = df.dropna()

    # Filter out data points that fall below the lower threshold or above the upper threshold
    # NOTE: the .shift() command moves towards the end of the series by default
    df = df[df[column] >= df[column].shift(1)]
    df = df[df[column] >= df[column].shift(1)]
    df = df[df[column] >= df[column].shift(1)]

    print(f"\tfilter on column '{column}' yields row count: {df.shape[0]}")

    temp_shift = 10  # max shift between temp samples allowed
    if column2:
        df = df[df[column2] - df[column2].shift(1) <= temp_shift]
        df = df[df[column2] - df[column2].shift(1) <= temp_shift]
        print(f"\tfilter on column '{column2}' yields row count: {df.shape[0]}")

    # reset the starting value to be at 0
    min_value = df[column].min()
    result = df[column] - min_value
    df[column] = result

    return df


# def clean_data(df, interest_column):
#     # Check the number of elements in each row
#     row_lengths = df[interest_column].astype(str).str.len()
#     cleaned_df = df[(5 <= row_lengths) & (row_lengths <= 8)]
#     return cleaned_df


def get_filtered_data(data_arr, interest_column):
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
        print(z_score)

        # If the z-score exceeds the threshold, mark the index for removal
        threshold = 0.01
        if z_score > threshold:
            filtered_indices.append(i)

    # Remove rows with filtered indices
    # data_arr_f = np.delete(data_arr, filtered_indices, axis=0)
    data_arr_f = data_arr.drop(filtered_indices)

    return data_arr_f


def get_total_data(total_file, col_str, float_col, clean_col):
    df = datah.load_csv_pandas(total_file, columns=col_str)

    for col in float_col:
        df = datah.df_float(df, col)

    for col in clean_col:
        df = clean_data(df, col)

    if "timestamp" in col_str:
        df["datetime"] = time_analysis.create_datetime(df["timestamp"])
        df["dtsecond"] = [date.timestamp() for date in df["datetime"]]

    return df


#####################################
### END OF GETTING DATA SECTION  ####
#####################################

def create_time_offset(mcu_time_arr, real_time):
    # calculate offset for x=0 to be y=0
    offset = -1 * (mcu_time_arr[0]) + real_time[0] * pow(10, 3)

    # calculate time delta
    i = 0
    time_diff = []
    for mcu_time in mcu_time_arr:
        time_diff.append(mcu_time - real_time[i] * pow(10, 3) + offset)
        i += 1

    return time_diff


def full_create_time_offset(df_tmp):
    time_offset = []
    dt_tmp = time_analysis.create_datetime(df_tmp["timestamp"])
    dt_seconds = [date.timestamp() for date in dt_tmp]
    time_offset.extend(
        create_time_offset(
            np.array(df_tmp["ms"]),
            dt_seconds)
    )
    return time_offset


def train_model(train_file, ver_file):
    train_df = pd.DataFrame()
    time_offset = []
    # LOAD IN AND FORMAT TRAIN DATA
    for tr_file in train_file:
        if ".csv" in tr_file:
            print(f"Loading in file: {tr_file}")
            df_tmp = get_total_data(tr_file, ["timestamp", "ms", "temp"], ["temp"], ["ms"])
            dt_tmp = time_analysis.create_datetime(df_tmp["timestamp"])
            dt_seconds = [date.timestamp() for date in dt_tmp]

            # extend training time offset array ?
            time_offset.extend(
                create_time_offset(
                    np.array(df_tmp["ms"]),
                    dt_seconds)
            )

            # concatenate new DataFrame into training data
            train_df = pd.concat([train_df, df_tmp], ignore_index=True)

    datetime_f_arr = time_analysis.create_datetime(train_df["timestamp"])

    # VARIABLE SETUP
    A = least_squares.generateA(train_df["ms"], train_df["temp"])
    d = np.array(time_offset)
    d = d.reshape(-1, 1)
    pprint(A)
    print("### MATRIX A ABOVE ###")
    pprint(d)
    print("\n### MATRIX d ABOVE ###")
    print(f"\nComputing least squares with A matrix of \nt[shape, {A.shape}]\nt[type, {A.dtype}]")
    print(f"\tand d of \nt[shape, {d.shape}]\nt[type, {d.dtype}]")

    # RUN ANALYSIS
    w = least_squares.least_squares(A, d)
    w = np.array(w)
    # w = least_squares.run_prxgd(A, d)
    y = A @ w  # apply A matrix to newly found coefficients
    # w = [0.00744361959822233, 0]

    print(f"\tcoefs w are of shape: {w.shape}")
    print(f"\tshape of output y is: {y.shape}")
    [residual, e_norm] = least_squares.generate_residual(y, d)  # generate residual
    print(f"coefficients (w) found from data; computed output values (y) and formed residual")
    print(f"w: {w}")  # display coefficients
    # print(f"w2: {w2}")  # display coefficients
    print(f"Euclidean norm of this training data is: {e_norm}")  # display 2 norm of the residual

    # print out a shit ton of plots
    # plotter.time_plot(datetime_f_arr, mcu_ms, "Datetime", "Raw mcu training time")
    index = list(range(1, len(datetime_f_arr) + 1))
    # scaled_temp = datah.scale_array(A[:, 2], -1, 1)
    plotter.time_plot(index, time_offset, "Datetime", "Training time offset (ms)")
    plotter.time_plot(index, residual, "Data Entry #", "Training residual (ms)")

    temp_f_arr = temp_analysis.analyze_ICM_42670(train_df["temp"])
    plotter.time_plot(index, temp_f_arr, "Data Entry #", "Training temp", color="purple")
    return train_df


def linear_fit_train(x_arr, y_arr):
    # spit out linear fit
    print("Creating linear fit ....")
    stats = stats_analysis.linear_fit(x_arr, y_arr)
    pprint(stats)
    return stats


def verify_data(ver_file, columns):
    #####################################
    ### VERIFICATION SECTION  ###########
    #####################################
    df_ver = get_total_data(ver_file, columns, ["temp"], ["ms"])
    # df_ver = df_ver.head(480) # take first 100 samples only (useful for comparing drifts ...)
    ver_toff = np.array(
        create_time_offset(
            np.array(df_ver["ms"]),
            df_ver["dtsecond"].tolist())
    )

    df_ver["time_offset"] = ver_toff.reshape(-1, 1)
    [res, ver_e_norm] = least_squares.generate_residual(df_ver["dtsecond"], df_ver["time_offset"])
    print(f"Euclidean norm of this verification data is: {ver_e_norm}")  # display 2 norm of the residual

    # GENERATE VERIFICATION PLOTS
    print("\n\nGenerating verification plots...\n")
    min_value = df_ver["dtsecond"].min()
    result = df_ver["dtsecond"] - min_value
    df_ver["dtsecond_zero"] = result
    temp_f_arr = temp_analysis.analyze_ICM_42670(df_ver["temp"])
    plotter.time_plot(df_ver["dtsecond_zero"], df_ver["time_offset"], "Datetime seconds",
                      "Verification time offset (ms)", color="red")
    plotter.time_plot(df_ver["datetime"], temp_f_arr, "Datetime", "Verification temp (int16_t)", color="orange")
    plotter.time_plot(df_ver["datetime"], res, "Datetime", "Verification residual (ms)", color="red")
    return df_ver


if __name__ == "__main__":
    # SETTINGS
    print("clearing tmp folder ...")
    del_folder = "tmp"
    for filename in os.listdir(del_folder):
        file_path = os.path.join(del_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

    # get filepath
    basefilepath = os.getcwd() + "/../data/clock_data/"

    # basefilepath_train = basefilepath + "temp/"
    basefilepath_train = basefilepath
    training_file = []
    for file in os.listdir(basefilepath_train): # NOTE: don't need file extension check here because training function handles it
        training_file.append(basefilepath_train + file)

    # ver_file_full_path = basefilepath + "_20240417__235411_clock_test_.csv" # slope=7.20e-3
    # ver_file_full_path = basefilepath + "_20240418__000513_clock_test_.csv" # slope=7.193e-3
    ver_file_full_path = basefilepath + "_20240812__165145_clock_test_.csv"  # slope=7.193e-3

    ### TRAIN MODEL
    train_dataframe = train_model(training_file, ver_file_full_path)

    ### PERFORM VERIFICATION
    verification_df = verify_data(ver_file_full_path, ["timestamp", "ms", "temp"])
    time_dict = time_analysis.analyze_time(
        time_analysis.create_datetime(
            verification_df["timestamp"]
        ))
    pprint(time_dict)


    ### LINEAR FIT TRAIN
    # TODO: the end slope is wildly different than least squares analysis
    train_time_offset = full_create_time_offset(train_dataframe)
    linear_fit_train(train_dataframe["ms"], train_time_offset)

    # SHOW PLOTS
    print("Plot show!")
    plt.show()

    # generate pdf file AND open
    print("\nGenerating .pdf ...")
    image_folder = "tmp"
    output_pdf = "tmp/summary_document.pdf"
    logger.generate_summary_pdf(image_folder, output_pdf)

    basefilepath = "C:/Users/ander/OneDrive/Code/python/WWD/wwd_gui_api/analysis/"
    # subprocess.Popen([basefilepath + output_pdf], shell=True)
