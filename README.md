# WWD GUI API


> **Free, open-source lab automation and test equipment control for engineers who can't afford LabVIEW**

A Python-based GUI application for controlling test equipment, automating data collection, and analyzing measurements. Built for embedded systems engineers, electronics hobbyists, and anyone who needs to automate their lab without spending thousands on commercial software.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/yourusername/wwd_gui_api)

---

## Why This Exists

**The Problem:**
- LabVIEW costs $3,000-5,000+ and has a steep learning curve
- MATLAB + toolboxes cost $2,000+ per year
- Python scripts work but are fragmented and lack integration
- You just want to control your power supply and log some data

**The Solution:**
WWD GUI API gives you professional lab automation capabilities for **free**:
- Control multiple instruments simultaneously
- Automated data logging with synchronized timestamps
- Parameter sweep testing (voltage, frequency, duty cycle)
- Real-time plotting and analysis
- Instrument accuracy testing
- Cross-platform (Windows, Linux)

---

## ✨ Key Features

### 🔌 **Multi-Instrument Control**
- **Power Supplies**: Siglent SPD3303X, HP E3640A
- **Digital Multimeters**: OWON XDM1041, Fluke 8842A, HP 3478A
- **Function Generators**: Agilent 33120A
- **Debug Probes**: TI XDS110 JTAG/SWD
- **USB Devices**: Serial ports, relay controllers
- **Extensible**: Easy to add new equipment via plugin architecture

### 📊 **Automated Data Logging**
- Synchronized multi-instrument data collection
- CSV export with configurable headers
- Customizable sampling rates
- Serial data parsing and logging
- Timestamped recordings

### 🔄 **Stimulus Sweep Testing**
- **Single parameter sweeps**: Voltage, frequency, duty cycle
- **Dual parameter sweeps**: Nested loops for multi-variable testing
- Linear and logarithmic sweep modes
- Configurable settling times
- Automatic data collection at each step

### 📈 **Data Analysis & Visualization**
- Real-time plotting from CSV files
- Multiple labeling modes (filename, data column, none)
- Scale factors with scientific notation support (1e-3, etc.)
- **Preset system**: Save/load graph configurations
- Multi-file overlay plotting

### 🔧 **ATE (Automated Test Equipment)**
- **Instrument accuracy testing**: Sweep PS and measure with DMM
- Statistical analysis (mean error, std dev, max error, % FS)
- Benchmark tools for equipment performance
- Generic command/query interface

### 🎨 **Professional UI**
- Dark theme with customizable colors
- Auto-connect to previously used ports
- Status indicators for all connections
- Compact mode for smaller displays
- Cross-platform native look

---

## 📸 Screenshots

### Main Dashboard
*Main dashboard has USB relay (4 buttons, first one is green)*

*There is also an Arduino control thing I had (the buttons frame)*

![Main dash screenshot](/docs/tab_maindash_ss.png)


### DMM Tab
*Basic control of a DMM here*
*The power supply and function generator tabs look similar*

![DMM screenshot](/docs/tab_dmm_ss.png)


### Logger Tab
*Synchronized data collection with stimulus sweeps*
*Also can do live plotting, plot after sweep*

![Logger screenshot](/docs/tab_log_ss.png)


### Graphing Tab
*Multi-file plotting with presets*

![Graph screenshot](/docs/tab_graph_ss.png)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Tkinter (usually included with Python)
- PyVISA backend (NI-VISA or pyvisa-py)

### Installation

```bash
# Clone the repository
git clone --recurse-submodules https://github.com/yourusername/wwd_gui_api.git
cd wwd_gui_api

# Install dependencies
pip install -r requirements.txt

# Install system packages (Linux)
sudo apt-get install python3-tk

# Run the application
python main.py
```

### First Run

1. **Connect your equipment** via USB/Serial/VISA
2. **Launch the application**: `python main.py`
3. **Select a tab** (Logger, DMM Control, PS Control, etc.)
4. **Connect to equipment** using the connection panel
5. **Start logging or controlling**

---

## 📚 Usage Examples

### Example 1: Log DMM Data
```python
# In the Logger tab:
1. Check "Use DMM" checkbox
2. Click "Refresh" to find your DMM
3. Connect to the DMM
4. Set recording speed (e.g., 1 second)
5. Click "Start Record"

# Data saved to: data/DMM_YYYYMMDD_HHMMSS.csv
```

### Example 2: Power Supply Voltage Sweep
```python
# In the Logger tab:
1. Check "Use PS" and "Use DMM" checkboxes
2. Connect to both instruments
3. Enable "Use Stimulus" checkbox
4. Configure sweep:
   - Stimulus Type: PS Voltage
   - Start: 0V, Stop: 5V, Steps: 11
   - Settling Time: 0.5s
5. Click "Start Record"

# Automatically sweeps voltage and logs PS/DMM readings
# Data saved with columns: Time, PS_Voltage, PS_Vmeas1, DMM_Meas1, Stimulus_Step
```

### Example 3: Instrument Accuracy Test
```python
# In the ATE tab:
1. Connect PS and DMM
2. Go to "Instrument Accuracy Testing" section
3. Set sweep parameters:
   - Start: 0V, Stop: 10V, Steps: 21
   - Settling: 0.5s, Channel: 1
4. Click "Run Accuracy Test"

# Results show:
# - Mean error, Std deviation, Max error
# - Percent of full scale errors
# - Detailed measurement table
```

### Example 4: Plot Data with Presets
```python
# In the Graph tab:
1. Set data directory (or use default data/)
2. Configure plot parameters:
   - Title, X-label, Y-label
   - X-variable, Y-variable (CSV column names)
   - X-scale, Y-scale (e.g., 1e-3 for mV to V)
3. Click "Save" to save as preset
4. Select files to plot
5. Click "Graph Selected Files"

# Presets saved to: config/graph_presets/*.json
```

---

## 🔌 Supported Equipment

### Power Supplies
- ✅ Siglent SPD3303X (PyVISA)
- ✅ HP E3640A (PyVISA)

### Digital Multimeters
- ✅ OWON XDM1041 (Serial)
- ✅ Fluke 8842A (PyVISA)
- ✅ HP 3478A (PyVISA)

### Function Generators
- ✅ Agilent 33120A (PyVISA)

### Debug Probes
- ✅ TI XDS110 JTAG/SWD

### USB Devices
- ✅ Generic serial ports (pyserial)
- ✅ USB relay controllers (pyusb)

### Want to add your equipment?
Check the equipment submodule README or submit an issue!

---

## 🏗️ Architecture

```
wwd_gui_api/
├── main.py                 # Entry point
├── gui/
│   ├── gui_driver.py       # Main window and notebook
│   ├── gui_class.py        # Themed UI components
│   ├── guiTab_1_mainDashboard.py
│   ├── guiTab_2_LOG.py     # Logger with stimulus sweeps
│   ├── guiTab_3_DMM.py     # DMM control
│   ├── guiTab_4_XDS110.py  # JTAG debug
│   ├── guiTab_5_USB.py     # USB serial
│   ├── guiTab_6_PS.py      # Power supply
│   ├── guiTab_7_ATE.py     # Automated testing
│   ├── guiTab_8_GRAPH.py   # Data plotting
│   └── guiTab_9_FG.py      # Function generator
├── common/
│   ├── logger.py           # Data logging and stimulus control
│   ├── plotter.py          # Plotting utilities
│   ├── serial_api.py       # Serial port detection
│   └── path_helper.py      # Cross-platform path management
├── EEequipment/            # Equipment drivers (git submodule)
│   ├── TestEquipment.py    # Base classes
│   ├── SPD3303X/           # Siglent PS driver
│   ├── xdm1041/            # OWON DMM driver
│   └── ...
├── config/
│   ├── darcula.json        # UI theme
│   ├── master.ini          # Autoconnect settings
│   └── graph_presets/      # Saved graph configurations
└── data/                   # Logged data files
```

### Key Design Patterns

**ClassController Pattern**: Central controller manages all equipment references and shared state.

**Named Tuples**: File data uses named tuples for clarity (`file.filename`, `file.df` vs. `file[0]`, `file[3]`).

**Command Registry**: Equipment commands loaded from `config.ini` files for flexibility.

**Stimulus Generator**: Reusable sweep logic across logger and ATE tabs.

**Themed Components**: Consistent UI with theme JSON and base classes.

---

## 🗺️ Roadmap

### v1.0 - Core Stability (Current)
- [x] Multi-instrument control
- [x] Synchronized data logging
- [x] Stimulus sweep testing (single and dual)
- [x] Graph presets with named tuples
- [x] Instrument accuracy testing
- [x] Cross-platform support

### v1.1 - Equipment Expansion
- [ ] Rigol equipment support (DS1054Z oscilloscope, DP832 PS)
- [ ] Keysight/Agilent SCPI instruments
- [ ] Fluke 8846A 6.5-digit DMM
- [ ] BK Precision equipment
- [ ] Plugin architecture for community drivers

### v1.2 - Analysis Tools
- [ ] FFT analysis tools
- [ ] Statistical analysis dashboard
- [ ] Automated report generation (PDF)
- [ ] Data export formats (Excel, JSON, HDF5)

### v1.3 - Advanced Features
- [ ] Scripting/macro system
- [ ] Remote control via API
- [ ] Multi-user collaboration
- [ ] Cloud data storage (optional)

### v2.0 - Professional Features
- [ ] Oscilloscope integration
- [ ] Network analyzer support
- [ ] Automated calibration procedures
- [ ] Test sequence builder (LabVIEW-style)

---

## 🤝 Contributing

We welcome contributions! Whether you're:
- 🔧 Adding support for new equipment
- 🐛 Fixing bugs
- 📝 Improving documentation
- 💡 Suggesting features

### Easy Ways to Contribute
1. **Add equipment drivers** - Have a piece of test equipment? Add support for it!
2. **Test on different platforms** - Help verify cross-platform compatibility
3. **Write tutorials** - Share your workflows and use cases
4. **Report bugs** - Found something broken? Let us know!

---

## 💬 Community & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/wwd_gui_api/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/wwd_gui_api/discussions)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR**: You can use this software for any purpose, including commercial, as long as you include the license and copyright notice.

---

## 🙏 Acknowledgments

- **Equipment Drivers**: Built on PyVISA and pyserial ecosystems
- **UI Framework**: Tkinter for cross-platform GUI
- **Data Analysis**: NumPy, Pandas, Matplotlib
- **Inspiration**: The need for affordable lab automation tools

---

## 🌟 Star History

If you find this project useful, please consider giving it a star on GitHub! It helps others discover the project.

---

## 🎓 For Educators

This software is **free for educational use**. We encourage:
- Using it in lab courses
- Teaching automation concepts
- Student projects and research

---

## 🔬 Research & Publications

If you use this software in your research, please cite:

```bibtex
@software{wwd_gui_api,
  author = {Anders Bandt},
  title = {WWD GUI API: Open-Source Lab Automation Software},
  year = {2025},
  url = {https://github.com/yourusername/wwd_gui_api}
}
```

---

## 💡 Philosophy

> "Lab automation shouldn't cost more than the equipment you're automating."

We believe:
- **Open source** makes better software through community collaboration
- **Free tools** democratize access to professional capabilities
- **Python** is the right language for scientific instrumentation
- **Simplicity** beats feature bloat

---

## 🚧 Project Status

**Active Development** - This project is actively maintained and welcoming contributions.

---

**Made with ❤️ by engineers, for engineers**

*Because everyone deserves professional lab automation tools, not just those who can afford LabVIEW.*
