"""Template: basic PS + DMM script.

Simple example showing the execute() contract and equipment access.
Edit the parameters below and use as a starting point for new scripts.
"""

import time


def execute(ctx, log, check_stop):
    # --- parameters ---
    voltages = [1.0, 1.5, 2.0, 2.5, 3.0]
    settling_time = 0.5
    samples_per_step = 3

    ctx.ps.output_on(1)

    for voltage in voltages:
        check_stop()
        ctx.ps.set_voltage(1, voltage)
        time.sleep(settling_time)

        for i in range(samples_per_step):
            check_stop()
            dmm_val, _ = ctx.dmm.read_value()
            log(f"V={voltage:.1f}  sample {i+1}: DMM={dmm_val}")
            time.sleep(0.1)

    ctx.ps.output_off(1)
    return "Test complete"


if __name__ == "__main__":
    from common.script_runner import standalone
    standalone(__file__)
