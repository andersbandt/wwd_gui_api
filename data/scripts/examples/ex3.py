"""Temperature profile example (aspirational).

Demonstrates how a custom ramp profile could be defined for an
oven/temperature controller. This script is a design sketch —
it won't run until an oven controller service exists.

The pattern here shows how scripts can define complex stimulus
profiles that go beyond what StimulusConfig supports.
"""

import time


# Custom ramp profile: (command, target_value, duration_minutes)
TEMP_PROFILE = [
    ("SET",  5,   10),   # hold at 5C for 10 min
    ("RAMP", 70,  30),   # ramp to 70C over 30 min
    ("SET",  70,  10),   # hold at 70C for 10 min
    ("RAMP", 220, 30),   # ramp to 220C over 30 min
]


def execute(ctx, log, check_stop):
    # NOTE: ctx does not yet have an oven service.
    # This is a placeholder showing the intended pattern.

    log("Temperature profile:")
    for cmd, value, duration in TEMP_PROFILE:
        log(f"  {cmd} -> {value}C for {duration} min")

    # When an oven service is available, the loop would look like:
    # for cmd, value, duration in TEMP_PROFILE:
    #     check_stop()
    #     if cmd == "SET":
    #         ctx.oven.set_temperature(value)
    #     elif cmd == "RAMP":
    #         ctx.oven.ramp_to(value, duration)
    #     # collect serial data while waiting
    #     end_time = time.time() + duration * 60
    #     while time.time() < end_time:
    #         check_stop()
    #         data = ctx.serial.read()
    #         log(f"T={value}C  data={data}")
    #         time.sleep(1)

    return "Profile defined (oven service not yet available)"
