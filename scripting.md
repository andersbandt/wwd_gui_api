# Scripting and Automation Plan

- NOTE: I think I should come up with a few example scripts 
and then ask Claude to implement them based on the examples



## Current State

The `StimulusConfig` system (`common/logger.py`) already supports:
- Linear and logarithmic sweeps
- Dual-stimulus (nested loops)
- PS voltage, FG frequency, FG duty cycle stimulus types
- Basic parameter validation
- Full integration with the Logger tab (Tab 8)

The ATE tab (Tab 7) already has accuracy test automation and stimulus integration.
Scripting would extend this with user-defined sequences beyond what the GUI can configure.

---

## Recommended Approach: Three-Tier System

### Tier 1 — Expand StimulusConfig (quick win, no scripting needed)

Add predefined patterns to `StimulusType` in `common/logger.py`:
- `CUSTOM_POINTS` — comma-separated list of values entered in the GUI (no fixed step size)
- `STEP_HOLD` — step-and-hold with a configurable hold time per step (separate from settling time)

These cover a large portion of real test patterns without requiring a script.
`CUSTOM_POINTS` fits naturally into the existing Logger tab sweep UI.

### Tier 2 — Script Mode (complex/reusable sequences)

Load and execute a user Python file from `data/scripts/`. Run in a `StoppableThread`
so the emergency stop button can interrupt it cleanly.

**Equipment access:** Scripts receive a wrapper around `ClassController` that exposes
the **services layer**, not raw drivers. The services already have safety logic (limits,
state checks). This is the correct boundary — don't expose raw equipment objects.

```python
# Example: data/scripts/power_ramp_test.py

def execute(cc, log, config):
    """
    Args:
        cc:     Equipment wrapper (exposes cc.ps_service, cc.dmm_service, etc.)
        log:    Callable to print to the GUI prompt
        config: Dict of user parameters from the GUI (e.g. settling_time, samples_per_step)
    """
    ps  = cc.ps_service
    dmm = cc.dmm_service

    for voltage in [1.0, 1.5, 2.0, 2.5, 3.0]:
        ps.set_voltage(1, voltage)          # channel, voltage
        time.sleep(config['settling_time'])

        for i in range(config['samples_per_step']):
            meas = dmm.read_value()
            log({'Voltage': voltage, 'Measurement': meas, 'Sample': i})
            time.sleep(0.1)

    return "Test complete"
```

**Implementation notes:**
- `ScriptRunner` class lives in `common/script_runner.py`
- Loads the script with `importlib`, calls `execute(cc_wrapper, log_cb, config)`
- Runs inside a `StoppableThread`; the thread's `stopped()` flag should be checked
  periodically (pass it in, or have the wrapper check it on each equipment call)
- Script output goes to the ATE tab's prompt via the `log` callback (thread-safe `after(0, ...)`)
- On completion or exception, restore equipment to a safe state (PS off, etc.)
- Store user scripts in `data/scripts/`, ship examples in `data/scripts/examples/`

**On "sandboxing":** Python `exec()`-based sandboxing with restricted builtins is
not meaningfully secure. Don't rely on it. The real protection is:
1. The equipment wrapper only exposes service methods (no raw serial/VISA objects)
2. Services enforce voltage/current limits before applying them
3. An emergency stop button calls `StoppableThread.stop()` and triggers safe shutdown

### Tier 3 — Visual Sequence Builder (future, significant effort)

GUI drag-and-drop sequence builder (LabVIEW-style):
- Set voltage/frequency blocks, wait blocks, measurement blocks, conditionals
- Serializes to JSON/YAML for save/load
- No Python knowledge required

Not worth planning in detail until Tier 2 is proven useful.

---

## Implementation Order

**Phase 1 — StimulusConfig expansion** (small, self-contained):
1. Add `CUSTOM_POINTS` to `StimulusType` with a text entry in the Logger tab sweep UI
2. Add `hold_time` field to `StimulusConfig` for step-and-hold patterns

**Phase 2 — Script runner**:
1. `common/script_runner.py` — `ScriptRunner` class (load, validate, execute, stop)
2. Equipment wrapper class — thin wrapper around `cc` exposing only service methods
3. ATE tab (Tab 7) — add script loader UI: file picker, config entry, Run/Stop buttons
4. `data/scripts/examples/` — 2-3 example scripts covering common patterns

**Phase 3 — Polish** (after Phase 2 is working):
1. Script parameter UI — let scripts declare expected config keys with types/defaults
2. Dry-run / validation mode — check equipment is connected before starting
3. Script output saved alongside CSV data

---

## Where Things Live

| Concern              | Location                          |
|----------------------|-----------------------------------|
| StimulusConfig types | `common/logger.py`                |
| Sweep UI             | `gui/guiTab_8_LOG.py` (Tab 8)    |
| ScriptRunner         | `common/script_runner.py`         |
| Script loader UI     | `gui/guiTab_7_ATE.py` (Tab 7)    |
| User scripts         | `data/scripts/`                   |
| Example scripts      | `data/scripts/examples/`          |
| Equipment wrapper    | `common/script_runner.py` or `common/equipment_wrapper.py` |

---

## Safety Checklist (Phase 2)

- [ ] Equipment wrapper enforces service-layer limits (no raw driver access)
- [ ] Scripts run in `StoppableThread`; stop flag propagates to equipment calls
- [ ] Emergency stop button triggers `StoppableThread.stop()` + safe shutdown sequence
- [ ] Unhandled exceptions in script are caught, logged to prompt, safe state restored
- [ ] Timeout: kill thread after configurable max duration
- [ ] PS output turned off after script ends (success or failure)
