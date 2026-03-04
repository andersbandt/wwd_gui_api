"""Clock and time-domain analysis."""

# import needed modules
import logging
import pandas as pd
import numpy as np
from pprint import pformat
import subprocess
import os
import shutil
from matplotlib import pyplot as plt

# import user created modules
from analysis import stats_analysis
from analysis import data_helper as datah
from analysis.specific import least_squares
from common import plotter
from common.plotter import show_plots


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)


def clean_data(df, column, column2=None):
    _logger.info("Cleaning data ....")
    _logger.debug(f"data starting with row count: {df.shape[0]}")
    # drop out nAn values
    df = df.replace('', np.nan)
    df = df.dropna()

    # Filter out data points that fall below the lower threshold or above the upper threshold
    # NOTE: the .shift() command moves towards the end of the series by default
    df = df[df[column] >= df[column].shift(1)]
    df = df[df[column] >= df[column].shift(1)]
    df = df[df[column] >= df[column].shift(1)]

    _logger.debug(f"filter on column '{column}' yields row count: {df.shape[0]}")

    temp_shift = 10  # max shift between temp samples allowed
    if column2:
        df = df[df[column2] - df[column2].shift(1) <= temp_shift]
        df = df[df[column2] - df[column2].shift(1) <= temp_shift]
        _logger.debug(f"filter on column '{column2}' yields row count: {df.shape[0]}")

    # reset the starting value to be at 0
    min_value = df[column].min()
    result = df[column] - min_value
    df[column] = result

    return df


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
        _logger.debug(z_score)

        # If the z-score exceeds the threshold, mark the index for removal
        threshold = 0.01
        if z_score > threshold:
            filtered_indices.append(i)

    # Remove rows with filtered indices
    # data_arr_f = np.delete(data_arr, filtered_indices, axis=0)
    data_arr_f = data_arr.drop(filtered_indices)

    return data_arr_f


def get_train_data_old(file, col_str, float_col, clean_col):
    df = datah.load_csv_pandas(file, columns=col_str)

    if float_col is not None:
        for col in float_col:
            df = datah.df_float(df, col)

    if clean_col is not None:
        for col in clean_col:
            df = clean_data(df, col)

    return df



def get_train_data(
    file,
    col_str,                # list[str]: columns to load
    float_cols=None,        # list[str] to cast to float
    clean_cols=None,        # list[str] to clean with your clean_data()
    *,
    loop_col="BO", # str: binary 0/1 column for clamp
    volt_col="TP",        # str: continuous voltage column
    window=30,              # int: pre-activation samples for baseline
    min_samples=10,          # int: minimum samples to accept baseline
    use_median=True         # bool: use median (robust) or mean
):
    """
    Load and prepare a DataFrame with baseline features for a clamp loop.

    Adds columns:
      _baseline          : baseline computed from pre-activation window (NaN if not active/insufficient)
      _baseline_filled   : baseline filled with var4 when NaN
      _baseline_valid    : 1 if baseline valid for that row, else 0
      _delta             : _baseline_filled - var4
      _rising_idx        : 1 at 0->1 rising edge rows, else 0
    """
    # 0) Load & prep
    df = datah.load_csv_pandas(file, columns=col_str)

    if float_cols:
        for col in float_cols:
            df = datah.df_float(df, col)

    if clean_cols:
        for col in clean_cols:
            df = clean_data(df, col)

    # 1) Sanity checks
    for col in (loop_col, volt_col):
        if col not in df.columns:
            raise KeyError(f"Column '{col}' not found. Available: {list(df.columns)}")

    # 2) Extract arrays
    loop = df[loop_col].to_numpy().astype(np.int8)        # (N,)
    var4 = df[volt_col].to_numpy().astype(np.float64)     # (N,)
    N = len(df)

    # 3) Rising edges: indices where loop changes 0 -> 1
    rising = np.flatnonzero((loop[1:] == 1) & (loop[:-1] == 0)) + 1

    # 4) Compute baseline per active episode
    baseline = np.full(N, np.nan, dtype=np.float64)

    for idx in rising:
        start = max(0, idx - window)
        window_vals = var4[start:idx]
        if window_vals.size >= min_samples:
            base = np.median(window_vals) if use_median else np.mean(window_vals)
            # forward-fill while loop is active
            end = idx
            while end < N and loop[end] == 1:
                end += 1
            baseline[idx:end] = base
        # else: leave as NaN (insufficient pre-samples)

    # 5) Fill/flags/derived
    baseline_valid = (~np.isnan(baseline)).astype(np.float64)
    baseline_filled = np.where(np.isnan(baseline), var4, baseline)
    delta = baseline_filled - var4

    # 6) Attach to df
    df["_baseline"] = baseline
    df["_baseline_filled"] = baseline_filled
    df["_baseline_valid"] = baseline_valid
    df["_delta"] = delta
    df["_rising_idx"] = 0
    if len(rising) > 0:
        df.loc[rising, "_rising_idx"] = 1

    return df



# TODO: somehow add some usage notes that we need any time variables to be called `timestamp`
#if "timestamp" in col_str:
#    df["datetime"] = stats_analysis.create_datetime(df["timestamp"])
#    df["dtsecond"] = [date.timestamp() for date in df["datetime"]]


def get_truth_data(file, col_str):
    df = datah.load_csv_pandas(file, columns=col_str)
    truth = df[col_str]
    return truth


# TODO: have Claude fix this specialized function. Can follow the custom function I have for training data
def get_clock_truth_data():
    # dt_tmp = stats_analysis.create_datetime(df_tmp["timestamp"])
    # dt_seconds = [date.timestamp() for date in dt_tmp]
    #
    # extend training time offset array ?
    # time_offset.extend(
    #     create_time_offset(
    #         np.array(df_tmp["ms"]),
    #         dt_seconds)
    # )
    pass



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
    dt_tmp = stats_analysis.create_datetime(df_tmp["timestamp"])
    dt_seconds = [date.timestamp() for date in dt_tmp]
    time_offset.extend(
        create_time_offset(
            np.array(df_tmp["ms"]),
            dt_seconds)
    )
    return time_offset


# TODO: I think I can clean up the argument passing in here
# TODO: all the time stuff needs to be removed away, but still accessible
def train_model(train_file, columns, float_col, clean_col, truth_col):
    train_df = pd.DataFrame()
    truth_df = pd.DataFrame()

    # LOAD IN AND FORMAT TRAIN DATA
    for tr_file in train_file:
        if ".csv" in tr_file:
            _logger.info(f"Loading in file: {tr_file}")
            df_train_tmp = get_train_data(tr_file, columns, float_col, clean_col)
            df_truth_tmp = get_truth_data(tr_file, truth_col)

            # concatenate new DataFrame into training data
            train_df = pd.concat([train_df, df_train_tmp], ignore_index=True)
            truth_df = pd.concat([truth_df, df_truth_tmp], ignore_index=True)

    print(list(train_df.columns))
    train_df.info()

    # VARIABLE SETUP
    # TODO: I also think I can cleanup the variable mapping to generateA
    #A = least_squares.generateA(train_df["PV"], train_df["MV"], train_df["BO"], train_df["TP"], train_df["_baseline_filled"])

    A = np.column_stack((
        np.ones(len(train_df)),  # 1) intercept
        train_df["TP"],  # 2) natural measurement (BO=0 useful)
        train_df["BO"],  # 3) regime indicator
        train_df["_baseline_filled"],  # 4) baseline (pre-activation)
        train_df["BO"] * train_df["_baseline_filled"],  # 5) baseline effect only when clamped
        train_df["BO"] * (train_df["_baseline_filled"] - train_df["TP"]),  # 6) pull distance (delta) only when clamped
        #train_df["PV"],  # 7) optional extra predictors
        train_df["MV"]
    ))

    d = np.array(truth_df)
    d = d.reshape(-1, 1)
    print("MATRIX A:\n%s", pformat(A))
    print("MATRIX d:\n%s", pformat(d))
    _logger.info(f"Computing least squares with A matrix of shape={A.shape} dtype={A.dtype}")
    _logger.info(f"and d of shape={d.shape} dtype={d.dtype}")

    # RUN ANALYSIS
    w = least_squares.least_squares(A, d)
    w = np.array(w)
    y = A @ w  # apply A matrix to newly found coefficients

    print(f"coefs w are of shape: {w.shape}")
    print(f"shape of output y is: {y.shape}")
    print(f"coefficients (w) found from data; computed output values (y) and formed residual")
    print(f"w: {w}")  # display coefficients

    # TODO: move this stuff to a separate verification function
    [res, ver_e_norm] = least_squares.generate_residual(y, d)
    print(res)
    print(ver_e_norm)

    # TODO: make it so I can somehow make nice subplots here?
    plotter.plot([i for i in range(len(truth_df))], res, show_plot=False)
    plotter.plot([i for i in range(len(truth_df))], train_df["TP_O"], show_plot=False)
    plotter.plot([i for i in range(len(truth_df))], train_df["TP"], show_plot=False)
    plotter.plot([i for i in range(len(truth_df))], train_df["BO"], show_plot=False)
    show_plots()

    return train_df, y, w


def linear_fit_train(x_arr, y_arr):
    # spit out linear fit
    _logger.info("Creating linear fit ....")
    stats = stats_analysis.linear_fit(x_arr, y_arr)
    _logger.info(pformat(stats))
    return stats


def verify_data(ver_file, columns, float_col, clean_col, truth_col):
    #####################################
    ### VERIFICATION SECTION  ###########
    #####################################
    df_ver = get_train_data(ver_file, columns, float_col, clean_col)
    df_truth = get_truth_data(ver_file, truth_col)


    [res, ver_e_norm] = least_squares.generate_residual(df_ver["dtsecond"], df_ver["time_offset"])
    _logger.info(f"Euclidean norm of this verification data is: {ver_e_norm}")  # display 2 norm of the residual

    # GENERATE VERIFICATION PLOTS
    _logger.info("Generating verification plots...")
    min_value = df_ver["dtsecond"].min()
    result = df_ver["dtsecond"] - min_value
    df_ver["dtsecond_zero"] = result

    plotter.time_plot(df_ver["dtsecond_zero"], df_ver["time_offset"], "Datetime seconds",
                      "Verification time offset (ms)", color="red")
    plotter.time_plot(df_ver["datetime"], temp_f_arr, "Datetime", "Verification temp (int16_t)", color="orange")
    plotter.time_plot(df_ver["datetime"], res, "Datetime", "Verification residual (ms)", color="red")
    return df_ver



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")

    # TODO: have claude turn this into a separate function too
    # SETTINGS
    _logger.info("clearing tmp folder ...")
    del_folder = "analysis/tmp"
    for filename in os.listdir(del_folder):
        file_path = os.path.join(del_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            _logger.error('Failed to delete %s. Reason: %s' % (file_path, e))

    # set up training data
    basefilepath_train = os.getcwd() + "/data_shared/"
    training_files = []
    for file in os.listdir(basefilepath_train): # NOTE: don't need file extension check here because training function handles it
        training_files.append(basefilepath_train + file)

    # set up verification data
    ver_file_full_path = training_files[0]

    ### TRAIN MODEL
    headers = ["PV", "MV", "BO", "TP", "TP_O"]
    train_dataframe, train_y, train_w = train_model(training_files, headers, None, None, ["TP_O"])

    ### PERFORM VERIFICATION
    # verification_df = verify_data(ver_file_full_path, headers, None, None, ["TP_O"])
    # time_dict = stats_analysis.analyze_time(
    #     stats_analysis.create_datetime(
    #         verification_df["timestamp"]
    #     ))
    # _logger.info(pformat(time_dict))


    ### LINEAR FIT TRAIN
    # NOTE: the end slope is wildly different than least squares analysis
    #  HINT: (ONLY WHEN I USE AN ARRAY OF TRAINING DATA) one for one training / verification works ...!!!
    # train_time_offset = full_create_time_offset(train_dataframe)
    # linear_fit_train(train_dataframe["ms"], train_time_offset)

    # SHOW PLOTS
    _logger.info("Plot show!")
    # plt.show()
    #
    # # generate pdf file AND open
    # _logger.info("Generating .pdf ...")
    # image_folder = "tmp"
    # output_pdf = "tmp/summary_document.pdf"
    # logger.generate_summary_pdf(image_folder, output_pdf)
    #
    # subprocess.Popen([basefilepath_train + output_pdf], shell=True)
