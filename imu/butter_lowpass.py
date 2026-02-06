

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, freqz


def butter_lowpass(cutoff, fs, order=5):
    return butter(order, cutoff, fs=fs, btype='low', analog=False)

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y


def plot_freq_response():
    # Get the filter coefficients so we can check its frequency response.
    b, a = butter_lowpass(cutoff, fs, order)

    # Plot the frequency response.
    w, h = freqz(b, a, fs=fs, worN=8000)
    plt.subplot(2, 1, 1)
    plt.plot(w, np.abs(h), 'b')
    plt.plot(cutoff, 0.5 * np.sqrt(2), 'ko')
    plt.axvline(cutoff, color='k')
    plt.xlim(0, 0.5 * fs)
    plt.title("Lowpass Filter Frequency Response")
    plt.xlabel('Frequency [Hz]')
    plt.grid()


# Demonstrate the use of the filter.
def filter_data(data):
    print("filtering data... ")
    # First make some data to be filtered.
    T = 5.0  # seconds
    # n = int(T * fs) # total number of samples
    n = len(data)
    t = np.linspace(0, T, n, endpoint=False)

    # "Noisy" data.  We want to recover the 1.2 Hz signal from this.
    # data = np.sin(1.2*2*np.pi*t) + 1.5*np.cos(9*2*np.pi*t) + 0.5*np.sin(12.0*2*np.pi*t)

    # Filter the data, and plot both the original_b1 and filtered signals.
    y = butter_lowpass_filter(data, cutoff, fs, order)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    file_path = DATABASE_DIRECTORY + '02_imu_data.csv'

    # plot some information about the filter
    # Filter requirements.
    order = 6
    fs = 10.0  # sample rate, Hz (estimated this based on a period of 0.11 seconds between samples)
    # cutoff = 3.667  # desired cutoff frequency of the filter, Hz
    cutoff = 3

    plot_freq_response()

    # filter_data(accelerometer_data['a_y'])