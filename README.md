# PyVISA EE Test Equipment Control and Automation

> **Free, open-source lab automation and test equipment control for electrical engineers. Useful for a wide variety of lab tasks.**

A Python-based GUI application for controlling test equipment, automating data collection, and analyzing measurements. 

Built for embedded systems engineers, electronics hobbyists, and anyone who needs to automate their lab setup.
Being open-source, you can tweak it or add any integrations/hooks your heart desires!

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/yourusername/wwd_gui_api)

---

## Why This Exists

**The Problem:**
I originally designed this application to assist in debugging an embedded wearable device I was designing. 
It was such an early-prototype that I was doing things like power-cycling, reflashing, switching between USB/power supply power, taking current measurements quite often.

When I do a repeated task over and over, my brain screams the word "automation" at me. I also know that I will continue to use lab bench equipment for a long while yet after that specific project, so wanted to invest some time into developing a custom solution for myself.



I wanted a single application where I could easily do all my lab tasks. Python scripts worked but are fragmented and lack integration, they also quickly become project specific. 
I have grown to despise GUIs and prefer the command line for many tasks, but for something simple like toggling a power supply between ON/OFF simple buttons make sense.


**The Solution:**
- Control multiple instruments simultaneously
- Automated data logging with synchronized timestamps
- Parameter sweep testing (voltage, frequency, duty cycle)
- Real-time plotting and analysis
- Instrument accuracy testing
- Open-source so you can set up hooks like turn on power supply before flashing program
- Cross-platform (Windows, Linux)


### Philosophy

I believe open-source is the way to structure this 
- **Open source** makes better software through community collaboration
- **Free tools** democratize access to professional capabilities
- **Python** is the right language for scientific instrumentation
- **Simplicity** beats feature bloat

---


---

## ✨ Features

### **Instrument Control**

I maintain a second repo [EEequipment repo](https://github.com/andersbandt/EEequipment/tree/master) for the actual API layer of controlling the instruments.

At a high level, there is support for the following types of equipment

- Multimeters
- Power supplies
- Function generators
- Oscilloscopes

There is also some "one off" pieces of equipment like USB relays and debug probes.

Most equipment comes with a USB connection that you can simply plug into your host PC. Older equipment might just have GPIB/HPIB ports that will require some adapter interface. 
If you want to setup some networking switch interface many also include an Ethernet port. I haven't explored this much.

Adding equipment is quite easy, and involves editing a single `.ini` file with your SCPI command list.
Please refer to the [EEequipment repo](https://github.com/andersbandt/EEequipment/tree/master) for a more complete picture of supported equipment and how to add your own.


#### ****
- Generic command/query interface
- **Instrument testing**: Sweep PS and measure with DMM
  - Reports accuracy statistics (mean error, std dev, max error, % FS)
- Benchmark tools for equipment performance (mainly sample rate right now)


### **Automated Data Logging**
- Synchronized multi-instrument data collection
- CSV export
- Customizable sampling rates
- Serial data parsing and logging
- Timestamped recordings

### **Stimulus Sweep Testing**
- Can sweep voltage, frequency, duty cycle
- Can do nested loops as well (max 2 parameters supported right now)
- Linear and logarithmic sweep modes
- Configurable settling times
- Automatic data collection at each step

### **Data Analysis & Visualization**
- Real-time plotting with Plotly (opens in web browser)
- Advanced labeling features (by filename, data column, etc.)
- Save/load graph configurations

### **Semi-Professional UI**
*The UI could use some work, mainly in regard to formatting and sizing on some tabs. It's also not "modern" by any means, but I don't think most engineers prioritize aesthetics*
- Dark theme with customizable colors
- Compact mode for smaller displays
- Cross-platform native look


---

## Screenshots

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

## Quick Start

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

# Run the application
python main.py
```

Please note that for Linux machines you will have to run this command to install Tkinter

```bash
# Install system packages (Linux)
sudo apt-get install python3-tk
```

### VISA backend
In order to use `pyvisa` you will need to configure a backend for the VISA interface. You can read good instructions [here](https://pyvisa.readthedocs.io/en/latest/introduction/configuring.html) on installing this. 


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
2. Click "Refresh" to find your DMM port, and select the right model
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

## Architecture

```
wwd_gui_api/
├── main.py                 # Entry point
├── gui/
│   ├── gui_driver.py       # Main window and notebook
│   ├── gui_class.py        # Themed UI components
│   ├── guiTab_x ....       # file for each tab of the GUI
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

**Command Registry**: Equipment commands loaded from `config.ini` files for flexibility.

**Stimulus Generator**: Reusable sweep logic across logger and ATE tabs.

**Themed Components**: Consistent UI with theme JSON and base classes.

**Service Layer**: Per-equipment service classes in `services/` handle connect/disconnect lifecycle, equipment operations, and error handling — separating business logic from GUI code.

---


## Contributing

I welcome contributions. I consider just installing and testing the application a contribution!
Some easy ways to contribute are


1. **Add equipment drivers** - Have a piece of test equipment? Add support for it!
2. **Test on different platforms/machines** - Help verify cross-platform compatibility
3. **Write tutorials** - Share your workflows and use cases
4. **Report bugs** - Found something broken? Let us know!


---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR**: You can use this software for any purpose, including commercial, as long as you include the license and copyright notice.

This also means it's free for educational use. I encourage usage in lab courses or student projects and research, when applications like LabVIEW are quite cost-prohibitive.


---


## Useful Resources

- [EEequipment repo](https://github.com/andersbandt/EEequipment/tree/master) 
- [PyVISA docs](https://pyvisa.readthedocs.io/)
- [Tkinter best practices](https://tkdocs.com/)
- [Testing with pytest](https://docs.pytest.org/)
- [SCPI commands](https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments)
- [personal blog post about this project](https://andersbandt.github.io/projects/Software_controlled_embedded_test_setup.html)



