
# import plotter modules
import matplotlib.animation as animation
from matplotlib import style
from drawnow import drawnow
import numpy as np
import matplotlib.pyplot as plt

# import needed modules
import secrets
import hashlib


def save_fig():
    random_string = secrets.token_hex(16)  # Generate 32 random hexadecimal characters (16 bytes)
    hashed_value = hashlib.sha256(random_string.encode()).hexdigest()  # Hash the random string using SHA-256
    hash_p = hashed_value[:5]  # Extract the first 5 characters of the hash to get a 5-digit hash
    plt.savefig(f'tmp/{hash_p}.png')


#################################
#### generic plotting ###########
#################################

# NOTE: not tested
def plot_3d(x_axis, y_axis, z_axis):
    # Meshgrid for plotting
    x, y = np.meshgrid(x_axis, y_axis)

    # 3D plot
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_surface(x, y, z_axis, cmap='viridis')

    ax.set_title('Frequency vs Duty Cycle vs Output Voltage')
    ax.set_xlabel('Duty Cycle (%)')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_zlabel('Output Voltage (V)')
    fig.colorbar(surf, shrink=0.5, aspect=10, label='Voltage (V)')


def plot(x_data, y_data,
         xlabel=None,
         ylabel=None,
         title=None,
         legend=None,
         color=None,
         vertical_lines=None,
         figsize=None):
    if figsize is None:
        plt.figure()
    else:
        plt.figure(figsize=figsize) # NOTE: example would be figsize=(12, 6)

    plt.plot(x_data, y_data, color=color)


    # Add vertical lines
    if vertical_lines is not None:
        for index in vertical_lines:
            plt.axvline(x=index, color='red', linestyle='--', linewidth=2)


    # annotate plot
    if xlabel is not None:
        plt.xlabel(xlabel)
    if ylabel is not None:
        plt.ylabel(ylabel)
    if title is not None:
        plt.title(title)
    if legend is not None:
        plt.legend(legend)


    plt.show()



#################################
#### liveplotting ###########
#################################

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
    def __init__(self, title, xlabel, ylabel, legend_loc="upper left"):
        style.use('fivethirtyeight')
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.xs = []
        self.ys = []

        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.legend(legend_loc)

    def show_animation(self, animate, interval=500):
        self.ani = animation.FuncAnimation(self.fig, animate, interval=interval)
        plt.show()


