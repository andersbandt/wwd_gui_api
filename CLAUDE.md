# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project provides a GUI-based control system for interfacing with embedded targets and test equipment. Built with Tkinter, it supports control of debug probes, serial ports, power supplies, multimeters, oscilloscopes, and other test/measurement equipment.

The application is called "WWD GUI API" and provides a tabbed interface for different control functions.

## Running the Application

### Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

**Important**: You need to install system packages separately:
- **Tkinter**: `sudo apt-get install python3-tk` (Linux)
- **VISA Backend**: Configure PyVISA backend following [official instructions](https://pyvisa.readthedocs.io/en/latest/introduction/configuring.html)

### Running

Run without auto-connect (default):
```bash
python main.py
```

Run with auto-connect enabled (connects to previously used ports):
```bash
python main.py -a
```

Force compact mode (overrides screen size detection):
```bash
python main.py -c
```

CLI arguments:
- `-a` / `--auto-connect` — Enable auto-connect mode (default: off)
- `-c` / `--compact` — Force compact mode

## Architecture

### Entry Point and Flow

1. **main.py** — Entry point that parses CLI arguments and calls `gui_driver.main()`
2. **gui/gui_driver.py** — Creates the Tkinter window and `MainApplication` instance
3. **MainApplication** class extends `ThemedApp` and creates the notebook with 10 tabs
4. Each tab is a separate module (`guiTab_1` through `guiTab_10`)

### ClassController Pattern

**class_controller.py** provides a central controller that holds references to all connected equipment:
- `ser` — Serial connection
- `dmm` — Digital multimeter
- `ps` — Power supply
- `relay` — USB relay controller
- `fg` — Function generator
- `osc` — Oscilloscope

Additional responsibilities:
- `recording` flag — prevents `gui_refresh` during active recording
- `ports_used` / `set_used_port()` — persists last-used port per device to `config/ports_used.xml`
- `set_used_model()` / `get_used_model()` — persists equipment model selection to XML attributes
- `active_connections` / `add_active_connection()` / `is_port_active()` — runtime port conflict detection

This controller is passed to all tabs, allowing them to share equipment instances.

### GUI Architecture

**gui/gui_class.py** contains the themed GUI component classes:

- `ThemedApp` — Base application class that loads theme from a JSON file (darcula or light)
- `ThemedFrame` — Base frame class with theming support
- `Prompt` — Console output widget used across tabs
- `ColorCircle` — Status indicator widget (green/red/yellow circles)
- `ConnFrame` / `SerialConnFrame` / `AutoConnFrame` — Connection management frames with status indicators
- `StoppableThread` — Threading utility for background operations

**gui/gui_helper.py** — GUI utility functions.

The theming system supports "compact" mode for smaller screens, which scales down padding and button sizes. Theme is selected in `config/master.ini` under `[THEME]`.

### Services Layer (Scaffolding — Not Yet Wired In)

**services/** contains per-equipment service classes that encapsulate the connect/disconnect lifecycle and business logic, separating it from GUI code:

- `equipment_service.py` — `EquipmentService` base class with template method `connect()`, plus `ConnectionResult` dataclass
- `dmm_service.py` — `DMMService`
- `ps_service.py` — `PSService` (includes `safe_shutdown()`)
- `fg_service.py` — `FGService`
- `osc_service.py` — `OscService`

**Status**: Service classes are created but NOT yet wired into tabs. See `todo.md` for migration plan.

### Equipment Control Layer

**EEequipment/** is a git submodule containing equipment drivers:

- **TestEquipment.py** — Core equipment abstraction layer with:
  - `CommandRegistry` — Loads commands from `config.ini` files in each equipment subdirectory
  - `ConnectionHandler` — Abstract base for connection protocols (Serial, VISA, USB)
  - Base classes for various equipment types

- **equipment_manager.py** — Equipment instantiation and `COMMUNICATION_ERRORS` tuple

- Each supported device has its own subdirectory with:
  - Implementation file (e.g., `SPD3303X.py`, `xdm1041main.py`)
  - `config.ini` with SCPI/command definitions
  - `__init__.py` for module imports

Supported equipment:
- Siglent SPD3303X power supply (PyVISA)
- OWON XDM1041 multimeter (serial)
- Keysight DSOX4104A oscilloscope (PyVISA)
- TI XDS110 debug probe (subprocess/scripts)
- USB relay module (pyusb)
- Fluke 8842A, HP 3478A multimeters
- Agilent 33120A function generator
- HP E3640A power supply
- Arduino (serial)

### Data Logging

**common/logger.py** provides logging functionality:

- `RecordConfig` — Dataclass to configure what gets logged (serial, DMM, PS, FG, OSC)
- `StimulusConfig` — Configures stimulus parameters for automated sweeps
- `setup_recording()` — Creates CSV files with appropriate headers
- `build_headers()` — Dynamically builds CSV headers based on enabled equipment
- Supports both CSV (structured data) and text (raw/timestamped) logging

**common/csv_helper.py** provides CSV file operations.

All log files are written to the `data/` directory with timestamped filenames.

### Common Utilities

**common/** contains shared utilities:

- `serial_api.py` — Port detection and enumeration (Windows/Linux/PyVISA methods)
- `serial_helper.py` — Serial processor and buffered reader
- `plotter.py` — Real-time plotting utilities
- `csv_helper.py` — CSV file operations
- `math_columns.py` — User-defined computed columns using safe expression evaluation (`simpleeval`)
- `path_helper.py` — Centralized path management (`get_data_dir()`, `get_full_data_path()`)
- `subprocessor.py` — Subprocess execution utilities
- `usb_api.py` — USB device enumeration

### Analysis

**analysis/** contains data analysis modules:

- `data_helper.py` — CSV/data manipulation utilities
- `stats_analysis.py` — Statistical analysis
- `afe_analysis.py` — Analog front-end data analysis
- `clock_analysis.py` — Clock/timing measurements
- `temp_analysis.py` — Temperature data analysis
- `time_analysis.py` — Time-series analysis
- `least_squares.py` — Least squares fitting

### IMU Utilities

**imu/** contains accelerometer/gyroscope analysis tools:

- `butter_lowpass.py` — Butterworth low-pass filter
- `imu_analysis.py` — IMU data analysis
- `live_imu_graph.py` — Real-time IMU visualization

### Configuration

**config/** directory contains:
- `master.ini` — Main config with sections: `[THEME]`, `[PATHS]`, `[AUTOCONNECT]`, `[DMM]`, `[USB]`, `[Target]`
- `darcula.json` — Dark theme configuration
- `light.json` — Light theme configuration
- `ports_used.xml` — Tracks last used port and model for each equipment type (auto-generated)
- `graph_presets/*.json` — Saved graph configurations

The autoconnect feature reads `master.ini` `[AUTOCONNECT]` to determine which tabs should auto-connect on startup.

## The 10 Tabs

Each tab is in `gui/guiTab_N_*.py`:

1. **MAIN** (`guiTab_1_mainDashboard.py`, `TabMainDashboard`) — Main dashboard with overview status
2. **DMM Control** (`guiTab_2_DMM.py`, `TabDMM`) — Digital multimeter control and data acquisition
3. **XDS110 JTAG** (`guiTab_3_XDS110.py`, `tabXDS110`) — JTAG debug probe interface
4. **USB COMM** (`guiTab_4_USB.py`, `TabUSB`) — USB serial communication
5. **PS Control** (`guiTab_5_PS.py`, `TabPS`) — Power supply control (voltage/current settings)
6. **FG Control** (`guiTab_6_FG.py`, `TabFG`) — Function generator control (waveform, frequency, duty cycle)
7. **ATE** (`guiTab_7_ATE.py`, `TabATE`) — Automated test equipment sequencing
8. **Logger** (`guiTab_8_LOG.py`, `TabLog`) — Data logging with various modes (timestamp, raw, data, math columns)
9. **GRAPH** (`guiTab_9_GRAPH.py`, `TabGraph`) — Real-time graphing of measurements with preset support
10. **OSC Control** (`guiTab_10_OSC.py`, `TabOSC`) — Oscilloscope control

Each tab has:
- Constructor that receives `(notebook, controller, basefilepath, theme_config, [autoconnect])`
- `gui_refresh(self, mode)` method called when tab becomes visible (skipped during active recording)
- Connection management frames for relevant equipment

## Important Code Patterns

### Port Conflict Management

The `ClassController` tracks active connections at runtime via `active_connections` dict. Before connecting, tabs can call `is_port_active(port)` to check if a port is already in use. Historical port/model preferences are persisted in `ports_used.xml`.

### Theme Scaling

The `scale_theme()` function in `gui_class.py` scales numeric theme values (padding, sizes) when compact mode is enabled. Theme is selected in `config/master.ini` `[THEME]` section (supports `darcula.json` and `light.json`).

### Equipment Command Registry

Instead of hardcoding SCPI commands, the `CommandRegistry` loads them from `config.ini` files:

```python
registry = get_registry()
cmd = registry.format_command("SPD3303X", "commands", "set_voltage", channel=1, voltage=5.0)
```

This keeps equipment-specific commands organized and modifiable without code changes.

### Threading for Background Operations

Many tabs use `StoppableThread` for continuous reading/monitoring. Threads check `stopped()` condition regularly and can be terminated gracefully.

### Math Columns

The Logger tab supports user-defined computed columns via `common/math_columns.py`. Users can define expressions like `Power_W = PS_Vmeas1 * PS_Imeas1` that are evaluated safely using `simpleeval` and appended to each CSV row during recording.

## Git Submodule

**EEequipment/** is a git submodule. When cloning, use:
```bash
git clone --recurse-submodules <repo-url>
```

Or initialize after cloning:
```bash
git submodule update --init
```

## Key Project Files

- **todo.md** — Development task tracker with open issues, refactoring priorities, and architecture improvement plans. This is the primary task/TODO list.
- **scripting.md** — Design notes for a planned scripting/automation system.
- **docs/** — Screenshots and documentation assets.

## Development Notes

- The codebase uses tag comments like `tag:HARDCODE` for hardcoded values that might need refactoring
- TODO comments indicate known issues and planned improvements
- The application performs graceful shutdown, turning off power supplies and opening all relays when closing (shutdown logic is in `gui_driver.py` lines 236-271)
- Serial port detection methods can be changed via dropdown (Auto/Windows/Linux/PyVISA)
- The GUI adjusts to screen size, using compact mode for smaller displays
- A services layer (`services/`) has been scaffolded but not yet integrated — see `todo.md` for migration plan
- Known architectural debt: tabs currently mix view, controller, and business logic; see `todo.md` "GUI / Logic Decoupling" section for details
