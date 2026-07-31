"""Decoder for WWD-n raw flash dumps (the .bin files produced by the USB COMM
tab's "Dump to File" button / DeviceProtocol.dump()).

Mirrors the on-flash record format defined in src/memory/nvs.h and the
page-walk logic in nvs_dump() (src/memory/nvs.c) — see those for the
authoritative layout. A dump is N full NAND pages (PAGE_SIZE bytes each)
concatenated; each page holds zero or more variable-length records packed
back-to-back, terminated by 0xFF padding (erased NAND) or a record that
would overrun the page.
"""

import importlib.util
import logging
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

PAGE_SIZE = 2176  # cfg->bytes_per_page on the MT29F2G01 (2048 data + 128 spare)

# Kernel tick rate — must match WWD-n's prj.conf CONFIG_SYS_CLOCK_TICKS_PER_SEC
# exactly (pinned there as of 2026-07-30 specifically so this doesn't drift
# out of sync again — it used to be an unset default that happened to land on
# 128, while this constant wrongly assumed 32768, i.e. the LFCLK/HW-cycle
# rate rather than the kernel tick rate. That mismatch made every
# reconstructed seconds_since_boot ~256x too slow). Used to convert
# TIME_ANCHOR raw_ticks and accumulated dt_ticks into seconds.
TICKS_PER_SEC = 128

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

    # seconds_since_boot is only contiguous *within* one anchor's reference
    # frame — CMD_ERASE resets NVS's write pointer but not the boot-relative
    # tick counter or the anchor-logging schedule, so a TIME_ANCHOR record
    # can land mid-dump and jump the timebase by the device's real uptime
    # (see nvs_erase_uptime_anchor notes). `segment` marks each such
    # contiguous run so callers can compute durations/rates without bridging
    # that jump.
    segment = 0

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
                    segment += 1
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

            row["segment"] = segment

            ticks_since_boot = anchor_ticks + (0 if type_name == "TIME_ANCHOR" else ticks_since_anchor)
            row["seconds_since_boot"] = ticks_since_boot / TICKS_PER_SEC
            row["wall_time"] = (anchor_walltime + timedelta(seconds=ticks_since_anchor / TICKS_PER_SEC)
                                 if (anchor_walltime is not None and type_name != "TIME_ANCHOR") else
                                 (anchor_walltime if type_name == "TIME_ANCHOR" else pd.NaT))

            rows.append(row)
            seq += 1

    return pd.DataFrame(rows)


@dataclass
class DumpViewConfig:
    """Display/processing options for the USB tab's "View Dump" action, set
    via the "Configure View..." dialog. temp_unit is applied directly;
    imu_script_path/imu_func_name are only used if imu_processing_enabled is
    True, and are resolved to a callable via load_imu_processor() right
    before plotting.
    """
    temp_unit: str = "C"
    imu_processing_enabled: bool = False
    imu_script_path: str = ""
    imu_func_name: str = "process"


def load_imu_processor(path, func_name="process"):
    """Dynamically loads a user-supplied Python function to use as
    plot_dump()'s imu_processor hook (e.g. a filtering routine).

    The file at `path` must define a top-level function `func_name(df)`
    that takes and returns a DataFrame in the same shape as the IMU_FIFO
    rows produced by decode_dump() (accel_x/y/z, gyro_x/y/z, imu_timestamp,
    seconds_since_boot, ...) — typically returning a copy with the same
    columns but filtered/transformed values.

    Raises ImportError/AttributeError/TypeError on a bad path, missing
    function, or non-callable attribute — callers should catch and surface
    these rather than letting a bad script crash the plot.
    """
    spec = importlib.util.spec_from_file_location("_dump_imu_processor", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load a Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, func_name):
        raise AttributeError(f"{path} has no function named '{func_name}'")
    func = getattr(module, func_name)
    if not callable(func):
        raise TypeError(f"'{func_name}' in {path} is not callable")
    return func


def plot_dump(df, title=None, temp_unit="C", imu_processor=None):
    """Basic 3-panel view: accel (g), gyro (dps), temperature vs. seconds
    since boot, each on its own stacked subplot. Skips panels with no data.
    Opens a matplotlib window (blocking show()).

    temp_unit: "C" or "F" — temp_c is converted for display only; the
    underlying DataFrame (and _data.txt export) always stays in Celsius,
    since that's what's on the wire.

    imu_processor: optional callable(imu_df) -> imu_df, applied to the
    IMU_FIFO subset right before plotting (e.g. a filtering function). Left
    as a hook for future processing options; identity by default.
    """
    import matplotlib.pyplot as plt

    if temp_unit not in ("C", "F"):
        raise ValueError(f"temp_unit must be 'C' or 'F', got {temp_unit!r}")

    panels = []
    imu = df[df.record_type == "IMU_FIFO"]
    if not imu.empty:
        if imu_processor is not None:
            imu = imu_processor(imu)
        panels.append(("accel", imu, [("accel_x", "X"), ("accel_y", "Y"), ("accel_z", "Z")], "Accel (g)"))
        panels.append(("gyro", imu, [("gyro_x", "X"), ("gyro_y", "Y"), ("gyro_z", "Z")], "Gyro (dps)"))
    temp = df[df.record_type == "TEMPERATURE"]
    if not temp.empty:
        if temp_unit == "F":
            temp = temp.copy()
            temp["temp_c"] = temp["temp_c"] * 9.0 / 5.0 + 32.0
        panels.append(("temp", temp, [("temp_c", "Temp")], f"Temp ({temp_unit})"))
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


def format_header(df, size_bytes=None):
    """Builds a human-readable metadata summary suitable for a companion
    "_header.txt" file: dump size, per-type record counts, every TIME_ANCHOR
    seen (with wall-clock time if valid), uptime span, and an average IMU
    sample rate. Complements export_datastream()'s raw record dump.
    """
    if df.empty:
        return "No records decoded."

    lines = []
    if size_bytes is not None:
        lines.append(f"Dump size: {size_bytes} bytes")
    lines.append(f"Pages: {df['page'].nunique()}")
    lines.append(f"Total records: {len(df)}")
    lines.append("")
    lines.append("Record counts:")
    for type_name, count in df["record_type"].value_counts().items():
        lines.append(f"  {type_name}: {count}")

    anchors = df[df.record_type == "TIME_ANCHOR"]
    lines.append("")
    lines.append(f"Time anchors ({len(anchors)}):")
    for _, row in anchors.iterrows():
        wall_time = row["wall_time"]
        wall_str = wall_time.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(wall_time) else "invalid"
        lines.append(f"  seq={int(row['seq']):>6}  t={row['seconds_since_boot']:.3f}s  "
                     f"wall={wall_str}  valid={row['time_valid']}")

    # seconds_since_boot can jump mid-dump if CMD_ERASE ran without a reboot
    # (the anchor schedule stays boot-relative — see
    # nvs_erase_uptime_anchor notes). Summing per-segment durations instead
    # of a naive max-min avoids counting that jump as elapsed time.
    lines.append("")
    logged_duration = sum(
        (seg["seconds_since_boot"].max() - seg["seconds_since_boot"].min())
        for _, seg in df.groupby("segment")
    )
    n_segments = df["segment"].nunique()
    if n_segments > 1:
        lines.append(f"Logged duration: {logged_duration:.3f} s  "
                      f"({n_segments} anchor segments — timebase jumps between them, see anchors above)")
    else:
        lines.append(f"Logged duration: {logged_duration:.3f} s")

    imu = df[df.record_type == "IMU_FIFO"]
    if len(imu) > 1:
        sample_count = 0
        imu_duration = 0.0
        for _, seg in imu.groupby("segment"):
            if len(seg) < 2:
                continue
            seg_duration = seg["seconds_since_boot"].iloc[-1] - seg["seconds_since_boot"].iloc[0]
            if seg_duration > 0:
                sample_count += len(seg) - 1
                imu_duration += seg_duration
        if imu_duration > 0:
            rate = sample_count / imu_duration
            lines.append(f"IMU sample rate (avg): {rate:.2f} Hz  ({len(imu)} samples)")

    return "\n".join(lines)


def export_datastream(df, path):
    """Writes the full decoded record stream (one row per record, same
    columns as decode_dump()'s DataFrame) to a CSV-formatted text file.
    """
    df.to_csv(path, index=False, float_format="%.6f")


def summarize(df):
    """One-line-per-type record count summary, for printing to the GUI prompt."""
    if df.empty:
        return "No records decoded."
    counts = df["record_type"].value_counts()
    lines = [f"{len(df)} records decoded, {df['page'].nunique()} page(s):"]
    for type_name, count in counts.items():
        lines.append(f"  {type_name}: {count}")
    # See format_header()'s comment: sum per-segment durations rather than a
    # naive max-min, since seconds_since_boot can jump mid-dump at an
    # anchor boundary if CMD_ERASE ran without a reboot.
    logged_duration = sum(
        (seg["seconds_since_boot"].max() - seg["seconds_since_boot"].min())
        for _, seg in df.groupby("segment")
    )
    lines.append(f"  logged duration: {logged_duration:.1f} s")
    return "\n".join(lines)
