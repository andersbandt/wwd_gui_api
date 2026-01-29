# Scripting and Automation Approach

Based on your codebase, I'd recommend a **hybrid approach** that balances flexibility with safety and ease of use. Here's my analysis:

## Current State

Your `StimulusConfig` system (common/logger.py:111-144) currently supports:
- Linear and logarithmic sweeps
- PS voltage, FG frequency, and FG duty cycle stimulus
- Basic parameter validation
- Good integration with the Logger tab

## Recommended Approach: Three-Tier System

### **Tier 1: Expand StimulusConfig (for common patterns)**

Add a few more predefined patterns to `StimulusType`:
- `RAMP_UP_DOWN` - Triangle wave pattern
- `STEP_HOLD` - Step pattern with configurable hold times
- `CUSTOM_POINTS` - User-defined list of values (entered as comma-separated)

**Pros**: Safe, validated, easy GUI integration, covers 80% of use cases

### **Tier 2: Script Mode (for complex sequences)**

Create a new scripting system that loads Python files:

```python
# Example user script: data/scripts/power_ramp_test.py
def execute(equipment, logger, config):
    """
    Custom power supply ramp test

    Args:
        equipment: Equipment controller with .ps, .dmm, .fg, .ser
        logger: Data logger for recording measurements
        config: Dict with user parameters from GUI
    """
    ps = equipment.ps
    dmm = equipment.dmm

    # Custom ramp pattern
    for voltage in [1.0, 1.5, 2.0, 2.5, 3.0]:
        ps.set_voltage(voltage, channel=1)
        time.sleep(config['settling_time'])

        # Take multiple measurements at each step
        for i in range(config['samples_per_step']):
            measurement = dmm.read_value()
            logger.log_row({
                'Voltage': voltage,
                'Measurement': measurement,
                'Sample': i
            })
            time.sleep(0.1)

    return "Test complete!"
```

**Implementation details**:
- Store scripts in `data/scripts/` directory
- Add "Load Script" button in Logger or ATE tab
- Execute in sandboxed environment with timeout
- Provide equipment API wrapper with safety checks
- Show script output in prompt window

**Pros**: Maximum flexibility, reusable, shareable, keeps core code simple

**Cons**: Requires Python knowledge, potential security concerns

### **Tier 3: Visual Sequence Builder (future enhancement)**

A GUI-based sequence builder where users drag-and-drop actions (similar to LabVIEW):
- Set voltage/frequency blocks
- Wait/delay blocks
- Measurement blocks
- Conditional branches
- Save as JSON/YAML

This would be the most user-friendly but requires significant development.

## Recommended Implementation Order

**Phase 1** (Quick win):
1. Add `CUSTOM_POINTS` to `StimulusType` - allows comma-separated list of values
2. Add `hold_time` parameter for step-and-hold patterns

**Phase 2** (Maximum flexibility):
1. Create `ScriptRunner` class in `common/script_runner.py`
2. Add script loader to ATE tab (Tab 7) - makes sense since it's for automated testing
3. Define equipment API wrapper with safety limits
4. Create example scripts in `data/scripts/examples/`

**Phase 3** (Polish):
1. Add script editor with syntax highlighting
2. Add dry-run/validation mode
3. Create script template generator

## Where to Put It?

Given your architecture, I'd suggest:

1. **Expand StimulusConfig** → Keep in `common/logger.py`, add to Logger tab (Tab 2)
2. **Script execution** → Add to **ATE tab (Tab 7)** since it's designed for automated test equipment sequencing
   - Currently Tab 7 is quite basic (just command/query)
   - Perfect place for scripted automation
   - Separates data logging (Tab 2) from test automation (Tab 7)

## Safety Considerations

For script execution, implement:
- **Voltage/current limits** - Check against equipment max ratings before applying
- **Timeout protection** - Kill script if it runs too long
- **Emergency stop** - Big red STOP button
- **Validation mode** - Dry run that shows what would happen without executing
- **Restricted imports** - Only allow safe modules (time, math, numpy), block os, subprocess
- **Equipment state restore** - Return to safe state after script completes/errors

## Next Steps

Would you like to implement:
- Phase 1 (expanding StimulusConfig with more patterns)
- Phase 2 (adding script execution to the ATE tab)
- Both?
