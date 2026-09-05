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
import os
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
    6: "SOC_TEMP",
    7: "WEAR_STATE",
    8: "ACTIVITY",
    9: "IMU_HEALTH",
}

# struct record_imu_health.event in nvs.h.
IMU_HEALTH_EVENTS = {
    0: "stall",
    1: "recovered",
    2: "recovery_failed",
}

# activity_id_t in src/activity/activity.h — must match exactly. Append only:
# these values are on flash, so renumbering rewrites the meaning of old dumps.
ACTIVITY_NAMES = {
    0: "none",
    1: "running",
    2: "eating",
    3: "working",
    4: "watching TV",
    5: "phone",
    6: "cleaning",
    7: "driving",
}

HDR_FMT = "<HHH"  # record_type, length, dt_ticks
HDR_SIZE = struct.calcsize(HDR_FMT)

PAYLOAD_FMT = {
    "TIME_ANCHOR": "<IH6B",   # raw_ticks, year, month, day, hours, minutes, seconds, time_valid
    "IMU_FIFO": "<6hH",       # accel[3], gyro[3], timestamp
    "TEMPERATURE": "<h",      # raw
    "STEP_COUNT": "<I",       # steps
    "SOC_TEMP": "<h",         # centi_c (hundredths of a degree C)
    "WEAR_STATE": "<B",       # worn (1 = on-wrist, 0 = off-wrist)
    "ACTIVITY": "<BBHI",      # event, activity_id, session_seq, nand_offset
    "POWER": "<BH",           # mode, voltage_mv
    "IMU_HEALTH": "<BBhH",    # event, pwr_mgmt0, raw_temp, frozen_ticks
    # RESET_MARKER has no payload
}


def decode_dump(data, accel_fsr_g=16, gyro_fsr_dps=2000, page_size=PAGE_SIZE,
                progress_callback=None):
    """Decodes a raw flash dump into a single wide DataFrame, one row per record.

    Columns present on every row: seq, page, record_type, dt_ticks,
    seconds_since_boot, wall_time (NaT if no valid RTC anchor seen yet),
    time_valid, segment (anchor interval — one per 5 min of capture), boot
    (power cycle; the scope activity session_seq is unique within).

    Type-specific columns (NaN where not applicable): accel_x/y/z (g),
    gyro_x/y/z (dps), imu_timestamp, temp_c, steps, power_mode, power_mv.

    accel_fsr_g / gyro_fsr_dps must match what the firmware was configured
    with at capture time (see startAccel()/startGyro() in imu.c — currently
    hardcoded to 16 g / 2000 dps) since raw ADC counts carry no scale info
    of their own.

    progress_callback: optional callable(pages_done, total_pages), invoked
    about 100 times over the dump rather than once per page — a 3.2 MB dump is
    ~1450 pages, and a GUI repaint per page would cost several times what the
    decode itself does. The hook has to live inside this loop because the
    decode is a meaningful fraction of View Dump's wall time (~0.6 s of ~2.2 s
    on a full dump), so a caller driving a progress bar cannot just wrap it.
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
    #
    # NOTE `segment` is NOT a boot: the firmware writes a TIME_ANCHOR every
    # ANCHOR_INTERVAL_SEC (300 s, nvs_bringup.c), so segments tick over every
    # five minutes of a healthy capture. Use `boot` below for anything that
    # needs "same power cycle" — most importantly pairing activity sessions,
    # whose session_seq is RAM-only and restarts at 0 on reset.
    segment = 0

    # Boot index. RESET_MARKER would be the natural delimiter but the firmware
    # never writes one (the call in nvs.c:101 is commented out), so the only
    # evidence of a reboot in a dump is the kernel tick count going BACKWARDS
    # between anchors — ticks restart near zero on reset while the log keeps
    # appending. Both signals are honoured here so this keeps working if that
    # call is ever restored.
    boot = 0
    prev_anchor_ticks = None

    n_pages = len(data) // page_size
    report_every = max(1, n_pages // 100)  # ~100 updates over the whole dump
    for page_idx in range(n_pages):
        if progress_callback is not None and page_idx % report_every == 0:
            progress_callback(page_idx, n_pages)
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
                    if prev_anchor_ticks is not None and raw_ticks < prev_anchor_ticks:
                        boot += 1
                    prev_anchor_ticks = raw_ticks
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

                if type_name == "RESET_MARKER":
                    boot += 1

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
                elif type_name == "SOC_TEMP" and struct.calcsize(PAYLOAD_FMT["SOC_TEMP"]) == len(payload):
                    # Already engineering units on the device, unlike
                    # TEMPERATURE's raw IMU counts — see struct record_soc_temp
                    # in nvs.h for why the two are stored differently.
                    (centi_c,) = struct.unpack(PAYLOAD_FMT["SOC_TEMP"], payload)
                    row["soc_temp_c"] = centi_c / 100.0
                elif type_name == "WEAR_STATE" and struct.calcsize(PAYLOAD_FMT["WEAR_STATE"]) == len(payload):
                    # Written only on a change. A gap in IMU_FIFO coverage
                    # should be preceded by worn=0; a gap without one has a
                    # different cause (reset, dump pause, full log).
                    (worn,) = struct.unpack(PAYLOAD_FMT["WEAR_STATE"], payload)
                    row["worn"] = bool(worn)
                elif type_name == "ACTIVITY" and struct.calcsize(PAYLOAD_FMT["ACTIVITY"]) == len(payload):
                    # Session boundary. Pair START with the STOP carrying the
                    # same session_seq to get a span; every IMU_FIFO record
                    # between them belongs to that session, which is how a run
                    # gets its analysis bounds.
                    #
                    # session_seq is unique only WITHIN A BOOT SEGMENT (it is
                    # RAM-only on the device and restarts at 0 after a reset),
                    # so pair within `segment`, not across the whole dump.
                    #
                    # The local names are prefixed on purpose: unpacking into
                    # bare `seq`/`offset` here shadowed the page-walk's own
                    # cursor and record counter, so `offset` jumped to the
                    # marker's nand_offset and the while-loop condition then
                    # ended the page. Every record after the FIRST activity
                    # marker in a page was silently dropped — including, in
                    # most cases, the matching STOP, which made sessions
                    # unpairable. Fixed 2026-08-26.
                    act_event, act_id, act_seq, act_offset = struct.unpack(
                        PAYLOAD_FMT["ACTIVITY"], payload)
                    row["activity"] = ACTIVITY_NAMES.get(act_id, f"unknown_{act_id}")
                    row["activity_id"] = act_id
                    row["activity_event"] = "start" if act_event else "stop"
                    row["session_seq"] = act_seq
                    row["session_offset"] = act_offset
                elif type_name == "POWER" and struct.calcsize(PAYLOAD_FMT["POWER"]) == len(payload):
                    mode, mv = struct.unpack(PAYLOAD_FMT["POWER"], payload)
                    row["power_mode"] = mode
                    row["power_mv"] = mv
                elif type_name == "IMU_HEALTH" and struct.calcsize(PAYLOAD_FMT["IMU_HEALTH"]) == len(payload):
                    # The IMU's sensor data path stopped (or was recovered).
                    # Like WEAR_STATE this is an edge marker, and it explains a
                    # gap in IMU_FIFO coverage that has no worn=0 before it.
                    #
                    # pwr_mgmt0 is the raw register byte: bits 1:0 are
                    # ACCEL_MODE, bits 3:2 GYRO_MODE (0 = OFF, 2 = LP,
                    # 3 = LOW_NOISE), bit 4 IDLE. Both modes reading OFF during
                    # a stall means the part was powered down rather than
                    # internally wedged — see imu_health.c in the firmware.
                    # 0xFF means the register read itself failed.
                    hl_event, pwr, hl_raw, hl_ticks = struct.unpack(
                        PAYLOAD_FMT["IMU_HEALTH"], payload)
                    row["imu_health_event"] = IMU_HEALTH_EVENTS.get(
                        hl_event, f"unknown_{hl_event}")
                    row["imu_pwr_mgmt0"] = pwr
                    row["imu_accel_mode"] = pwr & 0x03 if pwr != 0xFF else None
                    row["imu_gyro_mode"] = (pwr >> 2) & 0x03 if pwr != 0xFF else None
                    row["imu_health_raw_temp"] = hl_raw
                    row["imu_health_frozen_ticks"] = hl_ticks

            row["segment"] = segment
            row["boot"] = boot

            ticks_since_boot = anchor_ticks + (0 if type_name == "TIME_ANCHOR" else ticks_since_anchor)
            row["seconds_since_boot"] = ticks_since_boot / TICKS_PER_SEC
            row["wall_time"] = (anchor_walltime + timedelta(seconds=ticks_since_anchor / TICKS_PER_SEC)
                                 if (anchor_walltime is not None and type_name != "TIME_ANCHOR") else
                                 (anchor_walltime if type_name == "TIME_ANCHOR" else pd.NaT))

            rows.append(row)
            seq += 1

    if progress_callback is not None:
        progress_callback(n_pages, n_pages)

    return _rebuild_wall_time(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# Wall-clock reconstruction
#
# Every TIME_ANCHOR carries a real RTC date/time (year..seconds + time_valid),
# written every ANCHOR_INTERVAL_SEC. That has always been on flash; what was
# missing was trusting it. Everything downstream used to key off
# `seconds_since_boot`, which is device uptime — so two captures separated by a
# power cycle land on top of each other, and "how long was this run" silently
# became "how long had the watch been on".
#
# Two things have to be true before wall time can carry that weight:
#
# ORDERING. Records between anchors are placed by accumulating dt_ticks. That
# accumulation is only as good as the records it walks, and a corrupted length
# or a garbage dt injects time that never happened. On the dump that prompted
# this work, the last anchor read 2026-08-27 13:51 while the accumulated
# stream ran on to Aug 30 — three days of fiction past the last real reading.
#
# BOUNDING. The fix is to treat consecutive anchors as what they are: two
# measured instants with a known number of records between them. The tick
# accumulation sets each record's POSITION within that interval; the anchors
# set its LENGTH. When the accumulation claims more time than the anchors
# allow, it is rescaled to fit and the rows are flagged, rather than being
# quietly believed or quietly dropped.
#
# The last segment has no closing anchor and cannot be bounded this way. It is
# left on raw accumulation, which is the one place a runaway can still show.
# ---------------------------------------------------------------------------

# Slack allowed before an interval is judged to have over-run its anchors.
# Generous on purpose: dt_ticks is integer and the anchor cadence is a software
# timer, so a second of disagreement over a 300 s interval is normal and
# rescaling it would be noise-fitting.
_ANCHOR_SLACK_S = 2.0


def _rebuild_wall_time(df):
    """Re-derives wall_time from the anchors that bracket each segment.

    Adds a `time_rescaled` column marking rows whose interval claimed more
    elapsed time than its two anchors permit. Those rows keep their ORDER and
    their share of the interval, but their absolute times are compressed to fit
    between two measured instants — which is a statement about the log being
    damaged, not about the clock.
    """
    if df.empty or "wall_time" not in df.columns:
        return df

    df["time_rescaled"] = False

    anchors = df[df.record_type == "TIME_ANCHOR"]
    if anchors.empty:
        return df

    # One anchor opens each segment, so the segment IS the anchor interval.
    seg_info = {}
    for _, row in anchors.iterrows():
        seg_info.setdefault(int(row["segment"]),
                            (row["wall_time"], float(row["seconds_since_boot"]),
                             int(row["boot"])))

    segments = sorted(seg_info)
    for i, seg in enumerate(segments):
        anchor_wall, anchor_s, anchor_boot = seg_info[seg]
        if pd.isna(anchor_wall):
            continue

        mask = df["segment"] == seg
        offsets = df.loc[mask, "seconds_since_boot"] - anchor_s
        if offsets.empty:
            continue

        scale = 1.0
        if i + 1 < len(segments):
            next_wall, _, next_boot = seg_info[segments[i + 1]]
            # Only a same-boot successor bounds anything: across a reset the
            # tick base restarts, so the "interval" is not one.
            if next_boot == anchor_boot and pd.notna(next_wall):
                budget = (next_wall - anchor_wall).total_seconds()
                span = float(offsets.max())
                if budget >= 0 and span > budget + _ANCHOR_SLACK_S:
                    scale = budget / span if span > 0 else 1.0
                    df.loc[mask, "time_rescaled"] = True

        df.loc[mask, "wall_time"] = anchor_wall + pd.to_timedelta(offsets * scale, unit="s")

    return df


def dump_has_wall_time(df):
    """True if this dump carries usable RTC time.

    False for a board whose RTC was never set (every anchor has time_valid=0,
    e.g. no backup cell fitted), which is the case every caller has to keep
    working for — hence the boot-relative fallbacks throughout.
    """
    return (not df.empty and "wall_time" in df.columns
            and df["wall_time"].notna().any())


def dump_time_axis(df, prefer="auto"):
    """Picks the time domain to report in: ("wall_time", label) or
    ("seconds_since_boot", label).

    prefer: "auto" uses wall clock when the dump has it, "wall" demands it
    (raises if absent), "boot" forces uptime.
    """
    if prefer not in ("auto", "wall", "boot"):
        raise ValueError(f"prefer must be auto/wall/boot, got {prefer!r}")
    if prefer == "boot":
        return "seconds_since_boot", "Seconds since boot"
    if dump_has_wall_time(df):
        return "wall_time", "Time"
    if prefer == "wall":
        raise ValueError("this dump carries no valid RTC time (every anchor has "
                         "time_valid=0) — nothing to build a wall-clock axis from")
    return "seconds_since_boot", "Seconds since boot"


def _segment_wall_intervals(df):
    """(start, end) wall-clock timestamps for each segment that has them."""
    if not dump_has_wall_time(df):
        return []
    intervals = []
    for _, seg in df.groupby("segment"):
        wall = seg["wall_time"].dropna()
        if len(wall) >= 1:
            intervals.append((wall.min(), wall.max()))
    return intervals


def _union_seconds(intervals):
    """Total length of a union of (start, end) intervals, in seconds.

    A UNION rather than a sum, because segments can overlap in real time and
    summing them counts the overlap twice. That is not hypothetical: a driver
    bug that mirrored half the NAND put the same capture on flash twice, and
    the summed version reported 101 hours for 15 hours of wall clock. A union
    reports the same answer whether or not the log repeats itself, which is
    the property worth having in a number labelled "captured".
    """
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    total = 0.0
    cur_start, cur_end = ordered[0]
    for start, end in ordered[1:]:
        if start > cur_end:
            total += (cur_end - cur_start).total_seconds()
            cur_start, cur_end = start, end
        elif end > cur_end:
            cur_end = end
    total += (cur_end - cur_start).total_seconds()
    return total


def capture_wall_span(df):
    """(first, last) wall-clock timestamps in the dump, or (None, None)."""
    if not dump_has_wall_time(df):
        return None, None
    wall = df["wall_time"].dropna()
    return wall.min(), wall.max()


# ---------------------------------------------------------------------------
# Analysis layer
#
# decode_dump() gives one row per record, which is the right shape for plotting
# a signal and the wrong shape for every question about SPANS: how long was a
# run, how much of the capture was on-wrist, where does this session's IMU data
# start. ACTIVITY and WEAR_STATE are both edge-triggered — written only on a
# change — so those answers come from pairing consecutive markers, not from
# resampling a column. That pairing lives here so the GUI, the header export
# and any ad-hoc notebook all get the same numbers.
# ---------------------------------------------------------------------------

SESSION_COLUMNS = ["boot", "session_seq", "activity", "activity_id",
                   "start_s", "stop_s", "duration_s", "start_wall", "stop_wall",
                   "imu_samples", "complete"]


def session_table(df):
    """Pairs ACTIVITY start/stop markers into one row per session.

    session_seq is RAM-only on the device and restarts at 0 after a reset, so
    pairing is scoped by `boot`, never across the whole dump.

    A session with no STOP is still returned, with complete=False and its
    duration clamped to the last record of that boot. That is the normal shape
    for the session that was still running when the dump was taken, and also
    what a mid-run reset leaves behind — the distinction matters because an
    unterminated session's duration is a lower bound, not a measurement.

    imu_samples counts the IMU_FIFO records that fall inside the session's
    bounds, which is what tells you whether a session actually has data to
    analyse: wear detection gates NVS writes, so a session recorded off-wrist
    can be a perfectly valid span with nothing in it.
    """
    if df.empty or "activity_event" not in df.columns:
        return pd.DataFrame(columns=SESSION_COLUMNS)

    markers = df[df.record_type == "ACTIVITY"]
    if markers.empty:
        return pd.DataFrame(columns=SESSION_COLUMNS)

    imu = df[df.record_type == "IMU_FIFO"]
    rows = []

    for (boot, sess), group in markers.groupby(["boot", "session_seq"], sort=True):
        group = group.sort_values("seq")
        starts = group[group.activity_event == "start"]
        stops = group[group.activity_event == "stop"]

        # A STOP with no START means the START is off the front of the dump
        # (erased, or overwritten). Report it rather than dropping it — a
        # silently missing session is worse than a flagged partial one.
        start = starts.iloc[0] if not starts.empty else None
        stop = stops.iloc[-1] if not stops.empty else None
        ref = start if start is not None else stop

        boot_rows = df[df.boot == boot]
        have_wall = dump_has_wall_time(df)

        if start is not None:
            start_s = start["seconds_since_boot"]
            start_wall = start["wall_time"] if have_wall else pd.NaT
        else:
            start_s = boot_rows["seconds_since_boot"].min()
            start_wall = boot_rows["wall_time"].min() if have_wall else pd.NaT

        if stop is not None:
            stop_s = stop["seconds_since_boot"]
            stop_wall = stop["wall_time"] if have_wall else pd.NaT
            complete = start is not None
        else:
            stop_s = boot_rows["seconds_since_boot"].max()
            stop_wall = boot_rows["wall_time"].max() if have_wall else pd.NaT
            complete = False

        # Wall clock decides the duration when both ends are real instants.
        # An unterminated session is clamped to the end of its boot, and in
        # uptime that bound is wrong the moment a log resumes or repeats.
        if pd.notna(start_wall) and pd.notna(stop_wall):
            duration_s = (stop_wall - start_wall).total_seconds()
        else:
            duration_s = float(stop_s - start_s)

        in_bounds = imu[(imu.boot == boot) &
                        (imu.seconds_since_boot >= start_s) &
                        (imu.seconds_since_boot <= stop_s)]

        rows.append({
            "boot": int(boot),
            "session_seq": int(sess),
            "activity": ref["activity"],
            "activity_id": int(ref["activity_id"]),
            "start_s": float(start_s),
            "stop_s": float(stop_s),
            "duration_s": duration_s,
            "start_wall": start_wall,
            "stop_wall": stop_wall,
            "imu_samples": int(len(in_bounds)),
            "complete": bool(complete),
        })

    return pd.DataFrame(rows, columns=SESSION_COLUMNS).sort_values(
        ["boot", "start_s"]).reset_index(drop=True)


WEAR_COLUMNS = ["boot", "worn", "start_s", "stop_s", "duration_s",
                "start_wall", "stop_wall"]


def wear_table(df):
    """Turns WEAR_STATE transition markers into spans.

    Like ACTIVITY, these are written only on a CHANGE, so each marker opens a
    span that the next marker (or the end of that boot) closes. The state
    BEFORE the first marker is genuinely unknown — the device only logs the
    edge — so no span is emitted for it; that leading time shows up as the
    difference between the capture duration and the summed span durations.

    duration_s is measured in WALL CLOCK when the dump carries it, and in
    uptime otherwise. The two disagree in exactly the case that matters: a
    span closed by "the end of this boot" is bounded by the last record of the
    boot, and on a log that repeats or resumes, the last record by uptime is
    not the last record in real time.
    """
    if df.empty or "worn" not in df.columns:
        return pd.DataFrame(columns=WEAR_COLUMNS)

    markers = df[df.record_type == "WEAR_STATE"]
    if markers.empty:
        return pd.DataFrame(columns=WEAR_COLUMNS)

    have_wall = dump_has_wall_time(df)
    rows = []
    for boot, group in markers.groupby("boot", sort=True):
        group = group.sort_values("seq")
        boot_rows = df[df.boot == boot]
        boot_end = boot_rows["seconds_since_boot"].max()
        boot_end_wall = boot_rows["wall_time"].max() if have_wall else pd.NaT

        times = list(group["seconds_since_boot"])
        walls = list(group["wall_time"]) if have_wall else [pd.NaT] * len(times)
        worn_flags = list(group["worn"])

        for i, (t, worn) in enumerate(zip(times, worn_flags)):
            last = (i + 1 == len(times))
            end = boot_end if last else times[i + 1]
            end_wall = boot_end_wall if last else walls[i + 1]

            if pd.notna(walls[i]) and pd.notna(end_wall):
                duration = (end_wall - walls[i]).total_seconds()
            else:
                duration = float(end - t)

            rows.append({
                "boot": int(boot),
                "worn": bool(worn),
                "start_s": float(t),
                "stop_s": float(end),
                "duration_s": duration,
                "start_wall": walls[i],
                "stop_wall": end_wall,
            })

    return pd.DataFrame(rows, columns=WEAR_COLUMNS)


def capture_duration(df):
    """Total REAL time the dump covers, in seconds.

    Wall clock when the dump has it: the union of the per-segment wall-clock
    intervals (see _union_seconds for why a union and not a sum). That is the
    honest answer to "how much time is in this file" — it does not grow when
    the log repeats itself, and it does not shrink when the device is rebooted
    mid-capture.

    Falls back to summing per-segment `seconds_since_boot` spans when there is
    no valid RTC time. Per-segment rather than max-min because uptime jumps at
    a reboot and at a CMD_ERASE, and bridging either would report the device's
    uptime as capture time.
    """
    if df.empty:
        return 0.0

    intervals = _segment_wall_intervals(df)
    if intervals:
        return _union_seconds(intervals)

    return float(sum(
        (seg["seconds_since_boot"].max() - seg["seconds_since_boot"].min())
        for _, seg in df.groupby("segment")))


def time_allocation(df):
    """Where the captured time went, as a DataFrame of category/seconds/pct.

    Two independent breakdowns, both against the same capture duration:

      wear      - on-wrist vs off-wrist vs unknown (before the first marker)
      activity  - per declared activity, plus 'unallocated' for time inside no
                  session at all

    They are deliberately not merged into one table: a session can run while
    the watch reads off-wrist, so the two breakdowns overlap and adding them
    together would double-count.
    """
    total = capture_duration(df)
    rows = []

    wear = wear_table(df)
    if not wear.empty:
        for worn_state, label in ((True, "worn"), (False, "not worn")):
            secs = float(wear[wear.worn == worn_state]["duration_s"].sum())
            rows.append({"breakdown": "wear", "category": label, "seconds": secs})
        unknown = total - float(wear["duration_s"].sum())
        if unknown > 0.5:
            rows.append({"breakdown": "wear", "category": "unknown", "seconds": unknown})

    sessions = session_table(df)
    if not sessions.empty:
        for activity, group in sessions.groupby("activity"):
            rows.append({"breakdown": "activity", "category": activity,
                         "seconds": float(group["duration_s"].sum())})
        unallocated = total - float(sessions["duration_s"].sum())
        if unallocated > 0.5:
            rows.append({"breakdown": "activity", "category": "unallocated",
                         "seconds": unallocated})

    out = pd.DataFrame(rows, columns=["breakdown", "category", "seconds"])
    if not out.empty:
        out["pct"] = out["seconds"] / total * 100.0 if total > 0 else 0.0
    else:
        out["pct"] = []
    return out


def _format_hms(seconds):
    """Compact h/m/s for report lines — 3661.4 -> '1h 01m 01s'."""
    seconds = float(seconds)
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    h, rem = divmod(int(round(seconds)), 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{sign}{h}h {m:02d}m {sec:02d}s"
    if m:
        return f"{sign}{m}m {sec:02d}s"
    return f"{sign}{sec}s"


@dataclass
class DumpViewConfig:
    """Display/processing options for the USB tab's "View Dump" action, set
    via the "Configure View..." dialog. temp_unit is applied directly;
    imu_script_path/imu_func_name are only used if imu_processing_enabled is
    True, and are resolved to a callable via load_imu_processor() right
    before plotting. reuse_cached lets View Dump skip decoding and re-writing
    the text export when the artifacts beside the dump are still fresh — see
    artifact_is_fresh().
    """
    temp_unit: str = "C"
    reuse_cached: bool = True
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


# Span fill colours, indexed by activity_id. Deliberately pale: these sit
# UNDER the data on every panel and must never compete with it.
_ACTIVITY_COLORS = ["#7f7f7f", "#1f77b4", "#2ca02c", "#d62728", "#9467bd",
                    "#8c564b", "#e377c2", "#bcbd22"]


def _span_xs(row, wall):
    """(start, stop) for a session/wear row in the axis domain being plotted.

    Falls back to the uptime columns per-row rather than per-table: a session
    whose START was erased off the front of the dump has no start_wall even in
    a dump that otherwise has wall clock everywhere.
    """
    if wall and pd.notna(row.get("start_wall")) and pd.notna(row.get("stop_wall")):
        return row["start_wall"], row["stop_wall"]
    return row["start_s"], row["stop_s"]


def _shade_sessions(ax, sessions, label_axis=False, wall=False):
    """Draws each activity session as a shaded span across one axis.

    Applied to every panel so a feature in the accel trace can be read against
    the session it belongs to without eyeballing across subplots — that
    alignment is the whole reason the sessions are on the plot at all.
    """
    for _, row in sessions.iterrows():
        color = _ACTIVITY_COLORS[int(row["activity_id"]) % len(_ACTIVITY_COLORS)]
        x0, x1 = _span_xs(row, wall)
        ax.axvspan(x0, x1, color=color, alpha=0.13, lw=0, zorder=0)
        if label_axis:
            # Hatch an unterminated session so a lower-bound duration never
            # reads as a measured one.
            if not row["complete"]:
                ax.axvspan(x0, x1, facecolor="none", edgecolor=color,
                           hatch="///", alpha=0.35, lw=0, zorder=0)
            ax.text(x0, 1.06, f" {row['activity']}",
                    transform=ax.get_xaxis_transform(), fontsize=7,
                    color=color, ha="left", va="bottom")


def plot_dump(df, title=None, temp_unit="C", imu_processor=None,
              show_context=True, show=True, time_axis="auto"):
    """Stacked time-series view of a dump, one panel per signal family, sharing
    one time axis. Skips panels with no data. Opens a matplotlib window
    (blocking show()).

    time_axis: "auto" (default) plots against RTC wall clock when the dump
    carries it and falls back to seconds-since-boot when it does not; "wall"
    demands wall clock; "boot" forces uptime. Wall clock is the default
    because uptime cannot survive a power cycle — two captures either side of
    a reset both start at zero and draw on top of each other, which is exactly
    the reading this axis is supposed to prevent.

    Panels, in order: accel (g), gyro (dps), temperature, steps, and a context
    strip carrying wear state and activity sessions.

    temp_unit: "C" or "F" — applied to BOTH temperature series for display
    only; the underlying DataFrame (and _data.txt export) always stays in
    Celsius, since that's what's on the wire.

    The temperature panel plots the IMU die and the SoC die together on
    purpose. The firmware logs them back-to-back on one tick specifically so
    they can be differenced (see struct record_soc_temp in nvs.h): one die
    sensor cannot separate self-heating from sensor error, two on the same
    board can, and that is only visible if they share an axis.

    show_context: draw the wear/session strip and shade sessions across the
    other panels. Off gives the plain signal view.

    show: call plt.show() before returning. Pass False to build the figure and
    leave it to the caller to display — plt.show() raises every open figure, so
    a caller wanting this plot AND the time-allocation one side by side builds
    the other first with show=False and lets this call raise both.

    imu_processor: optional callable(imu_df) -> imu_df, applied to the
    IMU_FIFO subset right before plotting (e.g. a filtering function).
    """
    import matplotlib.pyplot as plt

    if temp_unit not in ("C", "F"):
        raise ValueError(f"temp_unit must be 'C' or 'F', got {temp_unit!r}")

    xcol, xlabel = dump_time_axis(df, prefer=time_axis)
    wall = (xcol == "wall_time")

    def to_unit(series):
        return series * 9.0 / 5.0 + 32.0 if temp_unit == "F" else series

    panels = []
    imu = df[df.record_type == "IMU_FIFO"]
    if not imu.empty:
        if imu_processor is not None:
            imu = imu_processor(imu)
        panels.append(("accel", imu, [("accel_x", "X"), ("accel_y", "Y"), ("accel_z", "Z")], "Accel (g)"))
        panels.append(("gyro", imu, [("gyro_x", "X"), ("gyro_y", "Y"), ("gyro_z", "Z")], "Gyro (dps)"))

    # One panel, both dies. Merged on seconds_since_boot rather than plotted
    # from two frames so the legend and any later differencing see one table.
    temp = df[df.record_type == "TEMPERATURE"]
    soc = df[df.record_type == "SOC_TEMP"]
    if not temp.empty or not soc.empty:
        series = []
        frame = pd.DataFrame()
        if not temp.empty:
            frame = temp[[xcol]].copy()
            frame["imu_die"] = to_unit(temp["temp_c"])
            series.append(("imu_die", "IMU die"))
        if not soc.empty:
            soc_frame = soc[[xcol]].copy()
            soc_frame["soc_die"] = to_unit(soc["soc_temp_c"])
            frame = soc_frame if frame.empty else pd.concat([frame, soc_frame])
            series.append(("soc_die", "SoC die"))
        panels.append(("temp", frame.sort_values(xcol), series,
                       f"Temp ({temp_unit})"))

    steps = df[df.record_type == "STEP_COUNT"]
    if not steps.empty:
        panels.append(("steps", steps, [("steps", "Steps")], "Steps"))

    sessions = session_table(df) if show_context else pd.DataFrame()
    wear = wear_table(df) if show_context else pd.DataFrame()
    context = show_context and (not sessions.empty or not wear.empty)

    if not panels and not context:
        raise ValueError("Nothing plottable in this dump "
                         "(no IMU_FIFO/TEMPERATURE/SOC_TEMP/STEP_COUNT records, "
                         "and no wear or activity markers)")

    n_axes = len(panels) + (1 if context else 0)
    heights = [3] * len(panels) + ([1.1] if context else [])
    fig, axes = plt.subplots(n_axes, 1, figsize=(11, sum(heights)), sharex=True,
                             gridspec_kw={"height_ratios": heights})
    if n_axes == 1:
        axes = [axes]

    for ax, (_, sub_df, series, ylabel) in zip(axes, panels):
        for col, label in series:
            # dropna per series: the temp frame is two record types stacked, so
            # each column is dense only on its own rows.
            sub = sub_df[[xcol, col]].dropna() if col in sub_df else None
            if sub is None or sub.empty:
                continue
            ax.plot(sub[xcol], sub[col], label=label, linewidth=0.8)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        if len(series) > 1:
            ax.legend(loc="upper right")
        if context:
            _shade_sessions(ax, sessions, wall=wall)

    if context:
        ax = axes[-1]
        if not wear.empty:
            # Step, not scatter: worn state is piecewise-constant between
            # edge-triggered markers, and a line implying a ramp between them
            # would be a lie about what the device recorded.
            xs, ys = [], []
            for _, row in wear.iterrows():
                x0, x1 = _span_xs(row, wall)
                xs += [x0, x1]
                ys += [1 if row["worn"] else 0] * 2
            ax.step(xs, ys, where="post", color="#2ca02c", linewidth=1.2, label="worn")
            ax.fill_between(xs, ys, step="post", color="#2ca02c", alpha=0.18)
        ax.set_ylim(-0.15, 1.15)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["off", "on"])
        ax.set_ylabel("Wrist")
        ax.grid(True, alpha=0.3)
        _shade_sessions(ax, sessions, label_axis=True, wall=wall)

    axes[-1].set_xlabel(xlabel)
    if wall:
        # Let matplotlib pick the tick density, but keep the date off every
        # tick — a capture is usually inside one day and repeating it eleven
        # times across the axis is noise. The date goes in the offset label.
        import matplotlib.dates as mdates
        locator = mdates.AutoDateLocator()
        axes[-1].xaxis.set_major_locator(locator)
        axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.suptitle(title or "Flash dump")
    plt.tight_layout()
    if show:
        plt.show()
    return fig, axes


def plot_time_allocation(df, title=None, show=True):
    """Horizontal stacked bars: one for the wear breakdown, one for activity.

    A pie chart is the reflex here and it is the wrong mark — these are parts
    of one known total (the capture duration) and the interesting comparison
    is between the two breakdowns, which a shared linear axis supports and
    angle does not.

    show: as plot_dump() — pass False to build the figure without displaying it.

    Returns (fig, ax), or None if the dump carries no wear or activity markers.
    """
    import matplotlib.pyplot as plt

    alloc = time_allocation(df)
    if alloc.empty:
        return None

    colors = {
        "worn": "#2ca02c", "not worn": "#d62728", "unknown": "#bbbbbb",
        "unallocated": "#dddddd",
    }
    fig, ax = plt.subplots(figsize=(10, 2.6))
    order = [b for b in ("wear", "activity") if b in set(alloc["breakdown"])]

    for y, breakdown in enumerate(order):
        left = 0.0
        for _, row in alloc[alloc.breakdown == breakdown].iterrows():
            width = row["seconds"]
            color = colors.get(row["category"], _ACTIVITY_COLORS[
                (hash(row["category"]) % (len(_ACTIVITY_COLORS) - 1)) + 1])
            ax.barh(y, width, left=left, color=color, edgecolor="white")
            # Only label a slice wide enough to hold text — a 2% sliver's
            # label lands on its neighbours and makes the bar unreadable.
            if width / max(alloc[alloc.breakdown == breakdown]["seconds"].sum(), 1) > 0.08:
                ax.text(left + width / 2, y,
                        f"{row['category']}\n{_format_hms(width)} ({row['pct']:.0f}%)",
                        ha="center", va="center", fontsize=8)
            left += width

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([b.capitalize() for b in order])
    ax.set_xlabel("Seconds of capture")
    ax.set_title(title or "Time allocation")
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    if show:
        plt.show()
    return fig, ax


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

    # IMU data-path stalls, called out rather than left to the record counts:
    # a stall is the one thing in a dump that invalidates the IMU coverage
    # either side of it, and it is silent otherwise (the part keeps answering
    # SPI, so nothing else in the log looks wrong).
    health = df[df.record_type == "IMU_HEALTH"] if "IMU_HEALTH" in set(df.record_type) else df.iloc[0:0]
    if not health.empty:
        lines.append("")
        lines.append(f"IMU data-path health events ({len(health)}):")
        for _, row in health.iterrows():
            wall_time = row["wall_time"]
            wall_str = (wall_time.strftime("%Y-%m-%d %H:%M:%S")
                        if pd.notna(wall_time) else "time unknown")
            pwr = row.get("imu_pwr_mgmt0")
            pwr_str = "read failed" if pwr is None or pwr == 0xFF else (
                f"PWR_MGMT0=0x{int(pwr):02x} accel_mode={int(row['imu_accel_mode'])} "
                f"gyro_mode={int(row['imu_gyro_mode'])}")
            lines.append(f"  {wall_str}  {row['imu_health_event']:<16} {pwr_str}")

    anchors = df[df.record_type == "TIME_ANCHOR"]
    lines.append("")
    lines.append(f"Time anchors ({len(anchors)}):")
    prev_wall = None
    for _, row in anchors.iterrows():
        wall_time = row["wall_time"]
        wall_str = wall_time.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(wall_time) else "invalid"
        # The gap to the previous anchor is the cheapest health check there is:
        # the firmware writes one every ANCHOR_INTERVAL_SEC (300 s), so
        # anything else is a reboot, a gap in logging, or a damaged interval.
        gap = ""
        if pd.notna(wall_time) and prev_wall is not None:
            delta = (wall_time - prev_wall).total_seconds()
            gap = f"  (+{delta:.0f}s)" if delta >= 0 else f"  (BACKWARDS {delta:.0f}s)"
        if pd.notna(wall_time):
            prev_wall = wall_time
        lines.append(f"  seq={int(row['seq']):>6}  t={row['seconds_since_boot']:.3f}s  "
                     f"wall={wall_str}  valid={row['time_valid']}{gap}")

    lines.append("")
    logged_duration = capture_duration(df)
    n_segments = df["segment"].nunique()
    n_boots = int(df["boot"].nunique())

    first, last = capture_wall_span(df)
    if first is not None:
        lines.append(f"Wall clock: {first:%Y-%m-%d %H:%M:%S} .. {last:%Y-%m-%d %H:%M:%S}")
        lines.append(f"Captured duration: {logged_duration:.3f} s ({_format_hms(logged_duration)})  "
                     f"[union of {n_segments} anchor interval(s), real time]")
    else:
        lines.append("Wall clock: unavailable — every anchor has time_valid=0 "
                     "(RTC never set), so all times below are device uptime")
        lines.append(f"Logged duration: {logged_duration:.3f} s ({_format_hms(logged_duration)})  "
                     f"[summed over {n_segments} anchor segment(s)]")

    if "time_rescaled" in df.columns:
        rescaled = int(df["time_rescaled"].sum())
        if rescaled:
            affected = int(df.loc[df["time_rescaled"], "segment"].nunique())
            lines.append(f"  WARNING: {rescaled} record(s) in {affected} interval(s) "
                         f"accumulated more time than their anchors allow and were "
                         f"rescaled to fit — that interval's log is damaged")
    if n_boots > 1:
        # Segments alone are NOT evidence of a discontinuity — the firmware
        # writes an anchor every 5 minutes, so a healthy capture has one per
        # 5 min. A tick count that goes backwards is the real signal, and that
        # is what the boot counter tracks.
        lines.append(f"  timebase restarts {n_boots - 1}x in this dump (reboot); "
                     f"durations are summed per segment, never across a restart")

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

    n_boots = int(df["boot"].nunique())
    if n_boots > 1:
        lines.append(f"Power cycles in this dump: {n_boots}  "
                      f"(detected from the tick count restarting — the firmware "
                      f"writes no RESET_MARKER)")

    lines.extend(_allocation_lines(df, logged_duration))
    lines.extend(_session_lines(df))

    return "\n".join(lines)


def _allocation_lines(df, total=None):
    """Time-allocation section for the header/summary reports."""
    alloc = time_allocation(df)
    if alloc.empty:
        return []

    total = capture_duration(df) if total is None else total
    lines = ["", f"Time allocation (of {_format_hms(total)} captured):"]
    for breakdown in ("wear", "activity"):
        rows = alloc[alloc.breakdown == breakdown]
        if rows.empty:
            continue
        lines.append(f"  by {breakdown}:")
        for _, row in rows.iterrows():
            lines.append(f"    {row['category']:<14} {_format_hms(row['seconds']):>12}  "
                         f"({row['pct']:5.1f}%)")
    return lines


def _session_lines(df):
    """Activity-session section for the header/summary reports."""
    sessions = session_table(df)
    if sessions.empty:
        return []

    lines = ["", f"Activity sessions ({len(sessions)}):"]
    for _, row in sessions.iterrows():
        wall = row["start_wall"]
        when = wall.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(wall) else f"t={row['start_s']:.1f}s"
        flag = "" if row["complete"] else "  [no STOP — duration is a lower bound]"
        lines.append(f"  boot {row['boot']} seq {row['session_seq']:<4} "
                     f"{row['activity']:<10} {when}  "
                     f"{_format_hms(row['duration_s']):>10}  "
                     f"{row['imu_samples']:>7} IMU samples{flag}")
        if row["complete"] and row["imu_samples"] == 0:
            # Not an error: wear detection gates NVS writes, so an off-wrist
            # session is a real span with nothing logged inside it. Say so
            # rather than leaving a zero to be read as a decode failure.
            lines.append("      (no IMU data inside this session — logging was "
                         "gated off, most likely off-wrist)")
    return lines


# ---------------------------------------------------------------------------
# Derived-artifact caching
# ---------------------------------------------------------------------------
# View Dump's two expensive phases — decode_dump() (~28% of wall time on a
# full dump) and the _data.txt export (~58%) — are both pure functions of the
# .bin plus this module's code. On a 283 MB dump that is ~10 minutes to
# recompute artifacts that already exist on disk, so a re-view reuses them.
#
# Freshness is mtime-based against TWO inputs: the dump itself (never
# rewritten in practice, so it mostly just anchors the comparison) and this
# source file. Keying on the decoder's own mtime is the point — editing a
# PAYLOAD_FMT or a tick constant here silently changes what every record
# decodes to, and an mtime check invalidates the caches automatically instead
# of serving rows produced by rules that no longer exist. There is no version
# constant to remember to bump.

_DECODER_SRC = os.path.abspath(__file__)

CACHE_SUFFIX = "_decoded.pkl"


def cache_path_for(dump_path):
    """Path of the cached DataFrame that goes with a .bin dump."""
    base, _ = os.path.splitext(dump_path)
    return base + CACHE_SUFFIX


def artifact_is_fresh(artifact_path, dump_path):
    """True if `artifact_path` exists and is newer than both the dump it was
    derived from and this decoder module. Any missing file means "not fresh"
    (recompute) rather than an error.
    """
    try:
        artifact_mtime = os.path.getmtime(artifact_path)
        newest_input = max(os.path.getmtime(dump_path),
                           os.path.getmtime(_DECODER_SRC))
    except OSError:
        return False
    return artifact_mtime >= newest_input


def load_cached_frame(dump_path):
    """Returns the cached decode of `dump_path`, or None if there isn't a
    usable one. A corrupt/half-written pickle (killed mid-save, pandas
    version change) is treated as a miss and logged, never raised — the
    caller's fallback is simply to decode again.
    """
    path = cache_path_for(dump_path)
    if not artifact_is_fresh(path, dump_path):
        return None
    try:
        return pd.read_pickle(path)
    except Exception:
        logger.warning("dump_decoder: ignoring unreadable decode cache %s", path,
                       exc_info=True)
        return None


def save_cached_frame(df, dump_path):
    """Pickles `df` next to its dump. Returns the path written, or None if the
    write failed — caching is an optimisation, so a full disk degrades View
    Dump back to recomputing rather than failing it. A partial file is removed
    so it can't later look fresh.
    """
    path = cache_path_for(dump_path)
    try:
        df.to_pickle(path)
        return path
    except Exception:
        logger.warning("dump_decoder: could not write decode cache %s", path,
                       exc_info=True)
        try:
            os.remove(path)
        except OSError:
            pass
        return None


def export_datastream(df, path, progress_callback=None, chunk_rows=20000):
    """Writes the full decoded record stream (one row per record, same
    columns as decode_dump()'s DataFrame) to a CSV-formatted text file.

    progress_callback: optional callable(rows_done, total_rows). Supplying it
    switches the write to chunk_rows-sized appends so a caller can drive a
    progress bar — this is the slowest phase of View Dump on a full dump
    (serializing ~144k rows costs more than decoding them), so it is the one
    that most needs to report. Without a callback it stays a single to_csv().
    """
    if progress_callback is None:
        df.to_csv(path, index=False, float_format="%.6f")
        return

    total = len(df)
    with open(path, "w", newline="") as f:
        for start in range(0, total, chunk_rows):
            chunk = df.iloc[start:start + chunk_rows]
            chunk.to_csv(f, index=False, float_format="%.6f", header=(start == 0))
            progress_callback(min(start + chunk_rows, total), total)
    if total == 0:
        progress_callback(0, 0)


def summarize(df):
    """One-line-per-type record count summary, for printing to the GUI prompt."""
    if df.empty:
        return "No records decoded."
    counts = df["record_type"].value_counts()
    lines = [f"{len(df)} records decoded, {df['page'].nunique()} page(s):"]
    for type_name, count in counts.items():
        lines.append(f"  {type_name}: {count}")
    logged_duration = capture_duration(df)
    lines.append(f"  logged duration: {logged_duration:.1f} s ({_format_hms(logged_duration)})")

    first, last = capture_wall_span(df)
    if first is not None:
        lines.append(f"  wall clock: {first:%Y-%m-%d %H:%M:%S} .. {last:%Y-%m-%d %H:%M:%S}")
    else:
        lines.append("  wall clock: unavailable (RTC never set — times are uptime)")

    sessions = session_table(df)
    if not sessions.empty:
        incomplete = int((~sessions["complete"]).sum())
        note = f", {incomplete} without a STOP" if incomplete else ""
        lines.append(f"  activity sessions: {len(sessions)}{note}")

    alloc = time_allocation(df)
    worn = alloc[(alloc.breakdown == "wear") & (alloc.category == "worn")]
    if not worn.empty:
        lines.append(f"  on-wrist: {_format_hms(float(worn['seconds'].iloc[0]))} "
                     f"({float(worn['pct'].iloc[0]):.1f}%)")
    return "\n".join(lines)
