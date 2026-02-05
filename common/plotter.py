
# import plotter modules
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib import cm
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Output, Input

# import needed modules
import threading
import webbrowser
from typing import Mapping, Sequence
from collections import deque
from queue import Queue, Empty


# consistent color palette for multi-series / multi-subplot plots
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
          '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# Line styles for distinguishing multiple files in combined labeling mode
LINE_STYLES = ['-', '--', '-.', ':']  # solid, dashed, dash-dot, dotted


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
        plt.xticks(rotation=90)
    if ylabel is not None:
        plt.ylabel(ylabel)
    if title is not None:
        plt.title(title)
    if legend is not None:
        plt.legend(legend)

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
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


def plot_subplots(x_data, channels, xlabel=None, title=None, figsize_per_row=4):
    """
    Stacked subplots with shared x-axis, one subplot per channel.

    Args:
        x_data: Shared x-axis data (array-like)
        channels: List of (y_data, ylabel) tuples for each subplot
        xlabel: Label for the shared x-axis (bottom only)
        title: Overall figure title
        figsize_per_row: Height per subplot row in inches
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
    show_grid=True):
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
        ax.grid(True, alpha=0.3)

    color_idx = 0

    # Preprocessing for 'data' and 'both' modes: color assignment
    data_value_to_color = {}
    colormap = None
    normalizer = None
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
                print("Warning: Data values are not numeric. Using discrete colors instead.")
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

        # Apply labeling strategy
        if labeling_mode == 'filename':
            # Label by filename parts
            # NOTE: Currently uses full filename stem. Future enhancement could add support for:
            #       - Single index: file_label_idx to extract parts[idx]
            #       - Range notation: "3-5" to extract parts[3:5]
            #       - Multiple indices: "0,3,4" to extract selected parts
            #       - Slice notation: "3:" to extract parts[3:]
            try:
                file_label_idx = label_config.get('file_label_idx', 0)
                # Use full filename stem (without .csv extension)
                from pathlib import Path
                label = Path(filename).stem
            except (ValueError, IndexError, TypeError):
                label = filename
            ax.plot(x_data * x_scale, y_data * y_scale,
                   label=label, color=COLORS[color_idx % len(COLORS)],
                   marker=plot_marker, markersize=markersize, linestyle=linestyle)
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

                ax.plot(df_tmp[x_var] * x_scale, df_tmp[y_var] * y_scale,
                       label=label, color=color,
                       marker=plot_marker, markersize=markersize, linestyle=linestyle)

        elif labeling_mode == 'both':
            # Label by both filename and data column
            # Color by data label, line style by file
            data_label_var = label_config.get('data_label_var')
            if data_label_var not in df.columns:
                raise KeyError(f"Label column '{data_label_var}' not found in {filename}")

            # Get line style for this file
            file_linestyle = LINE_STYLES[file_idx % len(LINE_STYLES)]

            # Get filename label
            try:
                file_label_idx = label_config.get('file_label_idx', 0)
                from pathlib import Path
                file_label = Path(filename).stem
            except (ValueError, IndexError, TypeError):
                file_label = filename

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

                ax.plot(df_tmp[x_var] * x_scale, df_tmp[y_var] * y_scale,
                       label=label,
                       color=color,
                       marker=plot_marker,
                       markersize=markersize,
                       linestyle=file_linestyle)

        else:
            # No label
            ax.plot(x_data * x_scale, y_data * y_scale,
                   color=COLORS[color_idx % len(COLORS)],
                   marker=plot_marker, markersize=markersize, linestyle=linestyle)
            color_idx += 1

        # Increment file index for line style assignment
        file_idx += 1

    # Show legend if any labels were added
    if labeling_mode in ['filename', 'data', 'both']:
        ax.legend()

    plt.tight_layout()
    plt.show()
    return fig, ax


###################################
### PLOTLY LIVE PLOTTING    #######
###################################

# TODO: in histogram mode it doesn't make sense for them to share the same x-axis


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
):
    # set up buffers
    time_buf = deque(maxlen=buffer_size)
    bufs = {ch: deque(maxlen=buffer_size) for ch in channels}

    # Helper to append one sample
    def _append_sample(sample: Mapping):
        t = sample.get(x_key)
        if t is None:
            return  # ignore malformed packets
        time_buf.append(t)
        for ch in channels:
            v = sample.get(ch)
            # Append None if missing to create a gap; or repeat last value if preferred
            bufs[ch].append(None if v is None else float(v))

    # Helper to accept either a single sample or a batch (list/tuple)
    def _ingest_from_bus():
        drained = 0
        while True:
            try:
                pkt = data_bus.get_nowait()
            except Empty:
                break
            if isinstance(pkt, (list, tuple)):
                for s in pkt:
                    if isinstance(s, Mapping):
                        _append_sample(s)
            elif isinstance(pkt, Mapping):
                _append_sample(pkt)
            drained += 1
        return drained


    # dash app definition
    app = Dash(__name__)
    app.title = title

    # NOTE: Other histogram display options to consider:
    #   - Side-by-side: make_subplots(rows=n_ch, cols=2) for time series + histogram
    #   - Separate tab: Add dcc.Tabs with separate graphs
    #   - Both views: Show histogram below time series in additional subplots
    app.layout = html.Div([
            html.H2(title),
            dcc.RadioItems(
                id="plot-mode",
                options=[
                    {"label": "Time Series", "value": "timeseries"},
                    {"label": "Histogram", "value": "histogram"}
                ],
                value="timeseries",
                inline=True,
                style={"marginBottom": "10px"}
            ),
            dcc.Graph(id="graph"),
            dcc.Interval(id="tick", interval=refresh_ms, n_intervals=0),
        ]
    )

    @app.callback(
        Output("graph", "figure"),
        Input("tick", "n_intervals"),
        Input("plot-mode", "value")
    )
    def update_graph(_, plot_mode):
        _ingest_from_bus()

        n_ch = len(channels)

        if not time_buf:
            fig = make_subplots(rows=n_ch, cols=1, shared_xaxes=True)
            fig.update_layout(template="plotly_white")
            return fig

        fig = make_subplots(
            rows=n_ch, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
        )

        if plot_mode == "histogram":
            # Histogram mode: show distribution of buffered data
            for i, ch in enumerate(channels):
                fig.add_trace(
                    go.Histogram(
                        x=list(bufs[ch]),
                        nbinsx=50,
                        name=ch,
                        marker=dict(color=COLORS[i % len(COLORS)]),
                    ),
                    row=i + 1, col=1
                )
                fig.update_yaxes(title_text="Count", row=i + 1, col=1)
                fig.update_xaxes(title_text=ch, row=i + 1, col=1)
        else:
            # Time series mode: show data over time
            x = list(time_buf)
            for i, ch in enumerate(channels):
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=list(bufs[ch]),
                        mode="lines",
                        name=ch,
                        line=dict(color=COLORS[i % len(COLORS)], width=2),
                    ),
                    row=i + 1, col=1
                )
                fig.update_yaxes(title_text=ch, row=i + 1, col=1)

            # only label the bottom x-axis
            fig.update_xaxes(title_text=x_label, row=n_ch, col=1)

        fig.update_layout(
            template="plotly_white",
            margin=dict(l=60, r=40, t=35, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=300 * n_ch,
        )
        return fig


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
