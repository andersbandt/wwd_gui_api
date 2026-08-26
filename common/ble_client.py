#!/usr/bin/env python3
"""Host-side BLE client for the WWD-n watch.

Companion to common/device_protocol.py, which speaks the USB command protocol.
The split matches the firmware's: USB carries bulk (log dumps, ~84 KB/s), BLE
carries small things (live status, setting the clock).

Talks to BlueZ over D-Bus rather than using bleak, so it needs nothing beyond
python3-dbus and python3-gi, both already present. Do not "improve" this by
switching to bleak without checking it is installed.

Usage:
    python3 -m common.ble_client scan
    python3 -m common.ble_client status
    python3 -m common.ble_client set-time            # sets watch to host LOCAL time
    python3 -m common.ble_client watch --seconds 30  # live notifications

The watch advertises as "WWD-n". Pass --address to skip the name lookup.
"""

import argparse
import calendar
import struct
import sys
import time

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

BLUEZ = "org.bluez"
OM_IFACE = "org.freedesktop.DBus.ObjectManager"
PROP_IFACE = "org.freedesktop.DBus.Properties"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
CHRC_IFACE = "org.bluez.GattCharacteristic1"

DEVICE_NAME = "WWD-n"

# Must match src/ble/ble.c
UUID_SVC = "a7f30001-6b5d-4f2e-9c88-2d1f7e4a0b11"
UUID_STATUS = "a7f30002-6b5d-4f2e-9c88-2d1f7e4a0b11"
UUID_TIME = "a7f30003-6b5d-4f2e-9c88-2d1f7e4a0b11"

# struct wwd_status in src/ble/ble.c — __packed little-endian, so the C layout
# IS the wire format. 19 bytes, chosen to fit the default 23-byte ATT MTU.
STATUS_FMT = "<IhhhIBHBB"
STATUS_LEN = struct.calcsize(STATUS_FMT)
assert STATUS_LEN == 19, STATUS_LEN

# activity_id_t in src/activity/activity.h
ACTIVITY_NAMES = {0: "none", 1: "running"}

# Refuse to send anything the firmware would reject anyway (see write_time()
# in ble.c): a bogus early timestamp would set the clock to 1970 AND make
# rv3028_time_is_set() report false, silently reverting dumps to relative time.
MIN_EPOCH = 1735689600  # 2025-01-01T00:00:00Z


def local_wallclock_epoch(now=None):
    """Seconds value that, decoded as UTC, reads as LOCAL wall-clock time.

    *** This is deliberately NOT a real UTC epoch. Do not "fix" it. ***

    The watch has no concept of a timezone. rv3028 stores plain calendar
    fields, and the firmware turns whatever number we send into those fields
    with gmtime_r() (write_time(), ble.c). So the number on the wire is not a
    moment in time, it is a wall clock: send true UTC and the watch face reads
    UTC, which is what it used to do.

    Two visible consequences of getting this wrong, which is why it is worth a
    docstring:
      - the clock face shows the wrong time
      - the step badge's midnight rollover (steps_today(), main.c) fires at
        whatever midnight the RTC keeps, so a UTC clock rolls the day over in
        the local evening

    Using calendar.timegm() on a LOCAL struct_time does the shift and gets DST
    right for free, because timegm() reads the fields as if they were UTC --
    which is exactly the reinterpretation the firmware will perform.

    dump_decoder.py needs no matching change: it builds a naive datetime
    straight from the record's calendar fields and applies no conversion, so
    dumps simply render in local time now.
    """
    return calendar.timegm(time.localtime(now if now is not None else time.time()))


def _bus():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    return dbus.SystemBus()


def _managed(bus):
    om = dbus.Interface(bus.get_object(BLUEZ, "/"), OM_IFACE)
    return om.GetManagedObjects()


def _adapter_path(bus):
    for path, ifaces in _managed(bus).items():
        if ADAPTER_IFACE in ifaces:
            return path
    raise RuntimeError("no Bluetooth adapter found")


def find_device(bus, address=None, name=DEVICE_NAME, discover_secs=8):
    """Return the D-Bus path of the watch, scanning if it is not already known."""
    def look():
        for path, ifaces in _managed(bus).items():
            dev = ifaces.get(DEVICE_IFACE)
            if not dev:
                continue
            if address and str(dev.get("Address", "")).upper() == address.upper():
                return path
            if not address and str(dev.get("Alias", "")) == name:
                return path
        return None

    path = look()
    if path:
        return path

    adapter = dbus.Interface(bus.get_object(BLUEZ, _adapter_path(bus)), ADAPTER_IFACE)
    try:
        adapter.StartDiscovery()
    except dbus.DBusException:
        pass  # already discovering is fine
    deadline = time.time() + discover_secs
    try:
        while time.time() < deadline:
            path = look()
            if path:
                return path
            time.sleep(0.5)
    finally:
        try:
            adapter.StopDiscovery()
        except dbus.DBusException:
            pass
    return None


def connect(bus, dev_path, timeout=20):
    dev = dbus.Interface(bus.get_object(BLUEZ, dev_path), DEVICE_IFACE)
    props = dbus.Interface(bus.get_object(BLUEZ, dev_path), PROP_IFACE)

    if not bool(props.Get(DEVICE_IFACE, "Connected")):
        dev.Connect()

    # Connecting is not enough — characteristics only appear as D-Bus objects
    # once BlueZ has finished GATT discovery. Acting before ServicesResolved
    # is the classic source of "characteristic not found" flakiness.
    deadline = time.time() + timeout
    while time.time() < deadline:
        if bool(props.Get(DEVICE_IFACE, "ServicesResolved")):
            return dev
        time.sleep(0.25)
    raise TimeoutError("services never resolved")


def disconnect(bus, dev_path):
    try:
        dbus.Interface(bus.get_object(BLUEZ, dev_path), DEVICE_IFACE).Disconnect()
    except dbus.DBusException:
        pass


def find_chrc(bus, dev_path, uuid):
    for path, ifaces in _managed(bus).items():
        chrc = ifaces.get(CHRC_IFACE)
        if chrc and path.startswith(dev_path) and str(chrc.get("UUID", "")).lower() == uuid:
            return dbus.Interface(bus.get_object(BLUEZ, path), CHRC_IFACE)
    raise RuntimeError(f"characteristic {uuid} not found (is the firmware current?)")


def decode_status(raw):
    (uptime_s, batt_mv, imu_raw, soc_centi,
     steps, act_id, seq, worn, time_valid) = struct.unpack(STATUS_FMT, bytes(raw))
    return {
        "uptime_s": uptime_s,
        "batt_mv": batt_mv,
        # Same conversion the firmware uses. NOTE the divisor is under review:
        # the ICM-42670 datasheet's typical sensitivity is 126.9 LSB/degC, not
        # 128, and the sensor reads warm from self-heating anyway. See
        # imu_notes.md before trusting this as an absolute temperature.
        "imu_temp_c": imu_raw / 128.0 + 25.0,
        "imu_temp_raw": imu_raw,
        "soc_temp_c": soc_centi / 100.0,
        "steps": steps,
        "activity": ACTIVITY_NAMES.get(act_id, f"unknown_{act_id}"),
        "session_seq": seq,
        "worn": bool(worn),
        "time_valid": bool(time_valid),
    }


def print_status(s):
    print(f"  uptime      : {s['uptime_s']} s")
    print(f"  battery     : {s['batt_mv']} mV")
    print(f"  IMU die     : {s['imu_temp_c']:.2f} C  (raw {s['imu_temp_raw']})")
    print(f"  SoC die     : {s['soc_temp_c']:.2f} C")
    print(f"  delta       : {s['imu_temp_c'] - s['soc_temp_c']:+.2f} C  (IMU - SoC)")
    print(f"  steps       : {s['steps']}")
    print(f"  activity    : {s['activity']}" +
          (f"  seq={s['session_seq']}" if s['activity'] != "none" else ""))
    print(f"  worn        : {s['worn']}")
    print(f"  clock set   : {s['time_valid']}")


def cmd_scan(args):
    """Report whether the watch is ACTUALLY advertising right now.

    BlueZ caches devices it has ever seen, so a plain lookup happily reports
    "found" for a radio that has since been switched off — which is exactly
    what it did the first time this was used to check the BLE on/off toggle.
    Removing the cached object first makes a hit mean a genuine, fresh
    advertisement.
    """
    bus = _bus()

    cached = find_device(bus, args.address, discover_secs=0)
    if cached:
        try:
            adapter = dbus.Interface(bus.get_object(BLUEZ, _adapter_path(bus)),
                                     ADAPTER_IFACE)
            adapter.RemoveDevice(cached)
        except dbus.DBusException:
            pass  # connected or already gone; the scan below still stands

    path = find_device(bus, args.address, discover_secs=args.seconds)
    if not path:
        print(f"{DEVICE_NAME} not advertising (nothing seen in {args.seconds}s). "
              f"Powered off, or BLE toggled off in System Settings?")
        return 1
    props = dbus.Interface(bus.get_object(BLUEZ, path), PROP_IFACE)
    addr = props.Get(DEVICE_IFACE, "Address")
    try:
        rssi = int(props.Get(DEVICE_IFACE, "RSSI"))
        print(f"found {DEVICE_NAME} at {addr}  RSSI {rssi} dBm")
    except dbus.DBusException:
        print(f"found {DEVICE_NAME} at {addr}  (no RSSI reported)")
    return 0


def cmd_status(args):
    bus = _bus()
    path = find_device(bus, args.address)
    if not path:
        print("device not found"); return 1
    connect(bus, path)
    try:
        raw = find_chrc(bus, path, UUID_STATUS).ReadValue({})
        print_status(decode_status(raw))
    finally:
        if not args.stay:
            disconnect(bus, path)
    return 0


def cmd_set_time(args):
    # An explicit --epoch is sent verbatim; it exists for driving odd boundaries
    # (e.g. just before midnight, to test the step rollover) and must not move.
    if args.epoch and args.epoch < MIN_EPOCH:
        print(f"refusing to send {args.epoch}: before 2025, firmware would reject it")
        return 1

    bus = _bus()
    path = find_device(bus, args.address)
    if not path:
        print("device not found"); return 1
    connect(bus, path)
    try:
        chrc = find_chrc(bus, path, UUID_TIME)

        # Sample the clock HERE, immediately before the write -- not at the top
        # of this function.
        #
        # find_device() discovers for up to 8 s and connect() waits up to 20 s,
        # and in practice scan + connect + service resolution ran to 76 s on a
        # cold cache. Reading the host clock before all that sets the watch to
        # when the COMMAND STARTED rather than when the write LANDED, and the
        # device ends up that far behind -- measured at exactly 76 s on SN3.
        # Everything downstream inherits the error: TIME_ANCHOR, the dump time
        # axis, and the step badge's midnight rollover.
        epoch = args.epoch if args.epoch else local_wallclock_epoch()

        payload = struct.pack("<I", epoch)
        chrc.WriteValue([dbus.Byte(b) for b in payload], {})
        # gmtime() here is correct and not a bug: the value is a wall clock, so
        # rendering it as UTC shows exactly what the watch face will display.
        print(f"set clock to {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(epoch))} "
              f"local (wire value {epoch})")

        # Read back so the result is confirmed rather than assumed — but wait
        # first. time_valid in the status characteristic comes from a cache the
        # firmware refreshes on its ~9 s sensor tick (ble_publish_status), NOT
        # at read time. Reading immediately returns the PRE-WRITE value and
        # makes a successful set look like a failure; that is exactly what it
        # did on first run.
        #
        # Note this only proves the RTC now reports itself as set. The status
        # characteristic does not carry the wall clock, so it cannot confirm
        # the clock is set to the RIGHT time.
        settle = 11
        print(f"waiting {settle}s for the device status cache to refresh...")
        time.sleep(settle)
        s = decode_status(find_chrc(bus, path, UUID_STATUS).ReadValue({}))
        print(f"device reports clock set: {s['time_valid']}")
        if not s["time_valid"]:
            print("WARNING: clock still reports unset — did the write reach the device?")
            return 1
    finally:
        if not args.stay:
            disconnect(bus, path)
    return 0


def cmd_watch(args):
    """Subscribe to status notifications.

    UNVERIFIED as of 2026-08-25 — the firmware's notify path has never been
    exercised on hardware (nothing has ever enabled the CCC). Written because
    it was cheap; if streaming is ever wanted, this is the cheaper-on-air
    alternative to polling `status`. Expect to debug it the first time.
    """
    bus = _bus()
    path = find_device(bus, args.address)
    if not path:
        print("device not found"); return 1
    connect(bus, path)

    chrc = find_chrc(bus, path, UUID_STATUS)
    count = {"n": 0}

    def on_props(iface, changed, invalidated, sender_path=None):
        if iface != CHRC_IFACE or "Value" not in changed:
            return
        count["n"] += 1
        print(f"\n[notify #{count['n']}]")
        print_status(decode_status(changed["Value"]))

    bus.add_signal_receiver(on_props, dbus_interface=PROP_IFACE,
                            signal_name="PropertiesChanged",
                            path_keyword="sender_path")
    chrc.StartNotify()
    print(f"subscribed — watching {args.seconds}s (firmware pushes every 2 s)")

    loop = GLib.MainLoop()
    GLib.timeout_add_seconds(args.seconds, loop.quit)
    try:
        loop.run()
    finally:
        try:
            chrc.StopNotify()
        except dbus.DBusException:
            pass
        if not args.stay:
            disconnect(bus, path)

    print(f"\nreceived {count['n']} notification(s) in {args.seconds}s")
    return 0 if count["n"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--address", help="BD address, skips the name lookup")
    p.add_argument("--stay", action="store_true", help="leave the link connected on exit")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan"); s.add_argument("--seconds", type=int, default=8)
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("status"); s.set_defaults(func=cmd_status)

    s = sub.add_parser("set-time")
    s.add_argument("--epoch", type=int,
                   help="raw wire value, sent verbatim (default: host local wall clock)")
    s.set_defaults(func=cmd_set_time)

    s = sub.add_parser("watch"); s.add_argument("--seconds", type=int, default=20)
    s.set_defaults(func=cmd_watch)

    args = p.parse_args()
    try:
        return args.func(args)
    except (RuntimeError, TimeoutError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
