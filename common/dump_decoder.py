"""Decoder for WWD-n raw flash dumps (the .bin files produced by the USB COMM
tab's "Dump to File" button / DeviceProtocol.dump()).

Mirrors the on-flash record format defined in src/memory/nvs.h and the
page-walk logic in nvs_dump() (src/memory/nvs.c) — see those for the
authoritative layout. A dump is N full NAND pages (PAGE_SIZE bytes each)
concatenated; each page holds zero or more variable-length records packed
back-to-back, terminated by 0xFF padding (erased NAND) or a record that
would overrun the page.
"""

import logging
import struct
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

PAGE_SIZE = 2176  # cfg->bytes_per_page on the MT29F2G01 (2048 data + 128 spare)

# Kernel tick rate — see prj.conf / CONFIG_SYS_CLOCK_TICKS_PER_SEC. Used to
# convert TIME_ANCHOR raw_ticks and accumulated dt_ticks into seconds.
TICKS_PER_SEC = 32768

# enum record_type order in nvs.h — must match exactly.
RECORD_TYPE_NAMES = {
    0: "TIME_ANCHOR",
    1: "RESET_MARKER",
    2: "IMU_FIFO",
    3: "TEMPERATURE",
    4: "STEP_COUNT",
    5: "POWER",
}

HDR_FMT = "<HHH"  # record_type, length, dt_ticks
HDR_SIZE = struct.calcsize(HDR_FMT)

PAYLOAD_FMT = {
    "TIME_ANCHOR": "<IH6B",   # raw_ticks, year, month, day, hours, minutes, seconds, time_valid
    "IMU_FIFO": "<6hH",       # accel[3], gyro[3], timestamp
    "TEMPERATURE": "<h",      # raw
    "STEP_COUNT": "<I",       # steps
    "POWER": "<BH",           # mode, voltage_mv
    # RESET_MARKER has no payload
}


def decode_dump(data, accel_fsr_g=16, gyro_fsr_dps=2000, page_size=PAGE_SIZE):
    """Decodes a raw flash dump into a single wide DataFrame, one row per record.

    Columns present on every row: seq, page, record_type, dt_ticks,
    seconds_since_boot, wall_time (NaT if no valid RTC anchor seen yet),
    time_valid.

    Type-specific columns (NaN where not applicable): accel_x/y/z (g),
    gyro_x/y/z (dps), imu_timestamp, temp_c, steps, power_mode, power_mv.

    accel_fsr_g / gyro_fsr_dps must match what the firmware was configured
    with at capture time (see startAccel()/startGyro() in imu.c — currently
    hardcoded to 16 g / 2000 dps) since raw ADC counts carry no scale info
    of their own.
    """
    rows = []
    seq = 0

    # Running clock reconstruction. dt_ticks is only a 16-bit delta since the
    # PREVIOUS record and saturates at 0xFFFF, so ticks are accumulated
    # within an anchor interval and re-anchored at every TIME_ANCHOR record
    # (per the reconstruction rule documented in nvs.h / nvs_notes.md) —
    # never summed across an anchor boundary.
    anchor_ticks = 0
    anchor_walltime = None
    time_valid = False
    ticks_since_anchor = 0

    n_pages = len(data) // page_size
    for page_idx in range(n_pages):
        page = data[page_idx * page_size:(page_idx + 1) * page_size]
        offset = 0

        while offset + HDR_SIZE <= page_size:
            if page[offset] == 0xFF:
                break  # rest of page is erased padding

            record_type_raw, length, dt_ticks = struct.unpack_from(HDR_FMT, page, offset)
            offset += HDR_SIZE

            if offset + length > page_size:
                logger.warning("dump_decoder: record overruns page %d at offset %d", page_idx, offset)
                break

            payload = page[offset:offset + length]
            offset += length

            type_name = RECORD_TYPE_NAMES.get(record_type_raw, f"UNKNOWN_{record_type_raw}")

            row = {
                "seq": seq,
                "page": page_idx,
                "record_type": type_name,
                "dt_ticks": dt_ticks,
            }

            if type_name == "TIME_ANCHOR":
                fmt = PAYLOAD_FMT["TIME_ANCHOR"]
                if struct.calcsize(fmt) == len(payload):
                    raw_ticks, year, month, day, hours, minutes, seconds, tv = struct.unpack(fmt, payload)
                    anchor_ticks = raw_ticks
                    ticks_since_anchor = 0
                    time_valid = bool(tv)
                    if time_valid:
                        try:
                            anchor_walltime = datetime(year, month, day, hours, minutes, seconds)
                        except ValueError:
                            anchor_walltime = None
                    else:
                        anchor_walltime = None
                    row["time_valid"] = time_valid
            else:
                ticks_since_anchor += dt_ticks
                row["time_valid"] = time_valid

                if type_name == "IMU_FIFO" and struct.calcsize(PAYLOAD_FMT["IMU_FIFO"]) == len(payload):
                    ax, ay, az, gx, gy, gz, ts = struct.unpack(PAYLOAD_FMT["IMU_FIFO"], payload)
                    row["accel_x"] = ax / 32768.0 * accel_fsr_g
                    row["accel_y"] = ay / 32768.0 * accel_fsr_g
                    row["accel_z"] = az / 32768.0 * accel_fsr_g
                    row["gyro_x"] = gx / 32768.0 * gyro_fsr_dps
                    row["gyro_y"] = gy / 32768.0 * gyro_fsr_dps
                    row["gyro_z"] = gz / 32768.0 * gyro_fsr_dps
                    row["imu_timestamp"] = ts
                elif type_name == "TEMPERATURE" and struct.calcsize(PAYLOAD_FMT["TEMPERATURE"]) == len(payload):
                    (raw,) = struct.unpack(PAYLOAD_FMT["TEMPERATURE"], payload)
                    row["temp_c"] = raw / 128.0 + 25.0
                elif type_name == "STEP_COUNT" and struct.calcsize(PAYLOAD_FMT["STEP_COUNT"]) == len(payload):
                    (steps,) = struct.unpack(PAYLOAD_FMT["STEP_COUNT"], payload)
                    row["steps"] = steps
                elif type_name == "POWER" and struct.calcsize(PAYLOAD_FMT["POWER"]) == len(payload):
                    mode, mv = struct.unpack(PAYLOAD_FMT["POWER"], payload)
                    row["power_mode"] = mode
                    row["power_mv"] = mv

            ticks_since_boot = anchor_ticks + (0 if type_name == "TIME_ANCHOR" else ticks_since_anchor)
            row["seconds_since_boot"] = ticks_since_boot / TICKS_PER_SEC
            row["wall_time"] = (anchor_walltime + timedelta(seconds=ticks_since_anchor / TICKS_PER_SEC)
                                 if (anchor_walltime is not None and type_name != "TIME_ANCHOR") else
                                 (anchor_walltime if type_name == "TIME_ANCHOR" else pd.NaT))

            rows.append(row)
            seq += 1

    return pd.DataFrame(rows)


def plot_dump(df, title=None):
    """Basic 3-panel view: accel (g), gyro (dps), temperature (C) vs. seconds
    since boot, each on its own stacked subplot. Skips panels with no data.
    Opens a matplotlib window (blocking show()).
    """
    import matplotlib.pyplot as plt

    panels = []
    imu = df[df.record_type == "IMU_FIFO"]
    if not imu.empty:
        panels.append(("accel", imu, [("accel_x", "X"), ("accel_y", "Y"), ("accel_z", "Z")], "Accel (g)"))
        panels.append(("gyro", imu, [("gyro_x", "X"), ("gyro_y", "Y"), ("gyro_z", "Z")], "Gyro (dps)"))
    temp = df[df.record_type == "TEMPERATURE"]
    if not temp.empty:
        panels.append(("temp", temp, [("temp_c", "Temp")], "Temp (C)"))
    steps = df[df.record_type == "STEP_COUNT"]
    if not steps.empty:
        panels.append(("steps", steps, [("steps", "Steps")], "Steps"))

    if not panels:
        raise ValueError("Nothing plottable in this dump (no IMU_FIFO/TEMPERATURE/STEP_COUNT records)")

    fig, axes = plt.subplots(len(panels), 1, figsize=(11, 3 * len(panels)), sharex=True)
    if len(panels) == 1:
        axes = [axes]

    for ax, (_, sub_df, series, ylabel) in zip(axes, panels):
        for col, label in series:
            ax.plot(sub_df["seconds_since_boot"], sub_df[col], label=label, linewidth=0.8)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        if len(series) > 1:
            ax.legend(loc="upper right")

    axes[-1].set_xlabel("Seconds since boot")
    fig.suptitle(title or "Flash dump")
    plt.tight_layout()
    plt.show()
    return fig, axes


def summarize(df):
    """One-line-per-type record count summary, for printing to the GUI prompt."""
    if df.empty:
        return "No records decoded."
    counts = df["record_type"].value_counts()
    lines = [f"{len(df)} records decoded, {df['page'].nunique()} page(s):"]
    for type_name, count in counts.items():
        lines.append(f"  {type_name}: {count}")
    span = df["seconds_since_boot"].max() - df["seconds_since_boot"].min()
    lines.append(f"  span: {span:.1f} s of device uptime")
    return "\n".join(lines)
