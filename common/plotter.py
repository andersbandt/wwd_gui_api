
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

def plot_multi_file_data(
    file_data_list,
    x_var, y_var,
    x_scale=1, y_scale=1,
    title=None, xlabel=None, ylabel=None,
    labeling_mode='none',
    label_config=None,
    figsize=(10, 6),
    marker='o',
    markersize=3,
    show_grid=True
):
    """
    Plot data from multiple files with flexible labeling options.

    Args:
        file_data_list: List of FileData namedtuples (filename, filepath, parts, df)
                       or any iterable with (filename, filepath, parts, df)
        x_var: Column name for x-axis data
        y_var: Column name for y-axis data
        x_scale: Scale factor for x-axis data (default: 1)
        y_scale: Scale factor for y-axis data (default: 1)
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        labeling_mode: 'none', 'filename', or 'data'
        label_config: Dict with labeling configuration:
                     - For 'filename' mode: {'file_label_idx': int}
                     - For 'data' mode: {'data_label_var': str}
        figsize: Figure size tuple (width, height)
        marker: Marker style for plot
        markersize: Size of markers
        show_grid: Whether to show grid

    Returns:
        Tuple of (fig, ax) matplotlib objects

    Raises:
        KeyError: If x_var or y_var not found in dataframe
        ValueError: If label configuration is invalid
    """
    if label_config is None:
        label_config = {}

    # Set up plot
    fig, ax = plt.subplots(figsize=figsize)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if show_grid:
        ax.grid(True)
    plt.tight_layout()

    # Iterate through files and plot
    for file_data in file_data_list:
        # Unpack file data (works with namedtuple or regular tuple)
        if hasattr(file_data, 'filename'):
            # Named tuple access
            filename = file_data.filename
            file_parts = file_data.parts
            df = file_data.df
        else:
            # Regular tuple unpacking
            filename, _, file_parts, df = file_data

        # Extract x and y data
        if x_var not in df.columns:
            raise KeyError(f"Column '{x_var}' not found in {filename}")
        if y_var not in df.columns:
            raise KeyError(f"Column '{y_var}' not found in {filename}")

        x_data = df[x_var]
        y_data = df[y_var]

        # Apply labeling strategy
        if labeling_mode == 'filename':
            # Label by filename parts
            try:
                file_label_idx = label_config.get('file_label_idx', 0)
                label = file_parts[file_label_idx]
            except (ValueError, IndexError, TypeError):
                label = filename
            ax.plot(x_data * x_scale, y_data * y_scale,
                   label=label, marker=marker, markersize=markersize)

        elif labeling_mode == 'data':
            # Label by data column
            data_label_var = label_config.get('data_label_var')
            if not data_label_var:
                raise ValueError("data_label_var must be specified for 'data' labeling mode")
            if data_label_var not in df.columns:
                raise KeyError(f"Label column '{data_label_var}' not found in {filename}")

            for label_val in sorted(df[data_label_var].dropna().unique()):
                df_tmp = df[df[data_label_var] == label_val]
                label = f"{data_label_var}={label_val}"
                ax.plot(df_tmp[x_var] * x_scale, df_tmp[y_var] * y_scale,
                       label=label, marker=marker, markersize=markersize)

        else:
            # No label
            ax.plot(x_data * x_scale, y_data * y_scale,
                   marker=marker, markersize=markersize)

    # Show legend if any labels were added
    if labeling_mode in ['filename', 'data']:
        ax.legend()

    plt.show()
    return fig, ax


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



# Simple numeric normalization (works if labels are numeric or can be cast to float)
# If labels are strings, we'll just index them
# try:
#     # Attempt numeric normalization (e.g., PWM values like 0, 25, 50, 75, 100)
#     import numpy as np
#     lbl_arr = np.array(unique_labels, dtype=float)
#     vmin, vmax = lbl_arr.min(), lbl_arr.max()
#     norm_lbl = mcolors.Normalize(vmin=vmin, vmax=vmax)
#     cmap_lbl = plt.get_cmap('tab10')  # or 'viridis', 'plasma' etc.
#     color_for_label = {val: cmap_lbl(norm_lbl(float(val))) for val in unique_labels}
# except Exception:
#     # Fallback: categorical colors (e.g., strings)
#     cmap_lbl = plt.get_cmap('tab10')
#     color_for_label = {val: cmap_lbl(i % 10) for i, val in enumerate(unique_labels)}
#
# # Track which labels have already been added to the legend
# legend_added = set()


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


