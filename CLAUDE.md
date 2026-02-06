# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project provides a GUI-based control system for interfacing with embedded targets and test equipment. Built with Tkinter, it supports control of debug probes, serial ports, power supplies, multimeters, and other test/measurement equipment.

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

Run with auto-connect enabled (connects to previously used ports):
```bash
python main.py
```

Run without auto-connect:
```bash
python main.py --disable-auto
```

The application will launch a Tkinter GUI with multiple tabs for different equipment control.

## Architecture

### Entry Point and Flow

1. **main.py** - Entry point that parses CLI arguments and calls `gui_driver.main()`
2. **gui/gui_driver.py** - Creates the Tkinter window and `MainApplication` instance
3. **MainApplication** class extends `ThemedApp` and creates the notebook with 8 tabs
4. Each tab is a separate module (guiTab_1 through guiTab_8)

### ClassController Pattern

**class_controller.py** provides a central controller that holds references to all connected equipment:
- `ser` - Serial connection
- `dmm` - Digital multimeter
- `ps` - Power supply
- `relay` - USB relay controller
- `fg` - Function generator

This controller is passed to all tabs, allowing them to share equipment instances. It also manages the `ports_used.xml` config to remember which ports were used for each device.

### GUI Architecture

**gui/gui_class.py** contains the themed GUI component classes:

- `ThemedApp` - Base application class that loads theme from `config/darcula.json`
- `ThemedFrame` - Base frame class with theming support
- `Prompt` - Console output widget used across tabs
- `ConnFrame` / `SerialConnFrame` / `AutoConnFrame` - Connection management frames with status indicators
- `StoppableThread` - Threading utility for background operations

The theming system supports "compact" mode for smaller screens, which scales down padding and button sizes.

### Equipment Control Layer

**EEequipment/** is a git submodule containing equipment drivers:

- **TestEquipment.py** - Core equipment abstraction layer with:
  - `CommandRegistry` - Loads commands from `config.ini` files in each equipment subdirectory
  - `ConnectionHandler` - Abstract base for connection protocols (Serial, VISA, USB)
  - Base classes for various equipment types

- Each supported device has its own subdirectory with:
  - Implementation file (e.g., `SPD3303X.py`, `xdm1041main.py`)
  - `config.ini` with SCPI/command definitions
  - `__init__.py` for module imports

Supported equipment:
- Siglent SPD3303X power supply (PyVISA)
- OWON XDM1041 multimeter (serial)
- TI XDS110 debug probe (subprocess/scripts)
- USB relay module (pyusb)
- Fluke 8842A, HP 3478A multimeters
- Agilent 33120A function generator
- HP E3640A power supply

### Data Logging

**common/logger.py** provides logging functionality:

- `RecordConfig` - Dataclass to configure what gets logged (serial, DMM, PS)
- `setup_recording()` - Creates CSV files with appropriate headers
- `build_headers()` - Dynamically builds CSV headers based on enabled equipment
- Supports both CSV (structured data) and text (raw/timestamped) logging

**analysis/csv_helper.py** provides CSV file operations.

All log files are written to the `data/` directory with timestamped filenames.

### Serial Communication

**common/** contains serial communication utilities:

- `serial_api.py` - Port detection and enumeration (Windows/Linux/PyVISA methods)
- `SerialReader.py` - Buffered serial reader with logging (extends `SerialGeneral`)
- `SerialGeneral.py` - Base serial connection class
- `plotter.py` - Real-time plotting utilities

### Configuration

**config/** directory contains:
- `master.ini` - Autoconnect settings for each tab (`[AUTOCONNECT]` section)
- `darcula.json` - GUI theme configuration (colors, fonts, sizing)
- `ports_used.xml` - Tracks last used port for each equipment type (auto-generated)
- `*.ini` - Other configuration files

The autoconnect feature reads `master.ini` to determine which tabs should auto-connect on startup.

## The 9 Tabs

Each tab is in `gui/guiTab_N_*.py`:

1. **MAIN** (guiTab_1_mainDashboard) - Main dashboard with overview status
2. **Logger** (guiTab_2_LOG) - Serial logging with various modes (timestamp, raw, data)
3. **DMM Control** (guiTab_3_DMM) - Digital multimeter control and data acquisition
4. **XDS110 JTAG** (guiTab_4_XDS110) - JTAG debug probe interface
5. **USB COMM** (guiTab_5_USB) - USB serial communication
6. **PS Control** (guiTab_6_PS) - Power supply control (voltage/current settings)
7. **ATE** (guiTab_7_ATE) - Automated test equipment sequencing
8. **GRAPH** (guiTab_8_GRAPH) - Real-time graphing of measurements
9. **FG Control** (guiTab_9_FG) - Function generator control (waveform, frequency, duty cycle)

Each tab has:
- Constructor that receives `(notebook, controller, basefilepath, theme_config, [autoconnect])`
- `gui_refresh(self, mode)` method called when tab becomes visible
- Connection management frames for relevant equipment

## Important Code Patterns

### Port Conflict Management

The application tracks which port is used by which tab in `ports_used.xml`. Before connecting, tabs can check if a port is already in use via the ClassController.

### Theme Scaling

The `scale_theme()` function in `gui_class.py` scales numeric theme values (padding, sizes) when compact mode is enabled. Key paths are specified for which values to scale.

### Equipment Command Registry

Instead of hardcoding SCPI commands, the `CommandRegistry` loads them from `config.ini` files:

```python
registry = get_registry()
cmd = registry.format_command("SPD3303X", "commands", "set_voltage", channel=1, voltage=5.0)
```

This keeps equipment-specific commands organized and modifiable without code changes.

### Threading for Background Operations

Many tabs use `StoppableThread` for continuous reading/monitoring. Threads check `stopped()` condition regularly and can be terminated gracefully.

## Git Submodule

**EEequipment/** is a git submodule. When cloning, use:
```bash
git clone --recurse-submodules <repo-url>
```

Or initialize after cloning:
```bash
git submodule update --init
```

## Development Notes

- The codebase uses tag comments like `tag:HARDCODE` for hardcoded values that might need refactoring
- TODO comments indicate known issues and planned improvements
- The application performs graceful shutdown, turning off power supplies and opening all relays when closing
- Serial port detection methods can be changed via dropdown (Auto/Windows/Linux/PyVISA)
- The GUI adjusts to screen size, using compact mode for smaller displays
