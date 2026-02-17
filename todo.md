# Development Notes & Recommendations

*Generated: 2025-02-03 | Last updated: 2026-02-17*

---

## concise tasks


- [ ] cleanup README
- [ ] evaluate versioning for requirements.txt
- [ ] need to give the serial logging a whirl
- [ ] test the math functions properly
- have Claude go through and compare my application to pymeasure. Strengths? Weaknesses?

---

## Open Tasks


### 1. Add Unit Tests
- **Current**: Only 1 test file in submodule
- **Priority test coverage**:
  - `logger.py` - StimulusGenerator, CSV building
  - `plotter.py` - plot_multi_file_data
  - `common/` utilities
- **Framework**: `pytest`


### 2. Consolidate Analysis Modules
- **Location**: `analysis/` directory (7 files)
- **Issue**: Appears underutilized, unclear purpose
- **Action**: Document what each does, consider if they should be in main app or separate scripts, move IMU-specific code (`imu/`) if not used



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

### Problem 5: Shutdown Logic in GUI Driver

`gui_driver.py:238-268` directly calls `ps.output_off(1)`, `ps.disconnect()`, `relay.open_all()`, etc.

**Recommendation:** Add a `ClassController.shutdown()` method. (`PSService.safe_shutdown()` already exists as a starting point.)

### Problem 6: Hardcoded Serial Commands in GUI

`guiTab_4_USB.py:124` has `"DAGA"`, and lines 141-149 map test names to codes like `"FR91"`, `"FR01"`, `"FE42"`.

**Recommendation:** Move to a config file or command dictionary, following the `CommandRegistry` pattern.

### Refactoring Priority

1. ~~**`ClassController.shutdown()`**~~ -- `PSService.safe_shutdown()` exists; full shutdown consolidation still pending
2. ~~**`ConfigService`**~~ -- DONE
3. ~~**Move analysis to `analysis/` modules**~~ -- partially done (accuracy stats, dataframe summary); `final_plot` remains

---

## Future Vision

### Short Term:
- [ ] Plugin system for community equipment drivers
- [ ] Automated report generation (PDF)
- [ ] FFT/frequency analysis tools
- [ ] Terminal-only API (connect and control instruments on CLI)

### Long Term:
- [ ] Web interface option (Flask/FastAPI backend)
- [ ] Database storage option (SQLite/PostgreSQL)
- [ ] Change tab color when something is active (e.g., connection live, recording in progress)

