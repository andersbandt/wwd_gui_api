"""Real-time and static plotting utilities."""

# import plotter modules
import logging
import numpy as np

logger = logging.getLogger(__name__)
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib import cm
from matplotlib.ticker import MaxNLocator
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Output, Input
from datetime import datetime as _dt

# import needed modules
import threading
import webbrowser
from pathlib import Path
from typing import Mapping, Sequence
from collections import deque
from queue import Queue, Empty

# import user created modules
from analysis.specific import filter_analysis


# Matplotlib default color cycle — shared across all plot types for visual consistency.
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
          '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# Line styles for distinguishing multiple files in combined labeling mode
LINE_STYLES = ['-', '--', '-.', ':']  # solid, dashed, dash-dot, dotted


def show_plots():
    plt.show()


#################################
#### generic plotting ###########
#################################

def plot(
        x_data,
        y_data,
         xlabel=None,
         ylabel=None,
         title=None,
         legend=None,
         color=None,
         vertical_lines=None,
         figsize=None,
         show_plot=True):
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
        plt.xticks(rotation=90)
    if ylabel is not None:
        plt.ylabel(ylabel)
    if title is not None:
        plt.title(title)
    if legend is not None:
        plt.legend(legend)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if show_plot:
        plt.show()


def plot_grouped(df, x_var, y_var, group_var,
                 xlabel=None, ylabel=None, title=None,
                 figsize=(10, 6), marker='o', markersize=3):
    """
    2D plot with one line per unique value of group_var.

    Args:
        df: DataFrame containing all data
        x_var: Column name for x-axis
        y_var: Column name for y-axis
        group_var: Column name to group by (each unique value becomes a labeled series)
    """
    fig, ax = plt.subplots(figsize=figsize)

    for i, group_val in enumerate(sorted(df[group_var].dropna().unique())):
        subset = df[df[group_var] == group_val]
        ax.plot(subset[x_var], subset[y_var],
                label=f"{group_var}={group_val}",
                color=COLORS[i % len(COLORS)],
                marker=marker, markersize=markersize)

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()
    return fig, ax


def plot_subplots(x_data, channels, xlabel=None, title=None, figsize_per_row=4, show_plot=True):
    """
    Stacked subplots with shared x-axis, one subplot per channel.

    Args:
        x_data: Shared x-axis data (array-like)
        channels: List of (y_data, ylabel) tuples for each subplot
        xlabel: Label for the shared x-axis (bottom only)
        title: Overall figure title
        figsize_per_row: Height per subplot row in inches
        show_plot: If True, call plt.show() immediately
    """
    n = len(channels)
    fig, axes = plt.subplots(n, 1, figsize=(10, figsize_per_row * n),
                             sharex=True)
    if n == 1:
        axes = [axes]

    for i, (ax, (y_data, ylabel)) in enumerate(zip(axes, channels)):
        ax.plot(x_data, y_data, color=COLORS[i % len(COLORS)])
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel(xlabel or "")
    if title:
        fig.suptitle(title)
    plt.tight_layout()
    if show_plot:
        plt.show()
    return fig, axes


def plot_3d_from_df(df, x_var, y_var, z_var,
                    xlabel=None, ylabel=None, zlabel=None,
                    title=None, figsize=(10, 7), cmap='viridis'):
    """
    3D surface plot from a DataFrame with two sweep variables and a measurement.

    Pivots the DataFrame into a meshgrid and plots a surface.
    Works directly with dual-stimulus sweep data.

    Args:
        df: DataFrame with columns x_var, y_var, z_var
        x_var: Column for x-axis (e.g., outer stimulus)
        y_var: Column for y-axis (e.g., inner stimulus)
        z_var: Column for z-axis (e.g., measurement)
    """
    # Pivot to get z as a 2D grid indexed by (y_var, x_var)
    pivot = df.pivot_table(index=y_var, columns=x_var, values=z_var, aggfunc='mean')
    x_vals = pivot.columns.values.astype(float)
    y_vals = pivot.index.values.astype(float)
    X, Y = np.meshgrid(x_vals, y_vals)
    Z = pivot.values

    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    surf = ax.plot_surface(X, Y, Z, cmap=cmap, edgecolor='none', alpha=0.9)

    ax.set_xlabel(xlabel or x_var)
    ax.set_ylabel(ylabel or y_var)
    ax.set_zlabel(zlabel or z_var)
    if title:
        ax.set_title(title)
    fig.colorbar(surf, shrink=0.5, aspect=10, label=zlabel or z_var)
    plt.tight_layout()
    plt.show()
    return fig, ax


def plot_trendline(setpoints, measured,
                          x_label="Set Value",
                          y_label="Measured Value",
                          title="Accuracy Plot"):
    """
    Simple generic accuracy plot:
    - Plots measured vs. setpoints
    - Adds an ideal 1:1 line (VERY BASIC, literally just linear best fit with the first and last point)
        so your dataset should already be linear for it to work well
    """

    setpoints = np.array(setpoints)
    measured = np.array(measured)

    plt.figure(figsize=(7, 5))
    plt.plot(setpoints, measured, 'o-', label='Measured')

    # Ideal 1:1 reference line
    lo = min(setpoints.min(), measured.min())
    hi = max(setpoints.max(), measured.max())
    plt.plot([lo, hi], [lo, hi], 'k--', label='Ideal 1:1 (crude linear fit)')

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_accuracy_with_residuals(setpoints, measured, errors,
                                  x_label="Set Value",
                                  y_label="Measured Value",
                                  title="Accuracy Analysis"):
    """
    Accuracy plot with residuals subplot:
    - Top plot: Measured vs. setpoints with 1:1 ideal line
    - Bottom plot: Residuals (errors) vs. setpoints with zero line

    Args:
        setpoints: Array of setpoint values
        measured: Array of measured values
        errors: Array of errors (measured - setpoint)
        x_label: Label for x-axis (setpoints)
        y_label: Label for y-axis (measured values)
        title: Overall plot title
    """
    setpoints = np.array(setpoints)
    measured = np.array(measured)
    errors = np.array(errors)

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

    # Top plot: Accuracy (measured vs setpoint)
    ax1.plot(setpoints, measured, 'o-', label='Measured', color='#1f77b4', markersize=6)

    # Ideal 1:1 reference line
    lo = min(setpoints.min(), measured.min())
    hi = max(setpoints.max(), measured.max())
    ax1.plot([lo, hi], [lo, hi], 'k--', label='Ideal 1:1', linewidth=1.5)

    ax1.set_ylabel(y_label)
    ax1.set_title(title)
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Bottom plot: Residuals
    ax2.plot(setpoints, errors, 'o-', label='Error', color='#ff7f0e', markersize=6)
    ax2.axhline(y=0, color='k', linestyle='--', linewidth=1.5, label='Zero Error')

    # Add error statistics as text
    mean_error = np.mean(errors)
    std_error = np.std(errors)
    max_error = np.max(np.abs(errors))

    stats_text = f'Mean: {mean_error:.6f}\nStd: {std_error:.6f}\nMax: {max_error:.6f}'
    ax2.text(0.02, 0.98, stats_text,
             transform=ax2.transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
             fontsize=9)

    ax2.set_xlabel(x_label)
    ax2.set_ylabel('Error (Measured - Set)')
    ax2.set_title('Residuals')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.show()
    return fig, (ax1, ax2)



def plot_multi_file_data(file_data_list,
    x_var, y_var,
    x_scale=1, y_scale=1,
    title=None, xlabel=None, ylabel=None,
    labeling_mode='none',
    label_config=None,
    plot_style='Line + Scatter',
    figsize=(10, 6),
    marker='o',
    markersize=3,
    show_grid=True,
    grid_alpha=0.3,
    xtick_rotation=0,
    ytick_rotation=0,
    show_legend=True,
    legend_loc='best',
    linewidth=1.5,
    alpha=1.0,
    xtick_max=0):
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
        labeling_mode: 'none', 'filename', 'data', or 'both'
        label_config: Dict with labeling configuration:
                     - For 'filename' mode: {'file_label_idx': int}
                     - For 'data' mode: {'data_label_var': str, 'normalize_colors': bool}
                     - For 'both' mode: {'file_label_idx': int, 'data_label_var': str, 'normalize_colors': bool}
                       (color by data label, line style by file)
                     - 'normalize_colors': If True, maps numeric data values to a gradient colormap
                       (coolwarm: blue=low, red=high). If False, uses discrete colors from palette.
        plot_style: 'Line', 'Scatter', or 'Line + Scatter' (default: 'Line + Scatter')
        figsize: Figure size tuple (width, height)
        marker: Marker style for plot (used when plot_style includes scatter)
        markersize: Size of markers (used when plot_style includes scatter)
        show_grid: Whether to show grid
        grid_alpha: Opacity of grid lines (0.0–1.0, default 0.3)
        xtick_rotation: X-axis tick label rotation in degrees
        ytick_rotation: Y-axis tick label rotation in degrees
        show_legend: Whether to show the legend (only applies when labeling_mode != 'none')
        legend_loc: Matplotlib legend location string (e.g. 'best', 'upper right')
        linewidth: Line width for all plotted series
        alpha: Opacity of all plotted series (0.0–1.0)

    Returns:
        Tuple of (fig, ax) matplotlib objects

    Raises:
        KeyError: If x_var or y_var not found in dataframe
        ValueError: If label configuration is invalid
    """
    if label_config is None:
        label_config = {}

    # Determine plot parameters based on style
    if plot_style == 'Line':
        plot_marker = None
        linestyle = '-'
    elif plot_style == 'Scatter':
        plot_marker = marker
        linestyle = 'None'
    else:  # 'Line + Scatter' or default
        plot_marker = marker
        linestyle = '-'

    # Set up plot
    fig, ax = plt.subplots(figsize=figsize)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if show_grid:
        ax.grid(True, alpha=grid_alpha)

    color_idx = 0

    # Preprocessing for 'data' and 'both' modes: color assignment
    data_value_to_color = {}
    normalize_colors = label_config.get('normalize_colors', False)

    if labeling_mode in ['data', 'both']:
        data_label_var = label_config.get('data_label_var')
        if not data_label_var:
            raise ValueError(f"data_label_var must be specified for '{labeling_mode}' labeling mode")

        # Collect all unique data values across all files
        all_data_values = set()
        for file_data in file_data_list:
            if hasattr(file_data, 'df'):
                df = file_data.df
            else:
                df = file_data[3]

            if data_label_var in df.columns:
                all_data_values.update(df[data_label_var].dropna().unique())

        # Sort data values
        sorted_data_values = sorted(all_data_values)

        if normalize_colors:
            # Use color normalization with a gradient colormap
            try:
                # Convert to numeric values for normalization
                numeric_values = [float(v) for v in sorted_data_values]
                min_val = min(numeric_values)
                max_val = max(numeric_values)

                # Create normalizer and colormap
                normalizer = Normalize(vmin=min_val, vmax=max_val)
                colormap = cm.get_cmap('coolwarm')  # Blue (cold) to Red (hot)

                # Map each data value to a normalized color
                for data_val in sorted_data_values:
                    normalized = normalizer(float(data_val))
                    color_rgba = colormap(normalized)
                    data_value_to_color[data_val] = color_rgba

            except (ValueError, TypeError):
                # If values aren't numeric, fall back to discrete colors
                logger.warning("Data values are not numeric. Using discrete colors instead.")
                normalize_colors = False
                for idx, data_val in enumerate(sorted_data_values):
                    data_value_to_color[data_val] = idx % len(COLORS)
        else:
            # Use discrete colors from palette
            for idx, data_val in enumerate(sorted_data_values):
                data_value_to_color[data_val] = idx % len(COLORS)

    # Iterate through files and plot
    file_idx = 0
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
        x_is_numeric = np.issubdtype(df[x_var].dtype, np.number)

        # Apply labeling strategy
        if labeling_mode == 'filename':
            file_label_idx = label_config.get('file_label_idx', 0)
            try:
                label = file_parts[file_label_idx] if file_label_idx else Path(filename).stem
            except (IndexError, TypeError):
                label = Path(filename).stem
            ax.plot(x_data * x_scale if x_is_numeric else x_data, y_data * y_scale,
                   label=label, color=COLORS[color_idx % len(COLORS)],
                   marker=plot_marker, markersize=markersize, linestyle=linestyle,
                   linewidth=linewidth, alpha=alpha)
            color_idx += 1

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

                # Get color for this data value
                if normalize_colors:
                    color = data_value_to_color.get(label_val)
                else:
                    color_idx_for_value = data_value_to_color.get(label_val, 0)
                    color = COLORS[color_idx_for_value]

                ax.plot(df_tmp[x_var] * x_scale if x_is_numeric else df_tmp[x_var], df_tmp[y_var] * y_scale,
                       label=label, color=color,
                       marker=plot_marker, markersize=markersize, linestyle=linestyle,
                       linewidth=linewidth, alpha=alpha)

        elif labeling_mode == 'both':
            # Label by both filename and data column
            # Color by data label, line style by file
            data_label_var = label_config.get('data_label_var')
            if data_label_var not in df.columns:
                raise KeyError(f"Label column '{data_label_var}' not found in {filename}")

            # Get line style for this file
            file_linestyle = LINE_STYLES[file_idx % len(LINE_STYLES)]

            # Get filename label
            file_label_idx = label_config.get('file_label_idx', 0)
            try:
                file_label = file_parts[file_label_idx] if file_label_idx else Path(filename).stem
            except (IndexError, TypeError):
                file_label = Path(filename).stem

            # Plot each data value with consistent color but file-specific line style
            for label_val in sorted(df[data_label_var].dropna().unique()):
                df_tmp = df[df[data_label_var] == label_val]
                label = f"{file_label} - {data_label_var}={label_val}"

                # Get color for this data value (consistent across files)
                if normalize_colors:
                    color = data_value_to_color.get(label_val)
                else:
                    color_idx_for_value = data_value_to_color.get(label_val, 0)
                    color = COLORS[color_idx_for_value]

                ax.plot(df_tmp[x_var] * x_scale if x_is_numeric else df_tmp[x_var], df_tmp[y_var] * y_scale,
                       label=label,
                       color=color,
                       marker=plot_marker,
                       markersize=markersize,
                       linestyle=file_linestyle,
                       linewidth=linewidth,
                       alpha=alpha)

        else:
            # No label
            ax.plot(x_data * x_scale if x_is_numeric else x_data, y_data * y_scale,
                   color=COLORS[color_idx % len(COLORS)],
                   marker=plot_marker, markersize=markersize, linestyle=linestyle,
                   linewidth=linewidth, alpha=alpha)
            color_idx += 1

        # Increment file index for line style assignment
        file_idx += 1

    # Legend
    if show_legend and labeling_mode in ['filename', 'data', 'both']:
        ax.legend(loc=legend_loc)

    # Tick rotation
    if xtick_max and xtick_max > 0:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=xtick_max))
    if xtick_rotation:
        ax.tick_params(axis='x', rotation=xtick_rotation)
    if ytick_rotation:
        ax.tick_params(axis='y', rotation=ytick_rotation)

    plt.tight_layout()
    plt.show()
    return fig, ax


def plot_fft(channels, title="FFT Analysis"):
    """Plot FFT magnitude vs frequency as stacked subplots, one per channel.

    Args:
        channels: list of (freqs_array, magnitudes_array, label_str) tuples
        title: overall figure title
    """
    n = len(channels)
    if n == 0:
        return
    fig, axes = plt.subplots(n, 1, figsize=(10, 3 * n), sharex=False)
    if n == 1:
        axes = [axes]
    for i, (ax, (freqs, mag, label)) in enumerate(zip(axes, channels)):
        ax.plot(freqs, mag, color=COLORS[i % len(COLORS)], linewidth=1.0)
        ax.set_ylabel(f"|{label}|")
        ax.set_xlabel("Frequency (Hz)")
        ax.grid(True, alpha=0.3)
    if title:
        fig.suptitle(title)
    plt.tight_layout()
    plt.show()


def plot_freq_response(b, a, cutoff, fs):
    # Plot the frequency response.
    w, h = filter_analysis.freq_response(b, a, fs=fs)
    plt.subplot(2, 1, 1)
    plt.plot(w, np.abs(h), 'b')
    plt.plot(cutoff, 0.5 * np.sqrt(2), 'ko')
    plt.axvline(cutoff, color='k')
    plt.xlim(0, 0.5 * fs)
    plt.title("Lowpass Filter Frequency Response")
    plt.xlabel('Frequency [Hz]')
    plt.grid()




###################################
### PLOTLY LIVE PLOTTING    #######
###################################

def export_recorded_data_html(recorded_data: list, x_key: str, channels: list, title: str, html_path: str):
    """Export a list-of-dict recording session as a self-contained Plotly HTML file.

    Args:
        recorded_data: List of row dicts (same format written to CSV during recording).
        x_key: Column name to use as x-axis (e.g. 'Time' or a stimulus column).
        channels: List of column names to plot as separate traces.
        title: Plot title.
        html_path: Full output path for the .html file.
    """
    x_vals = [row.get(x_key) for row in recorded_data]
    fig = go.Figure()
    for ch in channels:
        y_raw = [row.get(ch) for row in recorded_data]
        y_vals = []
        for v in y_raw:
            try:
                y_vals.append(None if v is None else float(v))
            except (ValueError, TypeError):
                y_vals.append(None)
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, name=ch, mode='lines'))
    fig.update_layout(title=title, xaxis_title=x_key)
    fig.write_html(html_path)


def update_live_plot_state(state, data_bus, x_key, channels, buffer_size, x_label):
    """Update the shared state dict for a running live plot.

    This allows reconfiguring channels, x-axis, and buffers between
    recording sessions without restarting the Dash server.
    """
    state['x_key'] = x_key
    state['x_label'] = x_label
    state['channels'] = list(channels)
    state['data_bus'] = data_bus
    state['time_buf'] = deque(maxlen=buffer_size)
    state['bufs'] = {ch: deque(maxlen=buffer_size) for ch in channels}
    state['buffer_size'] = buffer_size


def start_live_plot(
        data_bus: Queue,
        x_key: str,
        channels: Sequence[str],
        buffer_size=3000,
        refresh_ms=200,
        x_label: str = "Time",
        title="Live Plot",
        host="127.0.0.1",
        port=8050,
        debug=False,
        state: dict = None,
        row_height: int = 300,
):
    # Initialize shared state dict (read by callback on every tick,
    # can be mutated from outside via update_live_plot_state())
    if state is None:
        state = {}
    update_live_plot_state(state, data_bus, x_key, channels, buffer_size, x_label)

    # Helper to drain samples from the bus into the current buffers
    def _ingest_from_bus():
        bus = state.get('data_bus')
        if bus is None:
            return
        cur_x_key = state['x_key']
        cur_channels = state['channels']
        cur_bufs = state['bufs']
        cur_time_buf = state['time_buf']

        while True:
            try:
                pkt = bus.get_nowait()
            except Empty:
                break
            samples = [pkt] if isinstance(pkt, Mapping) else [s for s in pkt if isinstance(s, Mapping)]
            for sample in samples:
                t = sample.get(cur_x_key)
                if t is None:
                    continue
                cur_time_buf.append(t)
                for ch in cur_channels:
                    buf = cur_bufs.get(ch)
                    if buf is not None:
                        v = sample.get(ch)
                        try:
                            buf.append(None if v is None else float(v))
                        except (ValueError, TypeError):
                            buf.append(None)


    # dash app definition
    app = Dash(__name__)
    app.title = title

    # NOTE: Other histogram display options to consider:
    #   - Side-by-side: make_subplots(rows=n_ch, cols=2) for time series + histogram
    #   - Separate tab: Add dcc.Tabs with separate graphs
    #   - Both views: Show histogram below time series in additional subplots
    app.layout = html.Div([
            html.H2(title),
            html.Div([
                dcc.RadioItems(
                    id="plot-mode",
                    options=[
                        {"label": "Time Series", "value": "timeseries"},
                        {"label": "Histogram", "value": "histogram"}
                    ],
                    value="timeseries",
                    inline=True,
                    style={"display": "inline-block", "marginRight": "20px"}
                ),
                html.Button("Clear Data", id="btn-clear", n_clicks=0,
                            style={"display": "inline-block"}),
                html.Button("Export HTML", id="btn-export-html", n_clicks=0,
                            style={"display": "inline-block", "marginLeft": "10px"}),
            ], style={"marginBottom": "10px"}),
            dcc.Graph(id="graph"),
            dcc.Interval(id="tick", interval=refresh_ms, n_intervals=0),
            dcc.Download(id="download-html"),
        ]
    )

    @app.callback(
        Output("graph", "figure"),
        Input("tick", "n_intervals"),
        Input("plot-mode", "value"),
        Input("btn-clear", "n_clicks"),
    )
    def update_graph(_, plot_mode, n_clicks):
        # Snapshot current state (may be updated between ticks)
        cur_channels = state['channels']
        cur_bufs = state['bufs']
        cur_time_buf = state['time_buf']
        cur_x_label = state.get('x_label', x_label)

        # Handle clear button via Dash callback context
        from dash import ctx
        if ctx.triggered_id == "btn-clear":
            cur_time_buf.clear()
            for ch in cur_channels:
                buf = cur_bufs.get(ch)
                if buf is not None:
                    buf.clear()

        _ingest_from_bus()

        n_ch = len(cur_channels)
        share_x = (plot_mode != "histogram")

        if not cur_time_buf or n_ch == 0:
            fig = make_subplots(rows=max(n_ch, 1), cols=1, shared_xaxes=share_x)
            fig.update_layout(template="plotly_white")
            return fig

        fig = make_subplots(
            rows=n_ch, cols=1,
            shared_xaxes=share_x,
            vertical_spacing=0.08,
        )

        if plot_mode == "histogram":
            # Histogram mode: each subplot has its own x-axis (independent ranges)
            for i, ch in enumerate(cur_channels):
                buf = cur_bufs.get(ch)
                fig.add_trace(
                    go.Histogram(
                        x=list(buf) if buf else [],
                        nbinsx=50,
                        name=ch,
                        marker=dict(color=COLORS[i % len(COLORS)]),
                    ),
                    row=i + 1, col=1
                )
                fig.update_yaxes(title_text="Count", row=i + 1, col=1)
                fig.update_xaxes(title_text=ch, row=i + 1, col=1)
        else:
            # Time series mode: shared x-axis, show data over time
            x = list(cur_time_buf)
            for i, ch in enumerate(cur_channels):
                buf = cur_bufs.get(ch)
                buf_list = list(buf) if buf else []
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=buf_list,
                        mode="lines",
                        name=ch,
                        line=dict(color=COLORS[i % len(COLORS)], width=2),
                    ),
                    row=i + 1, col=1
                )
                valid = [v for v in buf_list if v is not None]
                if valid:
                    ymin, ymax = min(valid), max(valid)
                    span = ymax - ymin
                    pad = span * 0.1 if span > 0 else abs(ymax) * 0.05 or 0.001
                    fig.update_yaxes(title_text=ch, range=[ymin - pad, ymax + pad], row=i + 1, col=1)
                else:
                    fig.update_yaxes(title_text=ch, row=i + 1, col=1)

            # only label the bottom x-axis
            fig.update_xaxes(title_text=cur_x_label, row=n_ch, col=1)

        fig.update_layout(
            template="plotly_white",
            margin=dict(l=60, r=40, t=35, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=row_height * n_ch,
        )
        return fig


    @app.callback(
        Output("download-html", "data"),
        Input("btn-export-html", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_html(_):
        cur_channels = state['channels']
        cur_bufs = state['bufs']
        cur_time_buf = state['time_buf']
        cur_x_label = state.get('x_label', x_label)

        if not cur_time_buf or not cur_channels:
            return None

        x = list(cur_time_buf)
        n_ch = len(cur_channels)
        fig = make_subplots(rows=n_ch, cols=1, shared_xaxes=True, vertical_spacing=0.08)
        for i, ch in enumerate(cur_channels):
            buf = cur_bufs.get(ch)
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=list(buf) if buf else [],
                    mode="lines",
                    name=ch,
                    line=dict(color=COLORS[i % len(COLORS)], width=2),
                ),
                row=i + 1, col=1,
            )
            fig.update_yaxes(title_text=ch, row=i + 1, col=1)
        fig.update_xaxes(title_text=cur_x_label, row=n_ch, col=1)
        fig.update_layout(
            template="plotly_white",
            margin=dict(l=60, r=40, t=35, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=row_height * n_ch,
        )

        filename = f"live_export_{_dt.now().strftime('%Y%m%d_%H%M%S')}.html"
        return dcc.send_string(fig.to_html(full_html=True, include_plotlyjs=True), filename=filename)

    # auto-open browser after a short delay (server needs to be up first)
    url = f"http://{host}:{port}"
    threading.Timer(1.0, webbrowser.open, args=[url]).start()

    # start server (blocking)
    app.run(host=host,
            port=port,
            debug=debug,
            use_reloader=False,
            dev_tools_silence_routes_logging=True  # this hides very noisy printout
            )
