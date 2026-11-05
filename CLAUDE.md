# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project provides a GUI-based control system for interfacing with embedded targets and test equipment. Built with Tkinter, it supports control of debug probes, serial ports, power supplies, multimeters, oscilloscopes, and other test/measurement equipment.

The application is called "WWD GUI API" and provides a tabbed interface for different control functions.

### Companion firmware repo

`/home/anders/Documents/NCS/WWD-n` is the Zephyr firmware for the WWD-n board this GUI
talks to. The USB COMM tab's "Device Protocol" panel (`common/device_protocol.py`) is a
hand-written client for a binary protocol whose canonical spec lives there:
`src/comm/protocol.h`. **There is no shared source of truth or codegen between the two
repos** — if `protocol.h`'s `enum protocol_cmd`/`enum protocol_err` changes, update
`device_protocol.py`'s `CMD_*`/`ERR_NAMES` to match by hand, or the host will silently
misparse. That repo has its own `CLAUDE.md`; read `src/comm/protocol_notes.md` there
before doing protocol work from either side.

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

### Services Layer

**services/** contains per-equipment service classes that encapsulate the connect/disconnect lifecycle and business logic, separating it from GUI code:

- `equipment_service.py` — `EquipmentService` base class with template method `connect()`, plus `ConnectionResult` dataclass
- `dmm_service.py` — `DMMService`
- `ps_service.py` — `PSService` (includes `safe_shutdown()`)
- `fg_service.py` — `FGService`
- `osc_service.py` — `OscService`

**Status**: Service layer is fully wired into all relevant tabs (`guiTab_2_DMM`, `guiTab_5_PS`, `guiTab_6_FG`, `guiTab_8_LOG`, `guiTab_10_OSC`). Remaining decoupling work (threading, hardcoded commands) is tracked in `todo.md`.

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
- Tektronix MSO64 oscilloscope, 6 Series / 4 analog channels (PyVISA)
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
- `path_helper.py` — Centralized path management (`get_project_root()`, `resolve_path()`, `get_config_path()`, `get_data_dir()`, `get_full_data_path()`). All bundled resources (`config/`, `data/`, `EEequipment/`) resolve against the project root — derived from `__file__`, never `os.getcwd()` — so the app can be launched from any working directory. Never hardcode a relative path like `"config/master.ini"`; use `resolve_path()`.
- `capture_naming.py` — filename templating for OSC captures. `render()` expands
  a template like `{prefix}_Vin{Vin}_{n:03d}` from built-in tokens (`date`,
  `time`, `datetime`, `n`, `model`) plus user-defined fields, sanitizing each
  value for the filesystem; `next_index()` derives the capture counter from the
  run CSV's row count so it survives a restart. A bad token raises
  `TemplateError` rather than producing a surprising filename.
- `subprocessor.py` — Subprocess execution utilities
- `usb_api.py` — USB device enumeration
- `device_protocol.py` — binary client for the WWD-n firmware's host command protocol
  (`DeviceProtocol` class: ping/dump/erase/get_rate/set_rate). Hand-mirrors
  `src/comm/protocol.h` in the companion firmware repo — see "Companion firmware repo"
  above. Raises `ProtocolError` (framing/CRC/device-side errors) or its subclass
  `ConnectionLostError` (the serial port itself dropped mid-operation — callers should
  treat this as "tear down the connection," not just "retry").
- `dump_decoder.py` — decodes a raw flash dump (`.bin`, from the Dump to File button)
  into a pandas DataFrame (`decode_dump()`), plus an analysis layer and two plots.
  Mirrors the on-flash record layout in the firmware's `src/memory/nvs.h` by hand,
  same sync caveat as `device_protocol.py`.
  - Decode gives one row per record. Two scope columns matter: `segment` is an
    anchor interval (the firmware writes a TIME_ANCHOR every 5 min, so these tick
    over constantly and are NOT boots), and `boot` is a power cycle, detected from
    the kernel tick count going backwards because the firmware writes no
    RESET_MARKER. Activity `session_seq` is RAM-only and restarts at 0 per boot, so
    anything pairing sessions must scope by `boot`.
  - `session_table()` / `wear_table()` / `time_allocation()` turn the edge-triggered
    ACTIVITY and WEAR_STATE markers into spans and a time budget. `capture_duration()`
    is the shared denominator — sums per segment so a reboot or a post-CMD_ERASE
    anchor jump is never counted as elapsed time.
  - `plot_dump()` stacks accel / gyro / temperature (IMU die and SoC die on one axis,
    which is the point — see `record_soc_temp` in nvs.h) / steps, over a wear+session
    context strip, with sessions shaded across every panel.
    `plot_time_allocation()` is the wear-vs-activity budget as stacked bars. Both take
    `show=False` so a caller can raise several figures with one `plt.show()`.

### Analysis

**analysis/** contains data analysis modules:

- `data_helper.py` — CSV/data manipulation and type-conversion utilities
- `stats_analysis.py` — Statistical analysis, linear regression, accuracy metrics, and time-series helpers (duration, sample rate)
- `specific/` — Domain-specific analysis scripts (AFE, clock, IMU, least squares)

### IMU Utilities

**imu/** contains accelerometer/gyroscope analysis tools:

- `butter_lowpass.py` — Butterworth low-pass filter
- `imu_analysis.py` — IMU data analysis
- `live_imu_graph.py` — Real-time IMU visualization

### Configuration

**config/** directory contains:
- `master.ini` — Main config with sections: `[THEME]`, `[PATHS]`, `[AUTOCONNECT]`, `[VISA]`, `[DMM]`, `[USB]`, `[LOGGER]`, `[PS]`, `[OSC]`, `[SHUTDOWN]`, `[Target]`. All reads go through `services/config_service.py` (`ConfigService`) so the file is parsed once; add a getter there rather than reading the file directly. `[PS] output_off_on_connect` (default YES) controls whether `PSService._post_connect` forces both outputs off on connect — set NO to adopt the supply's existing state. `[OSC] capture_template` / `capture_dir` seed the OSC tab's Capture panel (the tech edits the template per run in the tab).
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
4. **USB COMM** (`guiTab_4_USB.py`, `TabUSB`) — USB serial console (ttyACM0) plus a
   "Device Protocol" panel driving a second, independent serial connection (ttyACM1,
   `cdc_acm_uart1` on the firmware side) for the binary command protocol: Ping, Dump to
   File (+ View Dump decoder/plotter, + filename postfix field), Erase Flash, Set Data
   Rates. See "Companion firmware repo" above and `common/device_protocol.py`.
5. **PS Control** (`guiTab_5_PS.py`, `TabPS`) — Power supply control: per-channel voltage and current-limit setpoints (current entry honors the A/mA/uA unit dropdown; SPD3303X applies its calibration offset automatically)
6. **FG Control** (`guiTab_6_FG.py`, `TabFG`) — Function generator control (waveform, frequency, duty cycle)
7. **ATE** (`guiTab_7_ATE.py`, `TabATE`) — Automated test equipment sequencing
8. **Logger** (`guiTab_8_LOG.py`, `TabLog`) — Data logging with various modes (timestamp, raw, data, math columns)
9. **GRAPH** (`guiTab_9_GRAPH.py`, `TabGraph`) — Real-time graphing of measurements with preset support
10. **OSC Control** (`guiTab_10_OSC.py`, `TabOSC`) — Oscilloscope control (channels,
    timebase, trigger, acquisition, measurements) plus a **Capture** panel that saves
    to the *host* filesystem: one click appends a measurement row to the run CSV and
    optionally writes a screenshot PNG beside it. The filename template and the
    user-defined fields feed both the filename and the CSV columns, so a sweep of
    Vin/temperature/load stays self-describing. Orchestration lives in
    `OscService.capture()`; naming in `common/capture_naming.py`.

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
- **tests/** — pytest test suite (run with `pytest tests/`):
  - `test_dmm_drivers.py` — AST-based check that each DMM driver's model name matches a `CommandRegistry` entry; no hardware needed
  - `test_equipment_instantiation.py` — instantiates every `TestEquipment` subclass with connection I/O mocked out; catches unimplemented abstract methods
  - `test_osc_capture.py` — capture filename templating and run-CSV behaviour
    (counter, header widening when a field is added mid-run, screenshot failure
    degrading to a warning); uses a fake scope, no hardware
  - `test_osc_drivers.py` — drives every control the OSC tab exposes against a
    recording fake connection for each scope model, so a missing `config.ini` key
    fails in CI instead of under the tech's mouse; also pins the MSO64's
    Keysight→Tek translations, waveform scaling and screenshot sequence
  - `manual_osc_capture_check.py` — **not** collected by pytest; run it by hand with a
    scope plugged in (`python3 tests/manual_osc_capture_check.py [--model MSO64]`) to
    verify the parts the fakes can't: a real VISA session, a complete screenshot
    transfer (it checks for the PNG `IEND` chunk, which is what catches a
    termination-character truncation), live measurements and a two-capture run
  - New drivers are picked up automatically via `equipment_manager.get_instruments`
- **conftest.py** — Adds project root to `sys.path` so pytest can import `EEequipment` and other packages

## Known Quirks and Gotchas

### Prompt timestamps use `time.strftime`, not `datetime.now`
`Prompt.print()` and `Prompt.print_ansi()` use `time.strftime("%H:%M:%S")` instead of `datetime.now().strftime(...)`. On this Linux machine, `datetime.now()` returns UTC despite the system clock being set to local time — `time.strftime()` reliably returns local time. Do not switch back to `datetime.now()`.

### `or "ERROR"` is wrong for numeric equipment reads
In `_collect_data_row` (Logger tab), always use `val if val is not None else "ERROR"` to guard equipment reads — never `val or "ERROR"`. Clamped current/voltage can return `0.0`, which is falsy and would be replaced with the string `"ERROR"`, breaking the live plot.

### SPD3303X: first VISA connect fails with EOVERFLOW (Errno 75)
The SPD3303X leaves stale data in the USBTMC bulk-in endpoint on disconnect. `PyVISAHandler.connect()` calls `inst.clear()` after `open_resource()` to drain it. This is wrapped in try/except so it silently skips on backends that don't support it. Don't remove this.

### SPD3303X: calibration offset direction is inverted between set and read
The SPD3303X applies per-channel calibration constants from its `config.ini` (`v_slope`/`v_offset`, `i_offset`). Voltage and current setpoints **add** the offset (`set_voltage`, `set_current` override in `SPD3303X.py`) while readbacks **subtract** it (`get_current` does `max(0.0, raw - i_offset)`). This is intentional and must stay symmetric: a requested 30 mA limit sends `0.030 + i_offset` so the effective regulated limit matches what the user asked for. Only the SPD3303X overrides `set_current`; the base `PowerSupply.set_current` sends the raw value with no offset. The PS tab's "Set Current" entry is interpreted in the channel's selected A/mA/uA unit before conversion to amps.

### Equipment I/O is shared between threads — never write-then-read unguarded
The Logger record thread and the PS tab's 10 s status poll (`_schedule_status_poll`)
talk to the *same* instrument session concurrently. `ConnectionHandler` now owns a
per-instance reentrant `io_lock`; `write()`/`read()`/`query()` take it, so a `query()`
is atomic. A bare `conn.write(cmd)` followed by `conn.read()` is **not** atomic — the
two halves can be split by another thread, which hands the wrong reply to the wrong
caller (e.g. `SYST:STAT`'s `'0x4'` reaching `get_set_voltage`'s `float()`) and leaves an
orphaned response in the USBTMC endpoint that surfaces later as `[Errno 75] Overflow`.
Use `conn.query(cmd)`, or `with self.conn.transaction():` for genuine multi-step
exchanges. Reader helpers in `services/` also catch `ValueError` so a malformed reply
returns `None` (logged as `"ERROR"`) instead of killing the record thread.

### Two oscilloscope SCPI dialects — never copy lines between the config.ini files
`DSOX4104A/config.ini` is Keysight/InfiniiVision, `MSO64/config.ini` is TekScope.
They disagree on spelling *and* meaning: Tek's `HORizontal:POSition` is a percentage
of the record where Keysight's `:TIMebase:POSition` is seconds of delay; Tek's
`TRIGger:A:TYPe` is the trigger kind while `TRIGger:A:MODe` is auto/normal, the
opposite of Keysight's `MODE`/`SWEep` naming. The registry keys are mapped by
*meaning*, and `MSO64.py` overrides the methods where behaviour (not just the
string) differs. The OSC tab's dropdowns still emit Keysight words
(`CHANnel1`, `POSitive`, `HRESolution`); `MSO64._TRIG_SOURCES`/`_TRIG_SLOPES`/
`_ACQ_TYPES` translate them so one GUI drives both scopes.

### MSO64 has no immediate-measurement query
The 6 Series dropped `MEASUrement:IMMed`; every measurement is an object that must
be added, pointed at a source, read, and deleted. `MSO64._measure_immediate()`
allocates one scratch slot past the highest one already on screen (so it never
clobbers the tech's own measurement badges), reuses it for the life of the
connection, and deletes it in `disconnect()`. It also has to treat `NAN` as "no
result" — `float("NAN")` succeeds, so the base class's 9.9E37 check alone lets a
silent NaN through into the CSV.

### Measurements are per-measurement tolerant, and a failure must resync the transport
`Oscilloscope.measure_all()` takes each measurement through `measure(name, channel)`
and turns an individual failure into `None` rather than aborting the channel. This is
not defensive padding: on the DSO1014A a single query (`measure_vrms`, which carried
the X-series' `DISPlay,AC` prefix that the 1000 series silently drops) timed out, and
because the old `measure_all` was all-or-nothing, **every** measurement column vanished
from the run CSV. An invalid *channel* still raises — that's a caller bug, and must not
dissolve into a row of blanks.

After any failed exchange, call `TestEquipment.recover()` (→ `ConnectionHandler.flush()`,
`inst.clear()` on VISA). A timed-out query's reply stays queued on the instrument, so
without the flush the *next* read gets the previous answer and every value after it is
off by one — the same failure mode as the `[Errno 75] Overflow` note above, and the
likely source of the `unpack_from ... buffer size is 0` seen after a measurement
timeout. `OscService._measure_channel()` also gives up on a channel after
`MAX_CONSECUTIVE_FAILURES`, since an unresponsive scope costs a full timeout per name.

When adding a scope model, check each `measure_*` line against *that model's*
programming guide rather than copying from another config.ini — the X-series and
1000-series measurement syntax differ in argument lists, not just spelling, and a
wrong one fails as a timeout rather than an error.

### Screenshot format is detected, never assumed
Scopes disagree on what `display_data` returns: the X-series streams a PNG in an
IEEE block, the DSO1014A (1000 series) a BMP that may arrive with no block header
and rejects the X-series' `PNG,COLor` arguments entirely. `Oscilloscope
.get_screenshot()` unwraps the block only when one is present, and
`screenshot_to_file()` picks the extension from the returned magic bytes
(`IMAGE_MAGIC`), so a BMP never lands on disk named `.png`; unrecognisable data
raises instead of writing a corrupt file. Because the real extension isn't known
until the scope answers, `OscService.capture()` reserves the name across every
`capture_naming.IMAGE_EXTENSIONS`.

### Binary reads must drop the VISA termination character
Waveform blocks and screenshot PNGs contain `0x0A` bytes. With `read_termination`
set (every scope config.ini sets it), VISA stops the read at the first one and the
image comes back truncated. `PyVISAHandler.read_raw()` clears the term char for the
duration of the read and restores it after. Use `conn.query_raw(cmd)` for these —
a bare `write()` + `read_raw()` pair is not atomic and hands the block to whichever
thread reads next.

### USB tab serial output: ANSI escape codes from Zephyr
The USB tab's `display_serial_data` uses `prompt.print_ansi()` instead of `prompt.print()`. Zephyr's logging emits ANSI SGR color codes (`\x1b[1;31m` etc.). `print_ansi()` strips the escape sequences and maps them to Tkinter text tags so log levels render in color (red=error, yellow=warning, green=info).

### Device Protocol dump/erase are not cancelable — don't hammer reconnect
`DeviceProtocol.dump()`/`.erase()` are synchronous, blocking calls to the firmware with
no cancel frame in the protocol. If a caller (or a quick test script) gives up early —
short timeout, closing the port, retrying immediately — the firmware keeps
streaming/erasing regardless, and the *next* connection's first read can pick up the
tail of the previous operation's frames interleaved with new ones. This looks exactly
like data corruption but isn't. Let an operation finish (or power-cycle the board)
before starting a new one, especially when debugging the protocol directly rather than
through the GUI buttons (which already serialize this via `_protocol_busy`). A full
~2.2 MB dump takes on the order of a minute — see `src/comm/protocol_notes.md` in the
companion firmware repo for why (`uart_poll_out` throughput, not a bug) and the
`uart_fifo_fill` corruption bug that was tried and reverted there.

### Background-thread errors need explicit handling, not just `except ProtocolError`
Every Device Protocol command that runs on a background thread (Dump, Erase, Ping,
Get/Set Rate) routes failures through `TabUSB._handle_protocol_exception()`, which
catches `ConnectionLostError` specially (tears down the stale `DeviceProtocol`, resets
the connection indicator) and falls back to a generic `except Exception` so an
unanticipated failure surfaces in the prompt instead of dying silently in the thread
(Tkinter does not propagate background-thread exceptions to the GUI — they just print a
traceback to the terminal and vanish otherwise). If you add a new Device Protocol
command handler, route it through this helper rather than a bare
`except (ProtocolError, TimeoutError)`.

## Development Notes

- The codebase uses tag comments like `tag:HARDCODE` for hardcoded values that might need refactoring
- TODO comments indicate known issues and planned improvements
- The application performs graceful shutdown, turning off power supplies and opening all relays when closing (shutdown logic is in `gui_driver.py` lines 236-271)
- Serial port detection methods can be changed via dropdown (Auto/Windows/Linux/PyVISA)
- The GUI adjusts to screen size, using compact mode for smaller displays
- The services layer (`services/`) is wired into all relevant tabs; remaining architectural debt is documented in `todo.md` under "GUI / Logic Decoupling"




## Threading

**Status: resolved / acceptable.**

- `guiTab_3_XDS110.py` -- uses bare `threading.Thread` via a `_run_in_thread(func, button)` helper. Correct for fire-and-forget one-shot actions (build/flash/check/toggle). `StoppableThread` would add no value here since the tasks complete naturally and don't loop.
- `guiTab_4_USB.py` -- all `StoppableThread` (t1/t2/t3), properly stopped in `port_close()`. Clean.
- `guiTab_8_LOG.py` -- `_record_thread` uses `StoppableThread`. `_dash_thread` uses bare `threading.Thread(daemon=True)`, which is correct since Dash's `app.run()` blocks with no external stop mechanism; daemon=True ensures it dies with the process.
- `thread_record_timed` uses deadline-based sleep (`time.monotonic()`) — no busy-wait.


## ATE Tab: Model Dropdown Audit

**Q: Can the model dropdown be replaced with just a connection handler dropdown?**

**Short answer: Not without losing benchmarking functionality.** The model is currently needed for two reasons:

1. **Class instantiation** — `port_init()` does `ate_temp = self.registry[model_name]` then `self.ate = ate_temp(port)`. Different instrument classes have different `__init__` signatures and different connection handler implementations. Removing the model means we lose the Python class entirely.

2. **`benchmark()` needs model-specific methods** — `ate_benchmark()` calls `self.ate.read_value` or `self.ate.test_conn`. Both are model-specific SCPI/serial sequences. Without a known model, there is no `read_value()` to call.

**What IS already model-agnostic:**
- `ate_command()` / `ate_query()` — just call `self.ate.write(cmd)` and `self.ate.query(cmd)` with a user-entered string. These could work fine with a generic connection handler and a user-typed address.
- `run_accuracy_test()` — uses `cc.ps_service` and `cc.dmm_service` exclusively; the ATE device is not involved at all.

**Possible future architecture (if model dropdown becomes a pain point):**
- Keep the connection handler selector (PyVISA / Serial) for the address-based generic send/query.
- Add a separate "benchmark command" text field so the user types the SCPI query string (e.g. `MEAS:VOLT:DC?`). The `benchmark()` helper can accept a callable or a raw command string.
- This would eliminate the need to pick a fully known model just to do timing benchmarks on an arbitrary instrument.

**Also note:** `port_close()` at line 516 calls `self.cc.set_ps(None)` — this appears to be a copy-paste bug. The ATE tab has no dedicated `cc` slot; it should either set `self.ate = None` or be left as-is if the intent was something else. Low priority since it doesn't affect correctness of the PS tab (PS tab manages its own state), but it is confusing.
