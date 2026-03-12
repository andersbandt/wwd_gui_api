


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