
from datetime import datetime
import matplotlib.pyplot as plt

from scipy.fft import fft, fftfreq
from scipy import signal
from scipy.signal.windows import blackman
#from scipy.signal import butter, lfilter, hamming
from scipy.stats import skew, kurtosis
from scipy.signal import find_peaks

import numpy as np

from common import plotter


####################################
###   Filtering       ##############
####################################

def calculate_frequency(peak_positions, sampling_rate):
    # Calculate the time between consecutive peaks
    time_between_peaks = np.diff(peak_positions) / sampling_rate
    print(time_between_peaks)
    print(len(peak_positions))
    print(len(time_between_peaks))
    print(f"sampling rate is: {sampling_rate}")
    # Calculate the average time between peaks
    avg_time_between_peaks = np.mean(time_between_peaks)
    # Calculate frequency (Hz)
    frequency = 1 / avg_time_between_peaks
    return frequency


def peak_detect_hr(data_arr, sample_rate, duration, show_plot=True):
    data_arr = np.array(data_arr)
    peaks, _ = find_peaks(data_arr,
                          height=0,
                          threshold=0,
                          distance=8)
    print(peaks)
    print("Found peaks above")

    # Plot the data array along with markers for the identified peaks
    if show_plot:
        plotter.graph_afe(
            list(range(0, len(data_arr))),
            data_arr,
            vertical_lines=None)
        plt.scatter(peaks, data_arr[peaks], color='red', marker='x', label='Peaks')
        plt.title('Data Array with Identified Peaks')
        plt.xlabel('Index')
        plt.ylabel('Value')
        plt.legend()
        plt.show()

    heart_rate = calculate_frequency(peaks, sample_rate)*60
    return heart_rate


def simple_moving_average(data, window_size):
    cumsum = np.cumsum(data)
    cumsum[window_size:] = cumsum[window_size:] - cumsum[:-window_size]
    return cumsum[window_size - 1:] / window_size


def cheby2_filter(data, rs, Wn, sample_rate):
    sos = signal.cheby2(20, # order of filter
                        rs, # float. Minimum attenuation required in the stop band
                        Wn, # Critical frequencies
                        'lp',
                        fs=sample_rate,
                        output='sos') # type of output: numerator/denominator (ba) or second order sections (sos)
    filtered = signal.sosfilt(sos, data)
    return filtered


def butter_bandpass_filter(data, lowcut, highcut, sample_rate, order=4):
    nyquist = 0.5 * sample_rate
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    y = lfilter(b, a, data)
    return y


def find_transitions(data_array):
    trans = []

    d_prev = 0
    i = 0
    for d in data_array:
        if d_prev != d:
            print(f"Transition found at: {i} !")
            trans.append(i)
        d_prev = d
        i += 1
    return trans


####################################
###   FFT analysis    ##############
####################################

def compute_fft(data_arr, sr):
    print("\n### COMPUTING FFT ###")
    # compute sampling interval
    T = 1.0/sr
    tr = np.arange(0, 1, T)

    # Number of sample points
    N = len(data_arr)
    print(f"\tnum samples: {N}")

    print(data_arr)
    print(type(data_arr))

    # do analysis
    w = blackman(N)

    yf = fft(data_arr)
    ywf = fft(data_arr*w)

    xf = fftfreq(N, T)[:N // 2]

    plt.figure(figsize=(12, 6))
    # plt.plot(xf, 2.0 / N * np.abs(yf[0:N // 2]))
    plt.semilogy(xf[1:N // 2], 2.0 / N * np.abs(yf[1:N // 2]), '-b')
    plt.semilogy(xf[1:N // 2], 2.0 / N * np.abs(ywf[1:N // 2]), '-r')
    plt.legend(['FFT', 'FFT w. window'])

    plt.grid()


def compute_fft_2(data, sample_rate):
    # Calculate the FFT
    fft_result = np.fft.fft(data)
    fft_freq = np.fft.fftfreq(len(data), d=1 / sample_rate)

    # Take the absolute value of the FFT result to get the magnitude spectrum
    fft_magnitude = np.abs(fft_result)

    # Plot the FFT (focus on positive frequencies)
    plt.figure(figsize=(10, 5))
    plt.plot(fft_freq[:len(fft_freq) // 2], fft_magnitude[:len(fft_magnitude) // 2])
    plt.title('FFT of Data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.yscale('log')  # Use a logarithmic scale for better visualization
    plt.grid(True)
    plt.show()


def find_peak_frequency(fft_freq, fft_magnitude):
    # Find the index of the peak magnitude
    peak_index = np.argmax(fft_magnitude)
    # Extract the corresponding frequency
    peak_frequency = fft_freq[peak_index]
    return peak_frequency


def plot_fft_with_windowing(data, sample_rate, lowcut, highcut):
    # Apply Hamming window to the signal
    windowed_data = data * hamming(len(data))

    # Apply bandpass filter to focus on the frequency range of interest
    filtered_data = butter_bandpass_filter(windowed_data, lowcut, highcut, sample_rate)

    # Calculate the FFT
    fft_result = np.fft.fft(filtered_data)
    fft_freq = np.fft.fftfreq(len(filtered_data), d=1 / sample_rate)

    # Take the absolute value of the FFT result to get the magnitude spectrum
    fft_magnitude = np.abs(fft_result)

    # Find the peak frequency in the filtered FFT
    peak_frequency = find_peak_frequency(fft_freq[:len(fft_freq) // 2], fft_magnitude[:len(fft_magnitude) // 2])
    peak_magnitude = np.max(fft_magnitude)
    print(f"\tpeak magnitude at freq: {peak_frequency}")
    print(f"\theart rate of: {peak_frequency*60} BPM")

    # Take the absolute value of the FFT result to get the magnitude spectrum
    fft_magnitude = np.abs(fft_result)

    plt.figure(figsize=(10, 5))

    # Mark the peak frequency with a red dot
    plt.scatter(peak_frequency, peak_magnitude, color='red', label=f'Peak Frequency: {peak_frequency:.2f} Hz')

    # Plot the FFT (focus on positive frequencies)
    plt.plot(fft_freq[:len(fft_freq) // 2], fft_magnitude[:len(fft_magnitude) // 2])
    plt.title('FFT of Data with Windowing and Bandpass Filtering')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.yscale('log')  # Use a logarithmic scale for better visualization
    plt.grid(True)
    plt.show()

####################################
###   STATS analysis    ############
####################################

def calculate_statistics(data):
    max_value = np.max(data)
    min_value = np.min(data)
    data_range = np.ptp(data)
    mean_value = np.mean(data)
    median_value = np.median(data)
    mode_value = float(np.argmax(np.bincount(data)))
    std_deviation = np.std(data)
    variance = np.var(data)
    skewness = skew(data)
    kurt = kurtosis(data)

    return {
        "max": max_value,
        "min": min_value,
        "range": data_range,
        # "mean": mean_value,
        # "median": median_value,
        # "mode": mode_value,
        "standard Deviation": std_deviation,
        "variance": variance,
        # "skewness": skewness,
        # "kurtosis": kurt
    }





####################################
###   main AFE function    #########
####################################

def analyze_afe(afe_d):
    # calculate raw statistics and add some calculated ones
    data_arr = afe_d["data"].tolist()
    stats_dict = calculate_statistics(data_arr)
    time_dict = analyze_time(afe_d)
#    afe_dict = stats_dict | time_dict # make one master dict by appending the two dict
    afe_dict = dict(stats_dict, **time_dict)

    # Print the results
    print("\n\n")
    for stat, value in afe_dict.items():
        print(f"{stat}: {value}")

    # apply some filtering
    mov_data_arr = simple_moving_average(data_arr, 1)

    ### DO FFT ANALYSIS
    # fft_output = anah.compute_fft(data_arr, data_freq)
    # mov_fft_output = anah.compute_fft(mov_data_arr, data_freq)
    # anah.compute_fft_2(data_arr, data_freq)
    # anah.plot_fft_with_windowing(data_arr, data_freq, .001, 4)
    # anah.plot_fft_with_windowing(mov_data_arr, data_freq, .001, 4)

    ### PEAK DETECTION to HR
    heart_rate = peak_detect_hr(mov_data_arr,
                                afe_dict['frequency'],
                                afe_dict['duration'].total_seconds(),
                                show_plot=False)
    print(f"heart rate: {heart_rate}")
    afe_dict["HR (BPM)"] = heart_rate
    afe_dict["HR (Hz)"] = heart_rate/60

    return afe_dict


def graph_afe(afe_d):
    afe_dict = analyze_afe(afe_d)
    data_arr = afe_d["data"].tolist()
    plt.close('all')

    # graph
    plotter.graph_afe(
        np.linspace(0, afe_dict['duration'].total_seconds(), len(data_arr), endpoint=False),
        data_arr,
        vertical_lines=None,
        title="Raw ADC data")

    # apply some filtering
    # mov_data_arr = simple_moving_average(data_arr, 8)
    # plotter.graph_afe(
    #     np.linspace(0, afe_dict['duration'].total_seconds(), len(mov_data_arr), endpoint=False),
    #     mov_data_arr,
    #     vertical_lines=None,
    #     title="Simple moving average")

    # cheby filter
    # cheby_data_arr = cheby2_filter(data_arr, 5, 15, afe_dict['frequency'])
    # plotter.graph_afe(
    #     np.linspace(0, afe_dict['duration'].total_seconds(), len(cheby_data_arr), endpoint=False),
    #     cheby_data_arr,
    #     vertical_lines=None,
    #     title="Chebyshev type II")

    # butter bandpass
    # butter_data_arr = butter_bandpass_filter(data_arr, .00000001, 15, afe_dict['frequency'], order=4)
    # plotter.graph_afe(
    #     np.linspace(0, afe_dict['duration'].total_seconds(), len(butter_data_arr), endpoint=False),
    #     butter_data_arr,
    #     vertical_lines=None,
    #     title="Butterworth bandpass")

    ### DO FFT ANALYSIS
    fft_output = compute_fft(data_arr, afe_dict['frequency'])

    heart_rate = peak_detect_hr(data_arr,
                                afe_dict['frequency'],
                                afe_dict['duration'].total_seconds(),
                                show_plot=True)
    plt.show()


### ANALYZE TRANSITIONS
# prev_trans = datetime_arr[0]
# transitions = anah.find_transitions(afe_d['data'])
# print(transitions)
# for transition in transitions:
#     print(f"\ttransition was found at index {transition}: "
#           f"{afe_d['timestamp'].iloc[transition]}")
#     T = (datetime_arr[transition] - prev_trans).total_seconds()
#     print(f"\ttime was: {T}")
#     prev_trans = datetime_arr[transition]
