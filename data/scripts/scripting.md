# Scripting and Automation

## Overview

User-defined Python scripts that run against connected equipment through the services layer.
Scripts are self-contained `.py` files — all parameters are defined in the script text, not in the GUI.

Scripts can run two ways:
1. **From the GUI** — ATE tab (Tab 7) provides script selection, Run/Stop buttons, and log output
2. **From the terminal** — `python data/scripts/examples/ex1.py` (uses last-used equipment from `ports_used.xml`)

## Current Implementation (Phase 2 — complete)

### Script contract

Every script must define:

```python
def execute(ctx, log, check_stop):
    ...
```

| Argument     | Type / Description                                                     |
|--------------|------------------------------------------------------------------------|
| `ctx`        | `ScriptContext` — exposes `ctx.ps`, `ctx.dmm`, `ctx.fg`, `ctx.osc`    |
| `log`        | `Callable(str)` — prints to the ATE tab prompt (thread-safe)          |
| `check_stop` | `Callable()` — raises `ScriptStoppedError` if user pressed Stop       |

Scripts can optionally return a string, which gets logged as "Script returned: ...".

### Equipment access

`ScriptContext` exposes the four equipment services directly:

- `ctx.ps` — `PSService` (set_voltage, output_on/off, read_voltage, read_current, etc.)
- `ctx.dmm` — `DMMService` (read_value, set_rate, etc.)
- `ctx.fg` — `FGService` (set_frequency, set_duty, output_on/off, etc.)
- `ctx.osc` — `OscService`

All methods are model-generic. No raw driver access — services handle error catching and null checks.

### Coupling with StimulusConfig / RecordConfig

Scripts can optionally import and use existing logging infrastructure:

- `StimulusConfig` + `StimulusGenerator` — generates sweep values (linear, log, by increment or step count)
- `RecordConfig` + `setup_recording()` — creates structured CSV files with proper headers

See `examples/ex2.py` for a full example of both.
This is optional — scripts can also just use plain `for` loops and their own file I/O.

### Stop mechanism

Scripts call `check_stop()` in their loops. When the user presses Stop:
1. The `_ScriptThread` stop event is set
2. Next `check_stop()` call raises `ScriptStoppedError`
3. `ScriptRunner` catches it, logs "stopped by user", runs `_safe_shutdown()` (PS outputs off)

Unhandled exceptions are also caught — traceback is logged to prompt, safe shutdown runs.

### Standalone mode (terminal)

Scripts can be run directly from the terminal without the GUI. Add this to any script:

```python
if __name__ == "__main__":
    from common.script_runner import standalone
    standalone(__file__)
```

`standalone()` does the following:
1. Finds the project root by walking up from the script file
2. Reads `config/ports_used.xml` for last-used port + model per equipment type
3. Creates a `ClassController`, loads registries, connects equipment via services
4. Builds a `ScriptContext` and calls `execute(ctx, print, check_stop)`
5. Ctrl+C triggers graceful stop (sets stop event, `check_stop()` raises)
6. Runs safe shutdown and `controller.shutdown()` on exit

The `log` callback in standalone mode is just `print`.
Equipment connections come from whatever was last used in the GUI — no hardcoding needed.

---

## Where Things Live

| Concern              | Location                          |
|----------------------|-----------------------------------|
| ScriptRunner         | `common/script_runner.py`         |
| ScriptContext        | `common/script_runner.py`         |
| Script UI            | `gui/guiTab_7_ATE.py` (Tab 7)    |
| User scripts         | `data/scripts/`                   |
| Example scripts      | `data/scripts/examples/`          |
| StimulusConfig       | `common/logger.py`                |
| RecordConfig         | `common/logger.py`                |

---

## Examples

| File    | Description                                                         |
|---------|---------------------------------------------------------------------|
| `ex1.py` | Exponential PS voltage ramp (PS only, simple loop)                 |
| `ex2.py` | PS sweep + DMM measurement with StimulusGenerator + CSV logging    |
| `ex3.py` | Temperature profile sketch (aspirational, oven controller needed)  |
| `ex4.py` | Minimal template — good starting point for new scripts             |

---

## Safety Checklist

- [x] Scripts access services layer only (no raw driver access)
- [x] Scripts run in `_ScriptThread`; stop flag checked via `check_stop()`
- [x] Stop button in ATE tab sends stop signal
- [x] Unhandled exceptions caught, logged to prompt, safe state restored
- [x] PS outputs turned off after script ends (success, failure, or stop)
- [ ] Timeout: kill thread after configurable max duration (not yet implemented)

---

## Future Work

- **Serial integration**: expose `SerialProcessor` on `ScriptContext` (needs a service or direct access)
- **Timeout**: configurable max script duration with forced stop
- **Dry-run validation**: check that required equipment is connected before starting
- **Tier 1 StimulusConfig expansion**: `CUSTOM_POINTS` and `STEP_HOLD` patterns in the Logger tab sweep UI (independent of scripting)
