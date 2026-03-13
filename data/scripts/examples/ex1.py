"""Exponential voltage ramp on power supply.

Ramps PS channel 1 from 0V to Vfinal following a 1 - exp(-t/tau) curve.
"""

import numpy as np
import time


def execute(ctx, log, check_stop):
    # --- parameters (edit these) ---
    Vfinal = 5.0
    tau = 0.2       # controls ramp shape (0-1 range, smaller = faster initial rise)
    N = 100
    delay = 0.01    # seconds between steps

    # generate exponential ramp
    t = np.linspace(0, 1, N)
    V = Vfinal * (1 - np.exp(-t / tau))

    ctx.ps.output_on(1)
    log(f"Ramping to {Vfinal}V over {N} steps")

    for i, voltage in enumerate(V):
        check_stop()
        ctx.ps.set_voltage(1, voltage)
        if i % 20 == 0:
            log(f"Step {i}/{N}: {voltage:.3f}V")
        time.sleep(delay)

    ctx.ps.output_off(1)
    return f"Ramp complete ({N} steps)"


if __name__ == "__main__":
    from common.script_runner import standalone
    standalone(__file__)
