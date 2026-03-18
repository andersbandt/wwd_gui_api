"""PS voltage sweep with DMM measurement logging.

Sweeps PS channel 1 through a set of voltages, takes DMM readings
at each step, and logs results to a CSV file.

Uses StimulusConfig/StimulusGenerator for sweep generation and
setup_recording/CSVHelper for structured CSV output.
"""

import time

from common.logger import (
    StimulusConfig, StimulusType, SweepMode, StepMode,
    StimulusGenerator, RecordConfig, setup_recording,
)
from common.path_helper import get_data_dir


def execute(ctx, log, check_stop):
    # --- parameters (edit these) ---
    start_v = 0.1
    stop_v = 3.3
    num_steps = 10
    settling_time = 0.5     # seconds to wait after each voltage change
    samples_per_step = 5    # DMM readings per voltage step
    ps_channel = 1

    # --- set up stimulus sweep ---
    stim = StimulusConfig(
        enabled=True,
        stimulus_type=StimulusType.PS_VOLTAGE,
        sweep_mode=SweepMode.LINEAR,
        step_mode=StepMode.NUM_STEPS,
        start_value=start_v,
        stop_value=stop_v,
        step_value=num_steps,
        settling_time=settling_time,
        channel=ps_channel,
    )
    valid, err = stim.validate()
    if not valid:
        log(f"Invalid config: {err}")
        return

    sweep = StimulusGenerator(stim)

    # --- set up CSV logging ---
    rec_config = RecordConfig(use_ps=True, use_dmm=True, ps_channel=1)
    data_dir = get_data_dir("script_data")
    rec_name, csvobj = setup_recording(data_dir, "SCRIPT_SWEEP", "", rec_config, stim)
    csvobj.initialize_file()
    log(f"Logging to: {rec_name}")

    # --- run sweep ---
    ctx.ps.output_on(ps_channel)
    log(f"Sweeping {start_v}V -> {stop_v}V in {len(sweep)} steps")

    for step_num, voltage in enumerate(sweep, 1):
        check_stop()
        ctx.ps.set_voltage(ps_channel, voltage)
        time.sleep(settling_time)

        for s in range(samples_per_step):
            check_stop()
            dmm_val, _ = ctx.dmm.read_value()
            ps_v = ctx.ps.read_voltage(ps_channel)
            ps_i = ctx.ps.read_current(ps_channel)

            row = {
                "Time": time.strftime("%H:%M:%S"),
                "PS_Vset1": f"{voltage:.4f}",
                "PS_Vmeas1": ps_v,
                "PS_Imeas1": ps_i,
                "DMM_Meas1": dmm_val,
                "PS_Voltage": f"{voltage:.4f}",
                "Stimulus_Step": step_num,
            }
            csvobj.write_row(list(row.values()))

        log(f"Step {step_num}/{len(sweep)}: {voltage:.3f}V, DMM={dmm_val}")

    ctx.ps.output_off(ps_channel)
    return f"Sweep complete. Data saved to {rec_name}"


if __name__ == "__main__":
    from common.script_runner import standalone
    standalone(__file__)
