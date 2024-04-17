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
from analysis import least_squares
from analysis import time_analysis
from analysis import stats_analysis
from common import plotter
from data import data_helper as datah
from common import logger


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

    temp_shift = 10 # max shift between temp samples allowed
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



def verify_data(ver_file, columns):
    #####################################
    ### VERIFICATION SECTION  ###########
    #####################################
    df_ver = datah.load_csv_pandas(ver_file, columns=columns)
    df_ver = datah.df_float(df_ver, "temp")
    df_ver = clean_data(df_ver, "ms")
    ver_dtime = time_analysis.create_datetime(df_ver["timestamp"])
    ver_dtsec = [date.timestamp() for date in ver_dtime]
    ver_toff = np.array(
        create_time_offset(
            np.array(df_ver["ms"]),
            ver_dtsec)
    )
    holdout = least_squares.generateA(df_ver["ms"], df_ver["temp"])
    print(f"\n\nVerification data is of numpy type: {holdout.dtype}\n\tand type: {type(holdout)}")
    print(f"Coefficients w are of numpy type: {w.dtype}\n\tand type: {type(w)}")
    # y_holdout = holdout @ w
    y_holdout = np.dot(holdout, w)

    ver_time_offset = ver_toff.reshape(-1, 1)
    [res, ver_e_norm] = least_squares.generate_residual(y_holdout, ver_time_offset)
    print(f"Euclidean norm of this verification data is: {ver_e_norm}")  # display 2 norm of the residual
    print("\n\nGenerating verification plots...\n")
    plotter.time_plot(ver_dtime, ver_time_offset, "Datetime", "Verification time offset (ms)", color="red")
    plotter.time_plot(ver_dtime, res, "Datetime", "Verification residual (ms)", color="red")
    plotter.time_plot(ver_dtime, df_ver["temp"], "Datetime", "Verification temp", color="orange")
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
    basefilepath = "C:/Users/ander/OneDrive/Code/python/WWD/wwd_gui_api/data/clock_data/"
    pre_temp_file = ["_20240409__215040_clock_test_.csv",
                     "_20240409__215558_clock_test_.csv",
                     "_20240409__215645_clock_test_.csv",
                     "_20240409__220025_clock_test_.csv",
                     "_20240411__195755_clock_test_.csv",
                     "_20240415__210006_clock_test_.csv",
                     "_20240416__110848_clock_test_.csv",
                     "_20240415__223453_clock_test_.csv"]

    train_folder = basefilepath
    train_file = os.listdir(train_folder)
    # ver_file = basefilepath + "_20240416__202039_clock_test_.csv"
    # ver_file = basefilepath + "_20240416__203234_clock_test_.csv"
    # ver_file = basefilepath + "_20240416__225652_clock_test_.csv"
    # ver_file = basefilepath + "_20240417__103744_clock_test_.csv"
    ver_file = basefilepath + "_20240417__171147_clock_test_.csv"

    filtered_data_arr = pd.DataFrame()
    time_offset = []
    # LOAD IN AND FORMAT TRAIN DATA
    for file in train_file:
        if ".csv" in file:
            if file not in ver_file:
                df_tmp = datah.load_csv_pandas(basefilepath + file, ["timestamp", "ms", "temp"])
                df_tmp = datah.df_float(df_tmp, "temp")
                df_tmp = clean_data(df_tmp, "ms", "temp")
                # df_tmp = get_filtered_data(df_tmp, "ms")
                dt_tmp = time_analysis.create_datetime(df_tmp["timestamp"])
                dt_seconds = [date.timestamp() for date in dt_tmp]
                time_offset.extend(
                    create_time_offset(
                        np.array(df_tmp["ms"]),
                        dt_seconds)
                )
                # filtered_data_arr = pd.concat(filtered_data_arr, df_tmp)
                filtered_data_arr = filtered_data_arr.append(df_tmp)

    datetime_f_arr = time_analysis.create_datetime(filtered_data_arr["timestamp"])

    # VARIABLE SETUP
    A = least_squares.generateA(filtered_data_arr["ms"], filtered_data_arr["temp"])
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
    # [residual, euclidean_norm] = least_squares.generate_residual(y, d)  # generate residual
    # w = [0.00744361959822233, 97.17110567685813]

    # do a second layer
    # A = least_squares.generateA(y)
    # # w2 = least_squares.least_squares(A, residual)
    # w2 = least_squares.run_prxgd(A, residual)
    # y2 = least_squares.generateA(y) @ w2

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
    plotter.time_plot(index, filtered_data_arr["temp"], "Data Entry #", "Training temp", color="purple")


    ### PERFORM VERIFICAITON
    verification_df = verify_data(ver_file, ["timestamp", "ms", "temp"])

    time_dict = time_analysis.analyze_time(
        time_analysis.create_datetime(
            verification_df["timestamp"]
        ))
    pprint(time_dict)


    # SHOW PLOTS
    print("Plot show!")
    plt.show()

    # spit out linear fit
    # print("Creating linear fit ....")
    # stats = stats_analysis.linear_fit(filtered_data_arr["ms"], time_offset)
    # time_stats = analyze_time(datetime_f_arr)
    #
    # pprint.pprint(stats)
    # pprint.pprint(time_stats)
    # # plt.show()
    #
    #
    # # HACK calculation
    # mcu_dur = (filtered_pd_frame["ms"].iloc[-1] - filtered_pd_frame["ms"].iloc[0]) * pow(10, -3) / 60
    # print(f"MCU duration (raw): {mcu_dur}")
    # hack_offset_secs = (time_stats['dur_min'] - mcu_dur) * 60
    # print(f"hack offset: {hack_offset_secs}")

    # generate pdf file AND open
    print("\nGenerating .pdf ...")
    image_folder = "tmp"
    output_pdf = "tmp/summary_document.pdf"
    logger.generate_summary_pdf(image_folder, output_pdf)

    basefilepath = "C:/Users/ander/OneDrive/Code/python/WWD/wwd_gui_api/analysis/"
    # subprocess.Popen([basefilepath + output_pdf], shell=True)
    # os.startfile()
