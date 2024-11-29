
# import plotter modules
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
from drawnow import *

# import needed modules
import time
import secrets
import hashlib


def time_plot(x_series, y_axis, xlabel, ylabel, color=None):
    plt.figure()
    plt.plot(x_series, y_axis, color=color)
    plt.grid(True)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    save_fig()


def graph_afe(x_series, afe_d, vertical_lines=None, title=None):
    # f = plt.figure()
    plt.figure(figsize=(12, 6))

    plt.plot(x_series, afe_d)
    # plt.scatter(x_series, afe_d) # this thing honestly sucks for AFE data

    # Add vertical lines
    if vertical_lines is not None:
        for index in vertical_lines:
            plt.axvline(x=index, color='red', linestyle='--', linewidth=2)

    if title is not None:
        plt.title(title)
    else:
        plt.title('AFE ADC data')
    # plt.xlabel('Sample Number')

    plt.legend(['afe_ADC'])

    plt.tight_layout()


def save_fig():
    random_string = secrets.token_hex(16)  # Generate 32 random hexadecimal characters (16 bytes)
    hashed_value = hashlib.sha256(random_string.encode()).hexdigest()  # Hash the random string using SHA-256
    hash_p = hashed_value[:5]  # Extract the first 5 characters of the hash to get a 5-digit hash
    plt.savefig(f'tmp/{hash_p}.png')


# Create a function that makes our desired plot
def makeFig(self):
    plt.title('Sensor data')  # Set the title
    plt.grid(True)  # Set The grid
    plt.ylabel('Axis Acceleration')  # Label the y axis
    plt.plot(self.afe_adc, 'ro-', label='AFE data')  # Set the line plot


def live_plot(self, data):
    plt.ion()
    update_frequency = 10

    # Ensure that index is not out of range
    if len(data) > 1:
        adc = int(data[2])
        self.afe_adc.append(adc)

        # trim array
        self.plot_cnt = self.plot_cnt + 1
        if self.plot_cnt > 100:
            self.afe_adc.pop(0)

    if self.plot_cnt % update_frequency == 0:
        drawnow(self.makeFig)
        # self.makeFig() # GPT suggested not using drawnow() but I haven't gotten this to work
        plt.pause(.00000001)


class LivePlot:
    def __init__(self):
        style.use('fivethirtyeight')
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.xs = []
        self.ys = []

        self.ax.set_title("Live Current Reading")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Current (A)")
        self.ax.legend(loc="upper left")


    def show_animation(self, animate, interval=500):
        self.ani = animation.FuncAnimation(self.fig, animate, interval=interval)
        plt.show()


