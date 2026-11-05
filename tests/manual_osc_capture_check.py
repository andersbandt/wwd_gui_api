#!/usr/bin/env python3
"""Hardware check for the OSC capture flow. Not collected by pytest.

Everything the unit tests fake out -- a real VISA session, a real screenshot
transfer, real measurements -- is exercised here against a connected scope:

    python3 tests/manual_osc_capture_check.py                  # auto-detect
    python3 tests/manual_osc_capture_check.py --address USB0::...::INSTR
    python3 tests/manual_osc_capture_check.py --model MSO64

Read-only apart from one caveat: on InfiniiVision scopes each :MEASure query
adds a badge to the on-screen measurement list. Pass --clear-measurements to
wipe the list afterwards -- but that also removes measurements you set up by
hand, so it is off by default and the bench is otherwise left as found.
"""

import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyvisa

from EEequipment import equipment_manager
from EEequipment.TestEquipment import set_visa_backend
from class_controller import ClassController
from services.config_service import ConfigService


def find_scope_address(backend):
    """First VISA resource that is not a serial port."""
    rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
    candidates = [r for r in rm.list_resources() if not r.startswith("ASRL")]
    return candidates[0] if candidates else None


def _is_complete(data, fmt):
    """Truncation check, using whatever end-marker the format provides."""
    if fmt == "png":
        return data.rstrip().endswith(b"IEND\xaeB`\x82")
    if fmt == "bmp":
        # Bytes 2-6 of a BMP are the file size the scope says it is sending.
        declared = int.from_bytes(data[2:6], "little")
        return declared > 0 and len(data) >= declared
    return fmt is not None


def _completeness_detail(data, fmt):
    if fmt == "png":
        return "IEND chunk present"
    if fmt == "bmp":
        return (f"header declares {int.from_bytes(data[2:6], 'little')} bytes, "
                f"got {len(data)}")
    return ""


def check(step, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {step}" + (f" -- {detail}" if detail else ""))
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--address", help="VISA resource string (default: auto-detect)")
    parser.add_argument("--model", default="DSOX4104A", help="driver model name")
    parser.add_argument("--run-dir", help="capture folder (default: a temp dir)")
    parser.add_argument("--clear-measurements", action="store_true",
                        help="clear the scope's measurement list when done")
    args = parser.parse_args()

    set_visa_backend(ConfigService().get_visa_backend())

    address = args.address or find_scope_address(ConfigService().get_visa_backend())
    if not address:
        print("No non-serial VISA resource found. Is the scope powered and plugged in?")
        return 1

    registry = equipment_manager.get_instruments("osc")
    if args.model not in registry:
        print(f"Unknown model '{args.model}'. Available: {sorted(registry)}")
        return 1

    # The real controller, so this exercises the same connect path (port
    # tracking, ports_used.xml) the tab does rather than a stand-in.
    controller = ClassController()
    service = controller.osc_service
    service.set_registry(registry)

    print(f"Connecting to {args.model} at {address}")
    result = service.connect(address, args.model)
    if not result.success:
        print(f"  connect failed: {result.error}")
        return 1
    print(f"  {result.device_id}")

    scope = controller.osc
    failures = 0
    run_dir = args.run_dir or os.path.join(tempfile.mkdtemp(), "osc_check")

    try:
        enabled = scope.get_enabled_channels()
        failures += not check("get_enabled_channels", bool(enabled), f"channels {enabled}")
        if not enabled:
            print("\nEnable at least one channel on the scope, then re-run.")
            return 1

        measurements = scope.measure_all(enabled[0])
        got = {k: v for k, v in measurements.items() if v is not None}
        failures += not check("measure_all", bool(got),
                              f"{len(got)}/{len(measurements)} returned a value")

        image = scope.get_screenshot()
        fmt = scope.detect_image_format(image)
        failures += not check("get_screenshot returns an image", fmt is not None,
                              f"{len(image)} bytes, {fmt or 'unrecognised'}, "
                              f"header {image[:8]!r}")
        # A truncated transfer still looks valid at the front, so check the end
        # too -- this is what the read_termination fix guards against.
        failures += not check("screenshot is complete", _is_complete(image, fmt),
                              _completeness_detail(image, fmt))

        capture = service.capture(run_dir, "{prefix}_Vin{Vin}_{n:03d}",
                                  {"prefix": "hwcheck", "Vin": "12.0"})
        failures += not check("capture", capture.success, capture.error or capture.name)
        for warning in capture.warnings:
            print(f"         warning: {warning}")

        if capture.success:
            failures += not check("PNG written", bool(capture.image_path)
                                  and os.path.getsize(capture.image_path) > 0,
                                  capture.image_path or "")
            failures += not check("CSV row written", os.path.exists(capture.csv_path),
                                  capture.csv_path)

            second = service.capture(run_dir, "{prefix}_Vin{Vin}_{n:03d}",
                                     {"prefix": "hwcheck", "Vin": "13.5"})
            failures += not check("counter advances",
                                  second.success and second.index == capture.index + 1,
                                  f"{capture.name} -> {second.name}")

            print(f"\n  run folder: {run_dir}")
            with open(service.run_csv_path(run_dir)) as f:
                for line in f:
                    print("  " + line.rstrip())

        if args.clear_measurements:
            scope.measure_clear()
            print("\n  measurement list cleared")
        else:
            print("\n  Note: measure_all left measurement badges on the scope display."
                  "\n  Re-run with --clear-measurements to wipe them.")
    finally:
        service.disconnect()

    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
