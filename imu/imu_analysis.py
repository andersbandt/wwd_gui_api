

# import needed modules
import pandas as pd
import pandas.errors
import numpy as np
import matplotlib.pyplot as plt


DATABASE_DIRECTORY = "C:/Users/ander/OneDrive/Projects/WWD/sys/imu_data_dir/"


def graph_accel_gyro(a_dat, g_dat):
    # Plot accelerometer data
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(a_dat)
    plt.title('Accelerometer Data')
    plt.xlabel('Sample')
    plt.ylabel('Acceleration (m/s^2)')
    plt.legend(['a_x', 'a_y', 'a_z'])

    # Plot gyroscope data
    plt.subplot(2, 1, 2)
    plt.plot(g_dat)
    plt.title('Gyroscope Data')
    plt.xlabel('Sample')
    plt.ylabel('Angular Velocity (rad/s)')
    plt.legend(['g_x', 'g_y', 'g_z'])
    plt.tight_layout()
    plt.show()


def graph_filter_unfilter(data, filtered_data, num_plot, subplot_num):
    # set up time-series axis
    T = 5.0
    n = len(data)
    t = np.linspace(0, T, n, endpoint=False)

    # make plot
    plt.subplot(num_plot, 1, subplot_num) # rows, columns, number
    plt.plot(t, data, 'b-', label='data')
    plt.plot(t, filtered_data, 'g-', linewidth=2, label='filtered data')
    # plt.xlabel('Time [sec]')
    plt.grid()
    plt.legend()



# C compatible implementation of a simple lowpass filter
def c_lowpass(x, xm1, a):
    y = [x[0] + xm1]

    for i in range(1, len(x)):
        # y_0 = (1-a) * y[i-1] + a*(x[i] - x[i-1])/2
        y_0 = (1-a) * y[i-1] + a*(x[i])
        # y_0 = y[i-1] + a*(x[i] - x[i-1])
        y.append(y_0)

    return y



def analyze_imu(file_path):
    # Load data from CSV file
    try:
        df = pd.read_csv(file_path)
    except pandas.errors.EmptyDataError as e:
        print(e)
        return False

    # Extract columns
    accelerometer_data = df[['a_x', 'a_y', 'a_z']]
    gyroscope_data = df[['g_x', 'g_y', 'g_z']]

    fs = 10.0  # sample rate, Hz (estimated this based on a period of 0.11 seconds between samples)
    cutoff = 3

    graph_accel_gyro(accelerometer_data, gyroscope_data)


    # set up graphing and alpha (filter) parameters
    N = 4
    min = 0.2
    max = 0.8
    space = (max - min)/N

    i = 1
    for a in np.arange(min, max, space):
        data = accelerometer_data['a_z']
        f_d = c_lowpass(data, 0, a)
        graph_filter_unfilter(data, f_d, N, i)

        plt.title("Filtered data w/ a=" + str(a))
        i += 1

    plt.show()



def conv_imu_flash(upper_byte, lower_byte):
    imu_data = (upper_byte >> 8) + lower_byte
    return imu_data

