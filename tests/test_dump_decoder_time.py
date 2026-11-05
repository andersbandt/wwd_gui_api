"""Wall-clock reconstruction in dump_decoder.

These build synthetic dumps rather than reading a capture off disk: the whole
point is to exercise the cases a healthy capture does NOT contain (a damaged
interval, a repeated log, a board whose RTC was never set), and a real dump
only has whichever of those it happens to have.
"""

import struct

import pandas as pd
import pytest

from common.dump_decoder import (PAGE_SIZE, TICKS_PER_SEC, capture_duration,
                                 capture_wall_span, decode_dump,
                                 dump_has_wall_time, dump_time_axis,
                                 wear_table)

HDR = "<HHH"
T_ANCHOR, T_IMU, T_WEAR = 0, 2, 7


def _rec(rtype, payload, dt_ticks=0):
    return struct.pack(HDR, rtype, len(payload), dt_ticks) + payload


def _anchor(raw_ticks, dt, valid=1):
    return _rec(T_ANCHOR, struct.pack("<IH6B", raw_ticks, dt.year, dt.month,
                                      dt.day, dt.hour, dt.minute, dt.second,
                                      valid))


def _imu(dt_ticks):
    return _rec(T_IMU, struct.pack("<6hH", 1, 2, 3, 4, 5, 6, 0), dt_ticks)


def _wear(worn, dt_ticks=0):
    return _rec(T_WEAR, struct.pack("<B", 1 if worn else 0), dt_ticks)


def _pages(records):
    """Packs records into pages, 0xFF-padding each page like erased NAND."""
    out = bytearray()
    page = bytearray()
    for rec in records:
        if len(page) + len(rec) > PAGE_SIZE:
            out += page + b"\xff" * (PAGE_SIZE - len(page))
            page = bytearray()
        page += rec
    if page:
        out += page + b"\xff" * (PAGE_SIZE - len(page))
    return bytes(out)


def _healthy(start=pd.Timestamp("2026-08-27 10:00:00"), intervals=2):
    """Anchors 300 s apart, with one IMU record per second between them."""
    recs = []
    for i in range(intervals + 1):
        t = start + pd.Timedelta(seconds=300 * i)
        recs.append(_anchor(int(300 * i * TICKS_PER_SEC), t))
        if i < intervals:
            recs += [_imu(TICKS_PER_SEC) for _ in range(299)]
    return recs


def test_healthy_capture_reports_real_wall_clock():
    df = decode_dump(_pages(_healthy()))

    assert dump_has_wall_time(df)
    assert dump_time_axis(df)[0] == "wall_time"

    first, last = capture_wall_span(df)
    assert first == pd.Timestamp("2026-08-27 10:00:00")
    assert last == pd.Timestamp("2026-08-27 10:10:00")

    # 600 s of anchors, and the duration is measured in real time.
    assert capture_duration(df) == pytest.approx(600, abs=2)
    assert not df["time_rescaled"].any()


def test_runaway_ticks_are_clamped_to_the_anchors():
    """A damaged interval must not invent time past its closing anchor.

    This is the bug that reported a dump ending on Aug 30 when its last anchor
    said Aug 27: corrupt records inject dt_ticks that never elapsed.
    """
    start = pd.Timestamp("2026-08-27 10:00:00")
    recs = [_anchor(0, start)]
    # 299 records claiming an hour each — three days of fiction inside a
    # 300-second interval.
    recs += [_imu(0xFFFF) for _ in range(299)]
    recs.append(_anchor(int(300 * TICKS_PER_SEC), start + pd.Timedelta(seconds=300)))

    df = decode_dump(_pages(recs))

    _, last = capture_wall_span(df)
    assert last == start + pd.Timedelta(seconds=300)
    assert df["time_rescaled"].any()
    assert capture_duration(df) == pytest.approx(300, abs=2)

    # Order is preserved even though the absolute times were compressed.
    imu = df[df.record_type == "IMU_FIFO"]
    assert imu["wall_time"].is_monotonic_increasing


def test_repeated_log_is_not_counted_twice():
    """A dump containing the same capture twice covers the same real time.

    Not hypothetical: a NAND geometry bug mirrored half the chip, and summing
    per-segment spans reported 101 hours for 15 hours of wall clock.
    """
    once = _pages(_healthy())
    twice = decode_dump(once + once)

    assert capture_duration(twice) == pytest.approx(600, abs=2)
    assert capture_duration(decode_dump(once)) == pytest.approx(600, abs=2)


def test_unset_rtc_falls_back_to_uptime():
    """A board with no working RTC still has to decode and still has to plot."""
    recs = [_anchor(0, pd.Timestamp("2000-01-01 00:00:00"), valid=0)]
    recs += [_imu(TICKS_PER_SEC) for _ in range(299)]

    df = decode_dump(_pages(recs))

    assert not dump_has_wall_time(df)
    assert dump_time_axis(df)[0] == "seconds_since_boot"
    assert capture_wall_span(df) == (None, None)
    assert capture_duration(df) == pytest.approx(299, abs=2)
    with pytest.raises(ValueError):
        dump_time_axis(df, prefer="wall")


def test_wear_span_is_measured_in_wall_clock():
    start = pd.Timestamp("2026-08-27 10:00:00")
    recs = [_anchor(0, start), _wear(True)]
    recs += [_imu(TICKS_PER_SEC) for _ in range(120)]
    recs.append(_wear(False))
    recs.append(_anchor(int(300 * TICKS_PER_SEC), start + pd.Timedelta(seconds=300)))

    wear = wear_table(decode_dump(_pages(recs)))

    worn = wear[wear.worn]
    assert len(worn) == 1
    assert worn.iloc[0]["duration_s"] == pytest.approx(120, abs=2)
    assert worn.iloc[0]["start_wall"] == start
