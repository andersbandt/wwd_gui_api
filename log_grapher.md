# Adding Graphing Features to Logging Sweep

## Overview

This document outlines the implementation plan for adding graphing capabilities to the Logger tab's stimulus sweep functionality, with the goal of reusing the graph configuration UI from the Graph tab.

## Current Architecture

### Logger Tab (guiTab_8_LOG.py)
- Handles stimulus sweeps (single and dual parameter)
- Logs data to CSV files
- Has frames: `fr_status`, `fr_setup`, `fr_stimulus`, `fr_analysis` (unused)

### Graph Tab (guiTab_9_GRAPH.py)
- Has `fr_setup` frame with comprehensive graph parameters:
  - Title, x-label, y-label text boxes
  - X/Y variable and scale inputs
  - Filename filter/labeling checkboxes
  - Preset save/load functionality
- Uses `plotter.plot_multi_file_data()` for plotting

### Plotter Module (common/plotter.py)
- `plot_multi_file_data()` - Main plotting function for multiple files
- `LivePlot` class - Real-time plotting capability
- `plot_3d()` - Stub for 3D plotting (not tested)

## Implementation Plan

### 1. Extract Graph Setup into Reusable Component

**File**: `gui/gui_class.py`

Create a new class `GraphSetupFrame(ThemedFrame)` that encapsulates all graph parameter widgets currently in `TabGraph.init_fr_setup()` (lines 87-173 of guiTab_9_GRAPH.py).

**Components to Extract**:
- Title, x-label, y-label text boxes
- X/Y variable and scale inputs (spinboxes)
- Filename filter checkbox and text field
- Filename labeling checkbox and index input
- Data (header) labeling checkbox and column name input
- Preset save/load UI and functionality

**Public Interface**:
```python
class GraphSetupFrame(ThemedFrame):
    def __init__(self, master, theme_config, basefilepath):
        # Initialize all widgets

    def get_graph_config(self):
        """Returns dict with all graph parameters"""
        return {
            "title": str,
            "x_label": str,
            "y_label": str,
            "x_scale": float,
            "y_scale": float,
            "x_var": str,
            "y_var": str,
            "labeling_mode": str,  # 'none', 'filename', 'data'
            "label_config": dict,
            "use_file_regex": bool,
            "file_filter": str
        }

    def set_graph_config(self, config):
        """Populates widgets from a config dict"""

    def load_preset(self, preset_name):
        """Load preset by name"""

    def save_preset(self, preset_name):
        """Save current config as preset"""

    def auto_configure_sweep_plot(self, stimulus_config, record_config):
        """Set intelligent defaults for sweep plotting"""
```

### 2. Add Graph Configuration to Logger Tab

**File**: `guiTab_8_LOG.py`

Add graph configuration UI to the Logger tab:

```python
class TabLog(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config):
        # ... existing init code ...

        # Add graph configuration frame
        self.fr_graph_config = guic.GraphSetupFrame(
            self.fr_top_container,
            theme_config,
            basefilepath
        )

        # Add checkbox to enable auto-plotting
        self.var_plot_after_sweep = tk.IntVar()

    def init_fr_analysis(self):
        """Initialize the analysis frame (currently unused)"""
        ttk.Label(self.fr_analysis,
                  text="Post-Sweep Analysis",
                  style="TPinkLabel.TLabel").grid(row=0, column=0, pady=5)

        # Checkbox to enable plotting after sweep
        ttk.Checkbutton(self.fr_analysis,
                        text="Plot After Sweep",
                        variable=self.var_plot_after_sweep,
                        onvalue=1,
                        offvalue=0).grid(row=1, column=0, padx=5, pady=5)

        # Button to manually configure graph settings
        btn_graph_config = tk.Button(self.fr_analysis,
                                      text="Configure Plot",
                                      command=self.show_graph_config,
                                      bg=self.theme_config["dark_3"],
                                      fg="white",
                                      height=self.theme_config["size"]["h_button"],
                                      width=self.theme_config["size"]["w_button"])
        btn_graph_config.grid(row=2, column=0, padx=5, pady=5)
```

**Layout Update**:
```python
# Add fr_analysis to layout (in __init__)
self.fr_analysis.pack(in_=bottom_row, side="left", padx=(0, 15))
```

### 3. Integrate Plotting into Sweep Completion

**File**: `guiTab_8_LOG.py`

Modify `thread_record_stimulus()` method (around line 706-728):

```python
def thread_record_stimulus(self):
    """Stimulus-based recording (sweep mode)"""
    self.prompt.print(f"Starting stimulus sweep with {len(self.stimulus_generator)} steps")

    try:
        if self.is_dual_stimulus:
            self._thread_record_dual_stimulus()
        else:
            self._thread_record_single_stimulus()

        # Sweep complete
        if self.record_status:
            self.prompt.print("Stimulus sweep completed!")

            # NEW: Auto-plot if enabled
            if self.var_plot_after_sweep.get():
                self.plot_sweep_results()

            self.record_status = False
            return

    except Exception as e:
        self.prompt.print(f"Error during stimulus sweep: {e}")
        guih.alert_user("Error during stimulus sweep", str(e), "error")
        self.record_status = False
        raise e
```

### 4. Add Plot Method to Logger Tab

**File**: `guiTab_8_LOG.py`

Add new methods for plotting sweep results:

```python
def show_graph_config(self):
    """Show/hide graph configuration panel"""
    # Toggle visibility of graph config frame
    # Could use a popup window or expand in current layout
    pass

def auto_configure_sweep_plot(self):
    """Auto-configure graph settings based on sweep parameters"""
    config = {}

    # Set X variable based on stimulus type
    if self.is_dual_stimulus:
        # For dual stimulus, might want outer loop as X
        outer_type = self.stimulus_config.outer_loop.stimulus_type
        config["x_var"] = logger.get_stimulus_column_name(outer_type)

        # Inner loop could be used for labeling
        inner_type = self.stimulus_config.inner_loop.stimulus_type
        config["labeling_mode"] = "data"
        config["label_config"] = {
            "data_label_var": logger.get_stimulus_column_name(inner_type)
        }
    else:
        # Single stimulus
        stim_type = self.stimulus_config.stimulus_type
        config["x_var"] = logger.get_stimulus_column_name(stim_type)

    # Set Y variable based on primary measurement instrument
    if self.record_config.use_dmm:
        config["y_var"] = "DMM_Meas1"
    elif self.record_config.use_ps:
        config["y_var"] = "PS_Vmeas1"
    elif self.record_config.use_fg:
        config["y_var"] = "FG_Freq"
    elif self.record_config.use_ser:
        config["y_var"] = "SerialData"

    # Set labels
    if self.is_dual_stimulus:
        outer_name = logger.get_stimulus_column_name(
            self.stimulus_config.outer_loop.stimulus_type
        )
        inner_name = logger.get_stimulus_column_name(
            self.stimulus_config.inner_loop.stimulus_type
        )
        config["title"] = f"{outer_name} vs {inner_name} Sweep"
        config["x_label"] = outer_name
    else:
        stim_name = logger.get_stimulus_column_name(
            self.stimulus_config.stimulus_type
        )
        config["title"] = f"{stim_name} Sweep"
        config["x_label"] = stim_name

    config["y_label"] = config.get("y_var", "Measurement")

    # Set scales (default to 1)
    config["x_scale"] = 1.0
    config["y_scale"] = 1.0

    return config

def plot_sweep_results(self):
    """Plot the results from the just-completed sweep"""
    try:
        # Load the CSV file that was just created
        csv_path = os.path.join(self.data_dir, self.recName)
        df = pd.read_csv(csv_path)

        # Create FileData namedtuple
        from collections import namedtuple
        FileData = namedtuple('FileData', ['filename', 'filepath', 'parts', 'df'])

        file_data = FileData(
            filename=self.recName,
            filepath=csv_path,
            parts=self.recName.split('_'),
            df=df
        )

        # Get graph configuration
        # Option 1: Use auto-configured settings
        if not hasattr(self, 'fr_graph_config') or self.fr_graph_config is None:
            graph_config = self.auto_configure_sweep_plot()
        else:
            # Option 2: Use user-configured settings
            graph_config = self.fr_graph_config.get_graph_config()

        # Call plotting function
        self.prompt.print("Generating plot...")
        plotter.plot_multi_file_data(
            file_data_list=[file_data],
            x_var=graph_config["x_var"],
            y_var=graph_config["y_var"],
            x_scale=graph_config.get("x_scale", 1.0),
            y_scale=graph_config.get("y_scale", 1.0),
            title=graph_config.get("title", "Sweep Results"),
            xlabel=graph_config.get("x_label", "Stimulus"),
            ylabel=graph_config.get("y_label", "Measurement"),
            labeling_mode=graph_config.get("labeling_mode", "none"),
            label_config=graph_config.get("label_config", {}),
            figsize=(10, 6),
            marker='o',
            markersize=5,
            show_grid=True
        )
        self.prompt.print("Plot generated successfully!")

    except FileNotFoundError:
        error_msg = f"Could not find CSV file: {self.recName}"
        self.prompt.print(error_msg, "error")
        guih.alert_user("File Not Found", error_msg, "error")
    except KeyError as e:
        error_msg = f"Column not found in data: {str(e)}"
        self.prompt.print(error_msg, "error")
        guih.alert_user("Data Error", error_msg, "error")
    except Exception as e:
        error_msg = f"Error plotting results: {str(e)}"
        self.prompt.print(error_msg, "error")
        guih.alert_user("Plotting Error", error_msg, "error")
```

### 5. Refactor Graph Tab to Use GraphSetupFrame

**File**: `guiTab_9_GRAPH.py`

Update the Graph tab to use the extracted component:

```python
class TabGraph(guic.ThemedFrame):
    def __init__(self, master, class_controller, basefilepath, theme_config):
        super().__init__(master, theme_config)
        # ... existing init code ...

        # Replace inline fr_setup with GraphSetupFrame
        self.graph_setup = guic.GraphSetupFrame(
            self,
            theme_config,
            basefilepath
        )

    def init_fr_setup(self):
        # Remove all the widget creation code (lines 88-173)
        # It's now handled by GraphSetupFrame
        pass

    def graph_files(self):
        # Update to use graph_setup.get_graph_config()
        selected_files = self.get_selected_files()

        if not selected_files:
            guih.alert_user("No Files Selected",
                           "Please select one or more files to graph",
                           "warning")
            return False

        # Get configuration from GraphSetupFrame
        config = self.graph_setup.get_graph_config()

        # Call plotting function
        try:
            plotter.plot_multi_file_data(
                file_data_list=selected_files,
                x_var=config["x_var"],
                y_var=config["y_var"],
                x_scale=config["x_scale"],
                y_scale=config["y_scale"],
                title=config["title"],
                xlabel=config["x_label"],
                ylabel=config["y_label"],
                labeling_mode=config["labeling_mode"],
                label_config=config["label_config"],
                figsize=(10, 6),
                marker='o',
                markersize=3,
                show_grid=True
            )
            self.prompt.print("Graph complete!")
            return True
        except Exception as e:
            # ... error handling ...
            pass
```

## Alternative: Real-time Live Plotting

For plotting during the sweep (not just after), you could leverage the existing `LivePlot` class.

**File**: `guiTab_8_LOG.py`

```python
def init_fr_analysis(self):
    # ... existing code ...

    # Add live plotting option
    self.var_live_plot = tk.IntVar()
    ttk.Checkbutton(self.fr_analysis,
                    text="Live Plot During Sweep",
                    variable=self.var_live_plot,
                    onvalue=1,
                    offvalue=0).grid(row=3, column=0, padx=5, pady=5)

def thread_record_stimulus(self):
    # Initialize live plot if enabled
    if self.var_live_plot.get():
        config = self.auto_configure_sweep_plot()
        self.live_plotter = plotter.LivePlot(
            title=config["title"],
            xlabel=config["x_label"],
            ylabel=config["y_label"]
        )

    # ... rest of sweep logic ...

def _thread_record_single_stimulus(self):
    for step_num, stimulus_value in enumerate(self.stimulus_generator, 1):
        # ... existing collection code ...

        # Update live plot
        if self.var_live_plot.get() and hasattr(self, 'live_plotter'):
            self.live_plotter.xs.append(stimulus_value)
            y_value = row.get(self.auto_configure_sweep_plot()["y_var"], 0)
            self.live_plotter.ys.append(y_value)
            # Trigger update
```

## File Structure Summary

```
gui/
  gui_class.py
    + GraphSetupFrame class (new)
      - All graph parameter widgets
      - Preset management
      - get_graph_config() / set_graph_config()

  guiTab_8_LOG.py (Logger Tab)
    + self.fr_graph_config = GraphSetupFrame(...) (optional)
    + self.var_plot_after_sweep checkbox
    + init_fr_analysis() method
    + plot_sweep_results() method
    + auto_configure_sweep_plot() method
    + show_graph_config() method (optional)

  guiTab_9_GRAPH.py (Graph Tab)
    ~ Refactor init_fr_setup() to use GraphSetupFrame
    ~ Update graph_files() to use get_graph_config()
    ~ Remove inline widget creation (lines 88-173)
```

## Benefits

1. **Code Reuse**: Both Logger and Graph tabs use the same `GraphSetupFrame`
2. **Consistency**: Same graph configuration UI across tabs
3. **Workflow Efficiency**: Configure plotting before starting sweep, plot appears immediately after
4. **Flexibility**: Can still use Graph tab for multi-file comparative analysis
5. **Smart Defaults**: Auto-configuration reduces manual setup for common sweep plots
6. **No Context Switching**: Results appear without changing tabs
7. **Preset System**: Save/load graph configurations for repeated experiments

## Future Enhancements

### 3D Plotting for Dual Stimulus
For dual stimulus sweeps (nested loops), implement 3D surface plots or heatmaps:

```python
def plot_dual_stimulus_3d(self):
    """Create 3D surface plot for dual stimulus sweep"""
    # Use the plotter.plot_3d() stub as a starting point
    # X-axis: Outer loop parameter
    # Y-axis: Inner loop parameter
    # Z-axis: Measurement
```

### Export Plot with Data
Add option to save plot image alongside CSV:

```python
def plot_sweep_results(self):
    # ... existing code ...

    # Save figure
    fig_path = csv_path.replace('.csv', '.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    self.prompt.print(f"Plot saved: {fig_path}")
```

### Multiple Y-Axis Plotting
When multiple instruments are recording, plot multiple Y-axes:

```python
# Support plotting DMM and PS voltage on same X-axis with dual Y-axes
```

### Sweep-Specific Presets
Create a separate preset directory for sweep plots vs multi-file plots:

```python
self.sweep_preset_dir = os.path.join(basefilepath, "config", "sweep_presets")
```

## Implementation Notes

- **Import Requirements**: Need to add `import pandas as pd` and `import os` to `guiTab_8_LOG.py`
- **Threading**: Plotting should happen after recording thread completes to avoid thread safety issues
- **Error Handling**: Robust error handling for missing columns, invalid data types
- **Performance**: For very long sweeps (>1000 points), consider decimation for live plotting
- **User Feedback**: Progress indicators during plot generation for large datasets

## Testing Checklist

- [ ] GraphSetupFrame works standalone in Graph tab
- [ ] Logger tab can auto-configure plot settings
- [ ] Plot appears after single stimulus sweep
- [ ] Plot appears after dual stimulus sweep
- [ ] Preset save/load works from Logger tab
- [ ] Manual graph configuration works from Logger tab
- [ ] Error handling for missing/invalid data
- [ ] Live plotting during sweep (if implemented)
- [ ] Graph tab still works with refactored GraphSetupFrame
- [ ] Theme scaling applies correctly to new components
