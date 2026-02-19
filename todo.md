# Development TODO and notes

*Generated: 2026-02-03 | Last updated: 2026-02-19*

---

## Open Tasks

### Near-term / Verify

- [ ] need to give the serial logging a whirl
- [ ] test the math functions properly
- [ ] get the FUNC2 thing working again or eliminate it (would be nice to read XDM1041 datasheet)
- [ ] add unit tests for `logger.py`, `plotter.py`, and the `common` utilities (EEequipment drivers already covered in `tests/`)
- [ ] add some documentation about pyvisa.ResourceManager('@py') in EEequipment
- [ ] clean up the "About" in the Github project page

### UI & Feature Work

- [ ] Change tab color when something is active (e.g., connection live, recording in progress)
- [ ] should I add a mini status indicator in ATE tab next to instrument accuracy testing?
- [ ] add a simulator mode using np.random() or similar to test live plotting / logging / math features
- [ ] multi-logging with mixed sample rates — how to handle equipment with very slow sample rates? (sub-threads per instrument?)
- [ ] custom taskbar icon for the app window

### Future / Exploratory

- [ ] Terminal-only API (connect and control instruments on CLI)
- [ ] Web interface option (Flask/FastAPI backend)
- [ ] Database storage option (SQLite/PostgreSQL)
- [ ] package into a standalone executable (PyInstaller didn't work previously — investigate Nuitka or cx_Freeze)




### Logger tab: per-channel unit scaling

Add a "Scale..." popup dialog (same pattern as the OSC config dialog) letting the user set a scale factor and unit label per channel (e.g. V→mV ×1000, A→mA ×1000). Stores a dict like `{'PS_Vmeas1': (1000, 'mV'), ...}`.

- **`final_plot()` side** — straightforward: multiply each DataFrame column by its scale factor before the `plotter.plot*` call, update the ylabel with the unit label.
- **Live Dash plot side** — harder: scale config needs to be threaded into `plotter.start_live_plot()` state dict and applied in `_ingest_from_bus()`. Do NOT pre-scale at `_save_data_row()` as that would corrupt the CSV.
- **X-axis (stimulus mode only)** — same dialog can expose a scale for the stimulus column.


### Graph tab: filename labeler text box

The `file_labeler` text box next to "Use Filename Labeler" is present in the UI but currently does nothing — `file_label_idx` is read from it and passed all the way into `plotter.plot_multi_file_data()` via `label_config`, but the plotter always ignores it and uses `Path(filename).stem` as the label.

The intended use case: filenames encode metadata (e.g. `sweep_25C_500Hz_board3.csv`) and the user wants that extracted value to be used as the series label, or to drive color mapping.

Three tiers of implementation:

1. ~~**Index-based** (low effort) — user types an int, label becomes `parts[idx]` from the underscore-split filename stem.~~ **DONE**

2. **Regex capture** (low-medium) — skipping for now. Index-based works fine if the filename parts are clean numeric values; user can rename files if needed.

3. **Color normalization for filename mode** (medium) — allow the index-extracted value to drive the `normalize_colors` colormap pipeline, the same way `'data'` mode does. Currently `normalize_colors` only runs in the `data_value_to_color` preprocessing block which is gated on `labeling_mode in ['data', 'both']`. To support `'filename'` mode: collect the extracted `file_parts[idx]` values across all files in a pre-pass, feed them into `data_value_to_color` using the same normalizer logic, then use that color in the `filename` branch plot call. The `label_config` dict already passes `normalize_colors` through in `'both'` mode; would need to extend it for pure `'filename'` mode too.

---

## GUI / Logic Decoupling

The tabs currently act as view, controller, and business logic all in one. The `ClassController` is a shared property bag rather than a mediating abstraction.

### ~~Problem 1: Tabs Directly Call Equipment Driver APIs~~ DONE

Per-equipment service classes in `services/` now handle all equipment interaction:

**Service layer (`services/`):**
- `EquipmentService` base class with connect/disconnect lifecycle (template method pattern)
- `DMMService` — `read_value()`, `set_sample_speed()`
- `PSService` — `output_on/off()`, `set_voltage()`, `set_current()`, `read_voltage()`, `read_current()`, `read_set_voltage()`, `safe_shutdown()`
- `FGService` — `output_on/off()`, `set_shape()`, `set_frequency()`, `set_duty()`, `set_amplitude()`, `set_offset()`, `get_frequency()`, `get_shape()`, `get_duty()`, `get_amplitude()`, `get_offset()`
- `OscService` — connect/disconnect lifecycle
- `ConnectionResult` dataclass returned by `connect()` with `success`, `device_id`, `error`, `timestamp`
- Services instantiated on `ClassController`; tabs call `cc.xxx_service.*`

**Tabs migrated:**
- `guiTab_2_DMM.py`, `guiTab_5_PS.py`, `guiTab_6_FG.py`, `guiTab_10_OSC.py` — connect/disconnect and all inline operations
- `guiTab_6_FG.py` — all 7 action functions (`toggle_output`, `update_FG`, `set_waveform`, `set_frequency`, `set_duty`, `set_amplitude`, `set_offset`) routed through `FGService`; removed `COMMUNICATION_ERRORS` import
- `guiTab_8_LOG.py` — `_collect_data_row`, `_apply_stimulus`, `start_record_stimulus`, `thread_record_serial` all routed through services; removed `COMMUNICATION_ERRORS` import
- `guiTab_7_ATE.py` — `run_accuracy_test` sweep uses `ps_service` and `dmm_service`
- `guiTab_3_XDS110.py` — `turn_power_on`/`turn_power_off` use `ps_service`

**Bugs fixed during migration:**
- `PSService.set_voltage/set_current` had swapped args (`channel, voltage` → `voltage, channel=channel`)
- `DMMService.read_value()` called nonexistent `dmm.read_val()`
- `FGService` had `set_waveform()` and `set_duty_cycle()` calling nonexistent driver methods
- `guiTab_8_LOG.py` `_collect_data_row` channel 2: VMEAS2 was reading `get_set_voltage(2)` instead of `get_voltage(2)`, IMEAS column was writing `get_current(1)` instead of `get_current(2)`
- `guiTab_3_XDS110.py` `turn_power_on`: `ps.set_voltage(channel, vdds)` had args swapped

**Not in scope (no service exists):**
- USB relay calls in `guiTab_3_XDS110.py` — still direct `self.cc.relay.*`
- OSC data collection in `guiTab_8_LOG.py` — still uses `logger.collect_osc_measurements(self.cc.osc, ...)` (already well-abstracted through `logger` module)
- ATE generic device in `guiTab_7_ATE.py` — still uses `COMMUNICATION_ERRORS` for its own device type

### Problem 2: Threading Logic in GUI Tabs

Tabs spawn `threading.Thread` directly in button callbacks with no lifecycle management.

- `guiTab_3_XDS110.py:75-127` -- 5 separate `threading.Thread(...).start()` calls, one per button
- `guiTab_4_USB.py:267,292` -- thread creation in `port_init` and `start_process`
- `guiTab_8_LOG.py:967` -- recording thread with busy-wait `time.sleep` loops

**Recommendation:** Use `StoppableThread` (already in `gui_class.py`) consistently, and move long-running work into service-layer methods that accept progress/completion callbacks.

### ~~Problem 3: Configuration Parsing Scattered Across Tabs~~ DONE

`ConfigService` (`services/config_service.py`) consolidates `master.ini` parsing. GUI tabs no longer import `configparser` — they access config through `ConfigService` or through values passed down at construction time.

### Problem 4: Data Transformation / Analysis in Button Callbacks

Statistical analysis and data manipulation embedded directly in GUI methods.

- ~~`guiTab_7_ATE.py` -- numpy mean, std, max, RMS in `run_accuracy_test`~~ → extracted to `analysis/stats_analysis.py` (`compute_accuracy_stats`, `format_accuracy_report`)
- `guiTab_8_LOG.py` -- `final_plot` builds DataFrame, selects plot type
- ~~`guiTab_8_LOG.py` -- `_apply_math_columns` evaluates user math expressions~~ already extracted to `common/math_columns.py`
- ~~`guiTab_9_GRAPH.py` -- `analyze_files` computes mean/std/min/max on DataFrames~~ → extracted to `analysis/data_helper.py` (`summarize_dataframe`)

**Remaining:** `final_plot` in `guiTab_8_LOG.py` (plot orchestration — lower priority).

### ~~Problem 5: Shutdown Logic in GUI Driver~~ DONE

`ClassController.shutdown()` now handles all equipment disconnection. `gui_driver.py` calls `app.controller.shutdown()` on close.

### Problem 6: Hardcoded Serial Commands in GUI

`guiTab_4_USB.py:124` has `"DAGA"`, and lines 141-149 map test names to codes like `"FR91"`, `"FR01"`, `"FE42"`.

**Recommendation:** Move to a config file or command dictionary, following the `CommandRegistry` pattern.






