#!/usr/bin/env python3
"""Step-by-step VISA / oscilloscope connection debugger.

Walks the same layers the OSC tab depends on, bottom-up, and stops at the first
one that fails with a hint about what to fix:

    1. VISA backends   -- which VISA libraries load (NI/IVI, pyvisa-py) and
                          which one master.ini makes the app use
    2. Resources       -- what each backend can see
    3. Network         -- for TCPIP addresses: are the VXI-11 / HiSLIP ports open
    4. Raw *IDN?       -- plain pyvisa open + query, no app code involved
    5. Driver connect  -- the app's own connect path (OscService + driver)
    6. Capture flow    -- (--capture) channels, a measurement, a screenshot, a
                          short waveform, then a real Capture into a run folder

    --trace (Tek scopes) runs between 4 and 5: the measurement and screenshot
    command sequences sent one raw command at a time with timings, BUSY? and
    the scope's event queue -- shows exactly which command hangs and why.

Examples:
    python scope_debug.py                                   # steps 1-2 only
    python scope_debug.py --address TCPIP0::10.44.176.100::inst0::INSTR
    python scope_debug.py --address USB0::0x0699::...::INSTR --capture
    python scope_debug.py --auto --capture --waveform       # first non-serial resource
    python scope_debug.py --address ... --backend @py       # try another backend
    python scope_debug.py --address ... --trace             # pinpoint a hang

Step 6 leaves the scope stopped (waveform reads stop it) and saves into
data/osc_data/debug_<timestamp> unless --run-dir is given.
"""

import argparse
import os
import re
import socket
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyvisa

TEK_VENDOR_ID = "0x0699"
NETWORK_PORTS = {111: "VXI-11 portmapper (inst0 addresses)",
                 4880: "HiSLIP (hislip0 addresses)",
                 4000: "raw socket (Tek ::4000::SOCKET addresses)"}


# ----------------------------------------------------------------- output ----

def header(title):
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def ok(msg):
    print(f"  [ OK ] {msg}")


def fail(msg, *hints):
    print(f"  [FAIL] {msg}")
    for hint in hints:
        print(f"         -> {hint}")


def info(msg):
    print(f"         {msg}")


def describe_backend(backend):
    return backend or "(blank: default IVI / NI-VISA)"


# ---------------------------------------------------------------- steps ----

def step_backends(app_backend):
    """Load every backend we care about. Returns {name: ResourceManager}."""
    header("1. VISA backends")
    info(f"Python {sys.version.split()[0]}, PyVISA {pyvisa.__version__}")
    info(f"backend under test = {describe_backend(app_backend)}  (master.ini [VISA], unless --backend)")

    app_key = app_backend or "@ivi"
    managers = {}
    for name in ("@ivi", "@py"):
        try:
            rm = pyvisa.ResourceManager(name)
        except Exception as e:
            reason = " ".join(str(e).split()) or type(e).__name__
            label = ("@ivi (NI-VISA / Keysight / TekVISA)" if name == "@ivi"
                     else "@py (pyvisa-py)")
            hint = ("Install NI-VISA or TekVISA to use it." if name == "@ivi"
                    else "pip install pyvisa-py")
            if name == app_key:
                fail(f"{label}: not available -- {reason}", hint)
            else:
                info(f"{label}: not installed (not used by the app, fine)")
            continue
        managers[name] = rm
        ok(f"{name}: {rm.visalib}")
        if name == "@py":
            _print_pyvisa_py_support(rm)

    if app_key not in managers:
        fail(f"The backend under test, {describe_backend(app_backend)}, "
             f"did not load, so the GUI can't see any VISA instrument.",
             "Change [VISA] backend in config/master.ini to one that loaded above.")
    return managers


def _print_pyvisa_py_support(rm):
    """pyvisa-py explains, per interface type, why it is or isn't usable."""
    try:
        debug = rm.visalib.get_debug_info()
    except Exception:
        return
    for key in ("USB INSTR", "TCPIP INSTR", "TCPIP SOCKET"):
        val = debug.get(key)
        if val is None:
            continue
        if isinstance(val, str) and val.strip().startswith("Available"):
            info(f"  {key:13s} available")
        else:
            lines = val if isinstance(val, list) else [val]
            info(f"  {key:13s} NOT available: {lines[-1].strip()}")
            if key == "USB INSTR":
                info("                -> for USB with @py: pip install libusb-package "
                     "(or use NI-VISA with a blank backend)")


def step_resources(managers, app_backend):
    header("2. Resources each backend can see")
    app_key = app_backend or "@ivi"
    found_any = False
    for name, rm in managers.items():
        try:
            resources = rm.list_resources("?*::INSTR") + rm.list_resources("?*::SOCKET")
        except Exception as e:
            fail(f"{name}: list_resources failed: {e}")
            continue
        tag = "  (app)" if name == app_key else ""
        if not resources:
            info(f"{name}{tag}: nothing found")
            continue
        found_any = True
        info(f"{name}{tag}:")
        for r in resources:
            flag = "  <- Tektronix" if TEK_VENDOR_ID in r.lower() else ""
            info(f"    {r}{flag}")
    if not found_any:
        fail("No backend lists any instrument.",
             "USB: is the scope on its rear USB-B (device) port and in Device Manager?",
             "LAN: list_resources only finds LAN scopes that answer discovery; "
             "pass --address TCPIP0::<ip>::inst0::INSTR directly.")
    info("Note: LAN instruments often don't show up here but still connect by address.")


def step_network(address):
    """For TCPIP addresses, check the host answers before blaming VISA."""
    m = re.match(r"TCPIP\d*::([^:]+)::", address, re.IGNORECASE)
    if not m:
        return True
    host = m.group(1)
    header(f"3. Network reachability ({host})")
    any_open = False
    for port, what in NETWORK_PORTS.items():
        try:
            with socket.create_connection((host, port), timeout=2):
                ok(f"port {port} open -- {what}")
                any_open = True
        except OSError as e:
            info(f"port {port} closed/unreachable -- {what} ({e.__class__.__name__})")
    if not any_open:
        fail(f"Nothing answers on {host}.",
             "Check the IP on the scope (Utility > I/O > LAN) and that this PC is "
             "on the same network/subnet.",
             "Try: ping " + host)
        return False
    if "inst0" in address.lower() and not _port_open(host, 111):
        fail("Address uses inst0 (VXI-11) but port 111 is closed.",
             f"Try TCPIP0::{host}::hislip0::INSTR instead.")
    return True


def _port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def step_raw_idn(rm, address, timeout_ms):
    header("4. Raw open + *IDN? (no app code)")
    try:
        t0 = time.monotonic()
        inst = rm.open_resource(address)
        ok(f"opened in {time.monotonic() - t0:.2f}s via {rm.visalib}")
    except Exception as e:
        fail(f"open_resource failed: {type(e).__name__}: {e}",
             "Address typo? Copy it exactly from step 2.",
             "USB + @py: the Windows USBTMC driver blocks pyvisa-py; use NI-VISA.",
             "Already open in another program (TekScope, NI MAX test panel, the GUI)?")
        return False
    try:
        inst.timeout = timeout_ms
        inst.read_termination = "\n"
        inst.write_termination = "\n"
        t0 = time.monotonic()
        idn = inst.query("*IDN?").strip()
        ok(f"*IDN? -> {idn}  ({(time.monotonic() - t0) * 1000:.0f} ms)")
        return True
    except Exception as e:
        fail(f"*IDN? failed: {type(e).__name__}: {e}",
             "Opened but no reply: wrong termination, wrong protocol (try hislip0 / "
             "::4000::SOCKET), or the scope's remote interface is disabled.")
        return False
    finally:
        try:
            inst.close()
        except Exception:
            pass


def step_driver_connect(address, model):
    header(f"5. App connect path (OscService + {model} driver)")
    from EEequipment import equipment_manager
    from class_controller import ClassController

    registry = equipment_manager.get_instruments("osc")
    if model not in registry:
        fail(f"Unknown model '{model}'. Available: {sorted(registry)}")
        return None
    controller = ClassController()
    service = controller.osc_service
    service.set_registry(registry)

    t0 = time.monotonic()
    result = service.connect(address, model)
    if not result.success:
        fail(f"connect failed: {result.error}",
             "Step 4 passed but this failed: the driver's config.ini settings "
             "(timeout / terminations) or its connect test query are the suspects.")
        return None
    ok(f"connected in {time.monotonic() - t0:.2f}s: {result.device_id}")
    if result.error:
        info(f"warning: {result.error}")
    return service


def step_capture(service, run_dir, with_waveform):
    header("6. Capture flow")
    scope = service.cc.osc
    failures = 0

    try:
        channels = scope.get_enabled_channels()
    except Exception as e:
        fail(f"get_enabled_channels: {e}")
        return 1
    if not channels:
        fail("No channels are displayed on the scope.", "Turn on at least one channel.")
        return 1
    ok(f"enabled channels: {channels}")
    ch = channels[0]

    try:
        t0 = time.monotonic()
        vpp = scope.measure("vpp", ch)
        ok(f"CH{ch} Vpp = {vpp}  ({(time.monotonic() - t0) * 1000:.0f} ms)")
    except Exception as e:
        failures += 1
        fail(f"measurement failed: {type(e).__name__}: {e}")
        _try_recover(scope)

    try:
        t0 = time.monotonic()
        image = scope.get_screenshot()
        fmt = scope.detect_image_format(image)
        complete = fmt != "png" or image.rstrip().endswith(b"IEND\xaeB`\x82")
        if fmt and complete:
            ok(f"screenshot: {len(image)} bytes {fmt} ({time.monotonic() - t0:.1f}s)")
        else:
            failures += 1
            fail(f"screenshot bad: format={fmt}, complete={complete}, "
                 f"first bytes {image[:8]!r}")
    except Exception as e:
        failures += 1
        fail(f"screenshot failed: {type(e).__name__}: {e}")
        _try_recover(scope)

    try:
        n = 1000
        t0 = time.monotonic()
        wave = scope.get_waveform_data(ch, points=n, fmt="WORD")
        dt = time.monotonic() - t0
        ok(f"waveform CH{ch}: {len(wave['y'])} points in {dt:.2f}s "
           f"(dt={wave['preamble']['x_increment']:.3g}s, "
           f"y {min(wave['y']):.4g}..{max(wave['y']):.4g})")
        _estimate_full_record(scope, dt, n)
    except Exception as e:
        failures += 1
        fail(f"waveform read failed: {type(e).__name__}: {e}")
        _try_recover(scope)

    t0 = time.monotonic()
    result = service.capture(run_dir, "{prefix}_{n:03d}", {"prefix": "debug"},
                             save_waveform=with_waveform)
    elapsed = time.monotonic() - t0
    if result.success:
        ok(f"Capture '{result.name}' in {elapsed:.1f}s")
        for label, path in (("image", result.image_path), ("row", result.csv_path),
                            ("waveform", result.waveform_path)):
            if path:
                info(f"  {label:8s} {path}")
    else:
        failures += 1
        fail(f"Capture failed: {result.error}")
    for w in result.warnings:
        info(f"  warning: {w}")
    return failures


def _estimate_full_record(scope, seconds, points):
    """Rough time for a full-record download, from the short one just done."""
    try:
        record = int(float(scope.conn.query(scope._cmd("acq_get_points"))))
    except Exception:
        return
    if record > points:
        est = seconds * record / points
        info(f"  full record is {record:,} points -> roughly {est:.0f}s per channel "
             f"for 'Waveform data' (overhead makes small reads look slow)")


def _try_recover(scope):
    try:
        scope.recover()
    except Exception:
        pass


# ------------------------------------------------------------- trace ----

class _Tracer:
    """Send Tek commands one at a time, timing each, and log what happens.

    Plain pyvisa, no app code, so a hang here is the scope or VISA -- not the
    driver's locking or retry logic.
    """

    def __init__(self, inst):
        self.inst = inst
        self.first_failure = None

    def _run(self, label, fn):
        t0 = time.monotonic()
        try:
            result = fn()
        except Exception as e:
            ms = (time.monotonic() - t0) * 1000
            print(f"  [FAIL] {label:52s} {ms:6.0f} ms  {type(e).__name__}: {e}")
            if self.first_failure is None:
                self.first_failure = label
            try:
                self.inst.clear()        # drop any half-sent reply
            except Exception:
                pass
            return None
        ms = (time.monotonic() - t0) * 1000
        shown = result if isinstance(result, str) else ""
        print(f"  [ OK ] {label:52s} {ms:6.0f} ms  {shown}")
        return result

    def write(self, cmd):
        return self._run(cmd, lambda: (self.inst.write(cmd), "")[1])

    def query(self, cmd):
        r = self._run(cmd, lambda: self.inst.query(cmd).strip())
        return r

    def query_raw(self, cmd):
        def go():
            saved = self.inst.read_termination
            self.inst.read_termination = None
            try:
                self.inst.write(cmd)
                return self.inst.read_raw()
            finally:
                self.inst.read_termination = saved
        data = self._run(cmd + "  (binary read)", go)
        if data is not None:
            kind = "PNG" if data.startswith(b"\x89PNG") else f"unknown, starts {data[:8]!r}"
            info(f"         got {len(data)} bytes, {kind}")
        return data

    def events(self):
        """Tek's event queue: where rejected commands and bad paths end up."""
        self.query("*ESR?")
        return self.query("ALLEv?")


def step_trace(rm, address, timeout_ms, screenshot_path):
    header("Trace: Tek command sequences, one command at a time")
    info(f"per-command timeout {timeout_ms} ms. The first [FAIL] is the culprit;")
    info("BUSY? = 1 means a Single acquisition is pending and *OPC? will hang.")
    try:
        inst = rm.open_resource(address)
    except Exception as e:
        fail(f"open_resource failed: {e}")
        return False
    inst.timeout = timeout_ms
    inst.read_termination = "\n"
    inst.write_termination = "\n"
    t = _Tracer(inst)

    try:
        print("\n  -- session state --")
        t.query("HEADer?")
        t.query("VERBose?")
        t.write("HEADer OFF")
        t.write("VERBose ON")
        t.query("ACQuire:STATE?")
        t.query("ACQuire:STOPAfter?")
        t.query("BUSY?")
        t.events()
        displayed = []
        for ch in range(1, 5):
            if t.query(f"DISplay:GLObal:CH{ch}:STATE?") == "1":
                displayed.append(ch)
        ch = displayed[0] if displayed else 1

        print(f"\n  -- measurement (CH{ch}, Vpp) --")
        listing = t.query("MEASUrement:LIST?") or ""
        used = [int("".join(c for c in n if c.isdigit()))
                for n in listing.split(",") if any(c.isdigit() for c in n)]
        slot = max(used) + 1 if used else 1
        t.write(f'MEASUrement:ADDNew "MEAS{slot}"')
        t.write(f"MEASUrement:MEAS{slot}:TYPe PK2PK")
        t.write(f"MEASUrement:MEAS{slot}:SOUrce CH{ch}")
        t.query("BUSY?")
        t.query("*OPC?")
        t.query(f"MEASUrement:MEAS{slot}:RESUlts:CURRentacq:MEAN?")
        t.events()
        t.write(f'MEASUrement:DELete "MEAS{slot}"')

        print("\n  -- screenshot --")
        t.write(f'SAVe:IMAGe "{screenshot_path}"')
        t.query("BUSY?")
        t.query("*OPC?")
        t.query_raw(f'FILESystem:READFile "{screenshot_path}"')
        t.write(f'FILESystem:DELEte "{screenshot_path}"')
        t.events()
    finally:
        try:
            inst.close()
        except Exception:
            pass

    if t.first_failure:
        fail(f"first failing command: {t.first_failure}",
             "Send me this whole trace output.")
        return False
    ok("every command in both sequences answered")
    return True


# ----------------------------------------------------------------- main ----

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--address", help="VISA resource string to test")
    parser.add_argument("--auto", action="store_true",
                        help="use the first non-serial resource the app's backend lists")
    parser.add_argument("--backend",
                        help="override master.ini, e.g. @py or @ivi (blank = default)")
    parser.add_argument("--model", default="MSO64", help="driver model (default MSO64)")
    parser.add_argument("--timeout", type=int, default=5000, help="raw query timeout, ms")
    parser.add_argument("--capture", action="store_true",
                        help="also run step 6 (measurement, screenshot, capture)")
    parser.add_argument("--waveform", action="store_true",
                        help="include full waveform data in the step-6 capture")
    parser.add_argument("--run-dir", help="where step 6 saves files")
    parser.add_argument("--trace", action="store_true",
                        help="send the Tek measurement/screenshot commands one by one")
    parser.add_argument("--trace-timeout", type=int, default=5000,
                        help="per-command timeout for --trace, ms (default 5000)")
    args = parser.parse_args()

    from services.config_service import ConfigService
    from common import path_helper
    from EEequipment.TestEquipment import set_visa_backend

    config = ConfigService()
    path_helper.init_config_service(config)
    backend = args.backend if args.backend is not None else config.get_visa_backend()
    # Make the app layers in steps 5-6 use the same backend as steps 1-4.
    set_visa_backend(backend)

    managers = step_backends(backend)
    step_resources(managers, backend)

    rm = managers.get(backend or "@ivi")
    address = args.address
    if not address and args.auto and rm is not None:
        candidates = [r for r in rm.list_resources() if not r.startswith("ASRL")]
        address = candidates[0] if candidates else None
        if address:
            info(f"--auto picked {address}")
    if not address:
        print("\nNo address to test. Re-run with --address <resource> (or --auto).")
        return 0
    if rm is None:
        print("\nThe configured backend didn't load; stopping before step 4.")
        return 1

    if not step_network(address):
        return 1
    if not step_raw_idn(rm, address, args.timeout):
        return 1
    if args.trace:
        from EEequipment.TestEquipment import get_registry
        try:
            shot = get_registry().get_command(args.model, "command", "screenshot_path")
        except Exception:
            shot = "C:/Temp.png"
        step_trace(rm, address, args.trace_timeout, shot)

    service = step_driver_connect(address, args.model)
    if service is None:
        return 1

    failures = 0
    try:
        if args.capture:
            run_dir = args.run_dir or path_helper.get_full_data_path(
                os.path.join("osc_data", "debug_" + datetime.now().strftime("%Y%m%d_%H%M%S")))
            failures = step_capture(service, run_dir, args.waveform)
    finally:
        service.disconnect()

    print("\n" + ("ALL STEPS PASSED" if not failures else f"{failures} STEP(S) FAILED"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
