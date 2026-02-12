# Development Notes & Recommendations

*Generated: 2025-02-03 | Last updated: 2026-02-12*

---

## Pre-Release Cleanup

### 1. ~~Add MIT License File~~ (DONE)

### 2. Clean Requirements.txt
- **Issues**:
  - `libusb` shouldn't be in requirements.txt (system package)
  - `usb` and `pyusb` are redundant (keep `pyusb`)
  - Missing version pinning (risky for reproducibility)
- **Action**:
  ```txt
  pyserial>=3.5
  matplotlib>=3.5.0
  pandas>=1.4.0
  numpy>=1.21.0
  scipy>=1.7.0
  pyusb>=1.2.1
  PyVISA>=1.12.0
  pyvisa-py>=0.5.3
  ```

### 3. Add .gitignore
- **Should ignore**:
  - `__pycache__/`, `*.pyc`, `*.pyo`
  - `.vscode/`, `.idea/`
  - `data/*.csv`, `data/*.log` (user data)
  - `config/ports_used.xml` (machine-specific)
  - `*.egg-info/`, `dist/`, `build/`

### 4. Cleanup README

---

## Open Tasks

### 5. Remove Hardcoded Values
- **Found 10 instances** with `tag:HARDCODE`
- **Priority fixes**:
  - `gui_driver.py:49` - Hardcoded tab count `range(1, 10)`
  - `guiTab_3_XDS110.py:66` - Hardcoded config file path
  - `guiTab_4_USB.py` - Hardcoded data paths and commands
- **Action**: Move to config file or constants

### 6. Add Graph UI Improvements
- **Location**: `guiTab_9_GRAPH.py:109, 119`
- **Issues**:
  - "make it more intuitive on what is labeling vs data specific"
  - "title text box might have to be bigger"
- **Action**: Add section separators, make title box auto-expand, add tooltips

### 7. Fix Threading Issue in Logger
- **Location**: `guiTab_8_LOG.py:513`
- **Issue**: "do I have to stop the thread here?"
- **Action**: Properly stop/join thread in `stop_record()`

### 8. Add Unit Tests
- **Current**: Only 1 test file in submodule
- **Priority test coverage**:
  - `logger.py` - StimulusGenerator, CSV building
  - `plotter.py` - plot_multi_file_data
  - `common/` utilities
- **Framework**: `pytest`

### 9. Improve Serial Timing Logging
- **Location**: `guiTab_8_LOG.py:523`
- **Issue**: "needs to know if we want serial data to base timing off UART output"
- **Feature**: Option to trigger recording on serial data arrival

### 10. USB Connection After Startup
- **Location**: `guiTab_1_mainDashboard.py:53`
- **Issue**: USB doesn't connect properly after program startup

---

## Code Cleanup - Technical Debt

### 11. Consolidate Analysis Modules
- **Location**: `analysis/` directory (7 files)
- **Issue**: Appears underutilized, unclear purpose
- **Action**: Document what each does, consider if they should be in main app or separate scripts, move IMU-specific code (`imu/`) if not used

### 12. Add Error Handling Improvements
- **Found**: 3 empty `except: pass` blocks
- **Action**: Add logging/error messages

### 13. Create Equipment Driver Documentation
- **Action**:
  - Document base class usage
  - Provide template
  - Examples from existing drivers
  - Add CONTRIBUTING.md to the EEequipment module

---

## GUI / Logic Decoupling

The tabs currently act as view, controller, and business logic all in one. The `ClassController` is a shared property bag rather than a mediating abstraction.

### ~~Problem 1: Tabs Directly Call Equipment Driver APIs~~ (SCAFFOLDING DONE)

Per-equipment service classes created in `services/`:
- `EquipmentService` base class with common connect/disconnect lifecycle (template method pattern)
- `DMMService`, `PSService`, `FGService`, `OscService` subclasses with device-specific operations
- `ConnectionResult` dataclass returned by `connect()` with `success`, `device_id`, `error`, `timestamp`
- Services handle business logic only; GUI updates remain the tab's responsibility
- **Next step:** Wire services into `ClassController` and migrate tabs to use them

**Remaining worst offenders (inline driver calls, not yet migrated):**
- `guiTab_8_LOG.py` `_collect_data_row` (~line 1311) -- queries DMM, PS, FG, and OSC all in one method
- `guiTab_7_ATE.py` `run_accuracy_test` (~line 376) -- runs a full PS+DMM measurement sweep loop with numpy stats
- `guiTab_6_FG.py` (~line 228-289) -- constructs raw SCPI command strings inline
- `guiTab_3_XDS110.py` `turn_power_on`/`turn_power_off` (~line 378-418) -- multi-equipment power sequencing in GUI

### ~~Problem 2: Duplicated `port_init` / `port_close` Pattern~~ (SCAFFOLDING DONE)

The common connect lifecycle is now captured in `services/equipment_service.py` `EquipmentService.connect()`. Each subclass only overrides `_store_on_controller`, `_clear_from_controller`, `_get_from_controller`, and `_post_connect`.

**Next step:** Migrate each tab's `port_init` to call the corresponding service's `connect()` method:
- `guiTab_2_DMM.py` -> `DMMService.connect()`
- `guiTab_5_PS.py` -> `PSService.connect()`
- `guiTab_6_FG.py` -> `FGService.connect()`
- `guiTab_7_ATE.py` -> needs its own service or uses base `EquipmentService` directly
- `guiTab_10_OSC.py` -> `OscService.connect()`

### Problem 3: Threading Logic in GUI Tabs

Tabs spawn `threading.Thread` directly in button callbacks with no lifecycle management.

- `guiTab_3_XDS110.py:75-127` -- 5 separate `threading.Thread(...).start()` calls, one per button
- `guiTab_4_USB.py:267,292` -- thread creation in `port_init` and `start_process`
- `guiTab_8_LOG.py:967` -- recording thread with busy-wait `time.sleep` loops

**Recommendation:** Use `StoppableThread` (already in `gui_class.py`) consistently, and move long-running work into service-layer methods that accept progress/completion callbacks.

### Problem 4: Configuration Parsing Scattered Across Tabs

Multiple tabs read `config/master.ini` or other config files independently.

- `guiTab_2_DMM.py:85-102` -- `load_dmm_config` reads `master.ini`
- `guiTab_3_XDS110.py:358-376` -- `parse_target_config` reads target `.ini` files
- `guiTab_4_USB.py:224-251` -- `get_baud_rate` reads `master.ini`
- `gui_driver.py:30-52` -- `parse_autoconnect_config` reads `master.ini`
- `gui_class.py:468-481` -- `get_previous_port` reads `ports_used.xml`

**Recommendation:** Create a `ConfigService` that loads and caches all configuration at startup. Tabs never touch `configparser` or file paths directly.

### Problem 5: Data Transformation / Analysis in Button Callbacks

Statistical analysis and data manipulation embedded directly in GUI methods.

- `guiTab_7_ATE.py:402-449` -- numpy mean, std, max, RMS in `run_accuracy_test`
- `guiTab_8_LOG.py:1393-1471` -- `final_plot` builds DataFrame, selects plot type
- `guiTab_8_LOG.py:855-859` -- `_apply_math_columns` evaluates user math expressions
- `guiTab_9_GRAPH.py:486-516` -- `analyze_files` computes mean/std/min/max on DataFrames

**Recommendation:** Move analysis logic into `analysis/` modules or a `DataService`.

### Problem 6: Shutdown Logic in GUI Driver

`gui_driver.py:238-268` directly calls `ps.output_off(1)`, `ps.disconnect()`, `relay.open_all()`, etc.

**Recommendation:** Add a `ClassController.shutdown()` method. (`PSService.safe_shutdown()` already exists as a starting point.)

### Problem 7: Hardcoded Serial Commands in GUI

`guiTab_4_USB.py:124` has `"DAGA"`, and lines 141-149 map test names to codes like `"FR91"`, `"FR01"`, `"FE42"`.

**Recommendation:** Move to a config file or command dictionary, following the `CommandRegistry` pattern.

### Refactoring Priority

1. **`ClassController.shutdown()`** -- quick win, low risk (`PSService.safe_shutdown()` already exists)
2. **`ConfigService`** -- consolidate config parsing, remove `configparser` from tabs
3. ~~**Extract `port_init` pattern**~~ -- service classes created, need to wire into tabs
4. ~~**Per-equipment service classes**~~ -- scaffolding done, need to migrate tab code
5. **Move analysis to `analysis/` modules** -- improves testability

---

## Hardcoded Values to Fix

- [ ] `guiTab_3_XDS110.py:66` - Config file path
- [ ] `guiTab_3_XDS110.py:291` - Sleep timer value
- [ ] `guiTab_4_USB.py:127` - Command string
- [ ] `guiTab_4_USB.py:203,209` - Data paths
- [ ] `guiTab_8_LOG.py:553` - Enum mapping
- [ ] `gui_driver.py:35` - Config file path
- [ ] `gui_driver.py:49` - Tab count range
- [ ] `gui_driver.py:125` - Autoconnect list size
- [ ] `gui_driver.py:180` - Unknown hardcode

---

## Design Patterns & Strengths

- **ClassController** - Centralized equipment management
- **Named Tuples** - Self-documenting file data structures
- **Themed UI** - Consistent look with compact mode scaling
- **StimulusConfig** - DRY principle applied successfully
- **Command Registry** - Flexible equipment command management
- **Service Layer** (new) - `services/` directory for GUI/logic separation

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

---

## Useful Resources

- PyVISA docs: https://pyvisa.readthedocs.io/
- Tkinter best practices: https://tkdocs.com/
- Testing with pytest: https://docs.pytest.org/
- SCPI commands: https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments

---

*This is a living document. Update as issues are resolved and new priorities emerge.*
