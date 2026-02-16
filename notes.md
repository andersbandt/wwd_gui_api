# Development Notes & Recommendations

*Generated: 2025-02-03 | Last updated: 2026-02-16*

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

### ~~Problem 1: Tabs Directly Call Equipment Driver APIs~~ (DONE for connect/disconnect)

Per-equipment service classes created in `services/` and wired into tabs:
- `EquipmentService` base class with common connect/disconnect lifecycle (template method pattern)
- `DMMService`, `PSService`, `FGService`, `OscService` subclasses with device-specific operations
- `ConnectionResult` dataclass returned by `connect()` with `success`, `device_id`, `error`, `timestamp`
- Services instantiated on `ClassController`; tabs call `cc.xxx_service.connect()`/`disconnect()`
- `port_init`/`port_close` migrated for DMM, PS, FG, and OSC tabs

**Remaining worst offenders (inline driver calls, not yet migrated):**
- `guiTab_8_LOG.py` `_collect_data_row` (~line 1311) -- queries DMM, PS, FG, and OSC all in one method
- `guiTab_7_ATE.py` `run_accuracy_test` (~line 376) -- runs a full PS+DMM measurement sweep loop with numpy stats
- `guiTab_6_FG.py` (~line 228-289) -- constructs raw SCPI command strings inline
- `guiTab_3_XDS110.py` `turn_power_on`/`turn_power_off` (~line 378-418) -- multi-equipment power sequencing in GUI

### Problem 2: Threading Logic in GUI Tabs

Tabs spawn `threading.Thread` directly in button callbacks with no lifecycle management.

- `guiTab_3_XDS110.py:75-127` -- 5 separate `threading.Thread(...).start()` calls, one per button
- `guiTab_4_USB.py:267,292` -- thread creation in `port_init` and `start_process`
- `guiTab_8_LOG.py:967` -- recording thread with busy-wait `time.sleep` loops

**Recommendation:** Use `StoppableThread` (already in `gui_class.py`) consistently, and move long-running work into service-layer methods that accept progress/completion callbacks.

### Problem 3: Configuration Parsing Scattered Across Tabs

Multiple tabs read `config/master.ini` or other config files independently. Hardcoded paths have been replaced with `path_helper.get_config_path()`, but each tab still parses the file independently.

- `guiTab_2_DMM.py` -- `load_dmm_config` reads `master.ini`
- `guiTab_3_XDS110.py` -- `parse_target_config` reads target `.ini` files
- `guiTab_4_USB.py` -- `get_baud_rate` reads `master.ini`
- `gui_driver.py` -- `parse_autoconnect_config` reads `master.ini`
- `gui_class.py` -- `get_previous_port` reads `ports_used.xml`

**Recommendation:** Create a `ConfigService` that loads and caches all configuration at startup. Tabs never touch `configparser` or file paths directly.

### Problem 4: Data Transformation / Analysis in Button Callbacks

Statistical analysis and data manipulation embedded directly in GUI methods.

- `guiTab_7_ATE.py:402-449` -- numpy mean, std, max, RMS in `run_accuracy_test`
- `guiTab_8_LOG.py:1393-1471` -- `final_plot` builds DataFrame, selects plot type
- `guiTab_8_LOG.py:855-859` -- `_apply_math_columns` evaluates user math expressions
- `guiTab_9_GRAPH.py:486-516` -- `analyze_files` computes mean/std/min/max on DataFrames

**Recommendation:** Move analysis logic into `analysis/` modules or a `DataService`.

### Problem 5: Shutdown Logic in GUI Driver

`gui_driver.py:238-268` directly calls `ps.output_off(1)`, `ps.disconnect()`, `relay.open_all()`, etc.

**Recommendation:** Add a `ClassController.shutdown()` method. (`PSService.safe_shutdown()` already exists as a starting point.)

### Problem 6: Hardcoded Serial Commands in GUI

`guiTab_4_USB.py:124` has `"DAGA"`, and lines 141-149 map test names to codes like `"FR91"`, `"FR01"`, `"FE42"`.

**Recommendation:** Move to a config file or command dictionary, following the `CommandRegistry` pattern.

### Refactoring Priority

1. **`ClassController.shutdown()`** -- quick win, low risk (`PSService.safe_shutdown()` already exists)
2. **`ConfigService`** -- consolidate config parsing, remove `configparser` from tabs
3. **Move analysis to `analysis/` modules** -- improves testability

---

## Design Patterns & Strengths

- **ClassController** - Centralized equipment management
- **Named Tuples** - Self-documenting file data structures
- **Themed UI** - Consistent look with compact mode scaling
- **StimulusConfig** - DRY principle applied successfully
- **Command Registry** - Flexible equipment command management
- **Service Layer** - `services/` directory for GUI/logic separation, wired into connect/disconnect lifecycle

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

---

## Useful Resources

- PyVISA docs: https://pyvisa.readthedocs.io/
- Tkinter best practices: https://tkdocs.com/
- Testing with pytest: https://docs.pytest.org/
- SCPI commands: https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments

---

*This is a living document. Update as issues are resolved and new priorities emerge.*
