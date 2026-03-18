"""Exponential voltage ramp on power supply.

Ramps PS channel 1 from 0V to Vfinal following a 1 - exp(-t/tau) curve.
"""

import time
import numpy as np


def execute(ctx, log, check_stop):
    # --- parameters ---
    Vfinal = 0.55
    tau = 37.0
    T_total = 4 * tau
    delay = 0.1

    log_interval = 5.0  # seconds between log message
    start = time.perf_counter()
    last_log_time = 0.0

    log(f"Ramping to {Vfinal}V (tau={tau}s)")
    ctx.ps.output_on(1)
    while True:
        check_stop()

        elapsed = time.perf_counter() - start
        if elapsed >= T_total:
            break

        voltage = Vfinal * (1 - np.exp(-elapsed / tau))
        ctx.ps.set_voltage(1, float(voltage))

        # --- intermediate logging ---
        if elapsed - last_log_time >= log_interval:
            percent = 100.0 * voltage / Vfinal
            log(
                f"t={elapsed:6.1f}s | "
                f"V={voltage:.4f} V ({percent:5.1f}%)"
            )
            last_log_time = elapsed

        time.sleep(delay)


    # force exact final value
    ctx.ps.set_voltage(1, Vfinal)
    #ctx.ps.output_off(1)
    return f"Ramp complete!)"


if __name__ == "__main__":
    from script_runner import standalone
    standalone(__file__)
