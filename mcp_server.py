#!/usr/bin/env python3
"""MCP server — lab bench access for Claude Code.

Exposes PS, DMM, USB relay, USB-201 DAQ, USB serial, and GDB tools
so Claude Code can directly observe and control the embedded target
during a debug session.

Launch from repo root or register in ~/.claude/settings.json:
    {
      "mcpServers": {
        "lab": {
          "command": "python",
          "args": ["/home/anders/Documents/GitHub/wwd_gui_api/mcp_server.py"]
        }
      }
    }
"""

import atexit
import collections
import logging
import os
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET

# Make the repo importable regardless of where this server is launched from.
# App resources (config/, EEequipment/) resolve via common.path_helper, so no
# working-directory juggling is needed.
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _REPO_ROOT)

from mcp.server.fastmcp import FastMCP

from class_controller import ClassController
from common.path_helper import init_config_service, resolve_path
from common.serial_api import SerialGeneral, get_ports
from common.logging_session import LoggingSession
from common import logger as lgr, path_helper
from common.math_columns import MathColumn, MathConfig
from EEequipment.equipment_manager import get_instruments
from EEequipment.TestEquipment import set_visa_backend
from EEequipment.usbrelay.usbrelay_controller import USBRelayController
from EEequipment.usbrelay.usbrelay_controller import find as relay_find
from services.config_service import ConfigService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Wire in ConfigService and set PyVISA backend (@py) before any instrument connects
_config_svc = ConfigService()
init_config_service(_config_svc)
set_visa_backend(_config_svc.get_visa_backend())

mcp = FastMCP("lab")
cc = ClassController()

# Load equipment registries (needed before any service.connect() call)
cc.ps_service.set_registry(get_instruments("ps"))
cc.dmm_service.set_registry(get_instruments("dmm"))


# ── USB Relay (USB HID, no port address needed) ───────────────────────────────

_relay: USBRelayController | None = None
try:
    _dev = relay_find()
    if _dev is not None:
        _relay = USBRelayController(_dev)
        cc.set_relay(_relay)
        logger.info("Relay: %s (%d channels)", _relay.product, _relay.num_relays)
    else:
        logger.warning("USB relay not found")
except Exception as exc:
    logger.warning("Relay init failed: %s", exc)


# ── USB-201 DAQ (USB, no port address needed) ─────────────────────────────────

_daq = None
_daq_ai = None
try:
    from uldaq import (
        AiInputMode, AInFlag, DaqDevice, InterfaceType, Range,
        get_daq_device_inventory,
    )
    _inventory = get_daq_device_inventory(InterfaceType.USB)
    if _inventory:
        _daq = DaqDevice(_inventory[0])
        _daq.connect()
        _daq_ai = _daq.get_ai_device()
        logger.info("USB-201: %s", _inventory[0].product_name)
    else:
        logger.warning("USB-201 not found")
except Exception as exc:
    logger.warning("USB-201 init failed: %s", exc)


# ── Auto-connect PS / DMM from saved ports (ports_used.xml) ──────────────────

def _auto_connect() -> None:
    """Try to connect PS and DMM using ports and models saved from the last GUI session."""
    import time

    try:
        root = ET.parse(resolve_path("config", "ports_used.xml")).getroot()
    except Exception:
        logger.info("No ports_used.xml — skipping auto-connect")
        return

    for usage, svc in [("PS_PyVISA", cc.ps_service), ("DMM_Serial", cc.dmm_service)]:
        elem = root.find(usage)
        if elem is None:
            continue
        port = (elem.text or "").strip()
        model = (elem.get("model") or "").strip()
        if not port or not model:
            continue
        logger.info("Auto-connect %s: %s @ %s", usage, model, port)
        r = svc.connect(port, model)
        if r.success:
            logger.info("  OK: %s", r.device_id)
        else:
            # SPD3303X leaves stale USBTMC data that causes EOVERFLOW on the first
            # test_conn. The first attempt drains it; retry succeeds.
            logger.warning("  FAIL: %s — retrying once...", r.error)
            time.sleep(0.5)
            r = svc.connect(port, model)
            if r.success:
                logger.info("  OK (retry): %s", r.device_id)
            else:
                logger.warning("  FAIL (retry): %s", r.error)


_auto_connect()


# ── Logging session ───────────────────────────────────────────────────────────

_log_session: LoggingSession = LoggingSession(cc)


# ── USB Serial buffer ─────────────────────────────────────────────────────────

_serial: SerialGeneral | None = None
_serial_buf: collections.deque = collections.deque(maxlen=500)
_serial_lock = threading.Lock()


def _serial_reader() -> None:
    """Background thread: drain serial port into _serial_buf."""
    global _serial
    while True:
        s = _serial
        if s is None or not s.serStatus:
            break
        try:
            line = s.read_line()
            if line:
                with _serial_lock:
                    _serial_buf.append(line.decode("utf-8", errors="replace").rstrip())
        except Exception:
            break


# ── GDB / J-Link ─────────────────────────────────────────────────────────────

_GDB_SCRIPT = os.path.expanduser("~/Documents/NCS/WWD-n/debug/gdb_query.sh")


# ── Cleanup on exit ───────────────────────────────────────────────────────────

@atexit.register
def _cleanup() -> None:
    if cc.ps is not None:
        try:
            cc.ps.output_off(1)
            cc.ps.output_off(2)
            cc.ps.disconnect()
        except Exception:
            pass
    if cc.dmm is not None:
        try:
            cc.dmm.disconnect()
        except Exception:
            pass
    if _daq is not None:
        try:
            _daq.disconnect()
        except Exception:
            pass


# =============================================================================
# Tools
# =============================================================================

# ── Utility ───────────────────────────────────────────────────────────────────

@mcp.tool()
def get_status() -> dict:
    """Return connection status of all equipment."""
    daq_connected = False
    if _daq is not None:
        try:
            daq_connected = _daq.is_connected()
        except Exception:
            daq_connected = _daq_ai is not None

    return {
        "ps":     cc.get_ps_status(),
        "dmm":    cc.get_dmm_status(),
        "relay":  cc.get_relay_status(),
        "daq":    daq_connected,
        "serial": _serial is not None and _serial.serStatus,
    }


@mcp.tool()
def list_ports() -> list[str]:
    """List available serial ports on this machine."""
    return get_ports()


# ── Power Supply ──────────────────────────────────────────────────────────────

@mcp.tool()
def ps_connect(port: str, model: str) -> str:
    """Connect to power supply.

    Args:
        port:  VISA address, e.g. 'USB0::0xF4EC::0x1430::SPD3XGDX5R5XXX::INSTR'
        model: Equipment model key, e.g. 'SPD3303X'
    """
    r = cc.ps_service.connect(port, model)
    return f"Connected: {r.device_id}" if r.success else f"Failed: {r.error}"


@mcp.tool()
def ps_board_power(on: bool) -> str:
    """Toggle board power (PS channel 1). on=True enables output."""
    ok = cc.ps_service.output_on(1) if on else cc.ps_service.output_off(1)
    return "OK" if ok else "Failed — is PS connected?"


@mcp.tool()
def ps_output(channel: int, on: bool) -> str:
    """Enable or disable a specific PS output channel (1 or 2)."""
    ok = cc.ps_service.output_on(channel) if on else cc.ps_service.output_off(channel)
    return "OK" if ok else "Failed"


@mcp.tool()
def ps_set_voltage(channel: int, volts: float) -> str:
    """Set target voltage on a PS channel."""
    ok = cc.ps_service.set_voltage(channel, volts)
    return "OK" if ok else "Failed"


@mcp.tool()
def ps_set_current(channel: int, amps: float) -> str:
    """Set current limit on a PS channel."""
    ok = cc.ps_service.set_current(channel, amps)
    return "OK" if ok else "Failed"


@mcp.tool()
def ps_read_voltage(channel: int) -> str:
    """Read measured voltage on a PS channel."""
    v = cc.ps_service.read_voltage(channel)
    return f"{v:.4f} V" if v is not None else "Read failed"


@mcp.tool()
def ps_read_current(channel: int) -> str:
    """Read measured current on a PS channel."""
    i = cc.ps_service.read_current(channel)
    return f"{i:.6f} A" if i is not None else "Read failed"


# ── DMM ───────────────────────────────────────────────────────────────────────

@mcp.tool()
def dmm_connect(port: str, model: str) -> str:
    """Connect to DMM.

    Args:
        port:  Serial port, e.g. '/dev/ttyUSB0'
        model: Equipment model key, e.g. 'XDM1041'
    """
    r = cc.dmm_service.connect(port, model)
    return f"Connected: {r.device_id}" if r.success else f"Failed: {r.error}"


@mcp.tool()
def dmm_read() -> str:
    """Read the current measurement from the DMM. Returns value and raw string."""
    val, raw = cc.dmm_service.read_value()
    return f"{val} ({raw})" if val is not None else f"Error: {raw}"


@mcp.tool()
def dmm_set_rate(speed: str) -> str:
    """Set DMM measurement rate: 'slow', 'medium', or 'fast'."""
    ok = cc.dmm_service.set_rate(speed)
    return "OK" if ok else "Failed"


# ── USB Relay ─────────────────────────────────────────────────────────────────

@mcp.tool()
def relay_set(channel: int, state: bool) -> str:
    """Set a relay channel on or off.

    Args:
        channel: 1=ARDUINO, 2=na, 3=MICRO-USB, 4=FTDI_IC
        state:   True = relay closed/active, False = open/inactive
    """
    if _relay is None:
        return "Relay not connected"
    try:
        _relay.set_state(channel, int(state))
        label = _relay.relay_mapping.get(f"channel_{channel}", str(channel))
        return f"ch{channel} ({label}) -> {'ON' if state else 'OFF'}"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def relay_get_all() -> dict:
    """Get the state of all relay channels with their labels."""
    if _relay is None:
        return {"error": "Relay not connected"}
    out = {}
    for i in range(1, _relay.num_relays + 1):
        label = _relay.relay_mapping.get(f"channel_{i}", str(i))
        out[f"ch{i}_{label}"] = bool(_relay.get_state(i))
    return out


# ── USB-201 DAQ ───────────────────────────────────────────────────────────────

@mcp.tool()
def daq_read_channel(channel: int) -> str:
    """Read a single USB-201 analog input channel (0–7). Returns voltage in V."""
    if _daq_ai is None:
        return "DAQ not connected"
    try:
        v = _daq_ai.a_in(channel, AiInputMode.SINGLE_ENDED, Range.BIP10VOLTS, AInFlag.DEFAULT)
        return f"{v:.5f} V"
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def daq_read_all() -> dict:
    """Read all 8 USB-201 analog input channels. Returns {ch0..ch7: volts}."""
    if _daq_ai is None:
        return {"error": "DAQ not connected"}
    out = {}
    for ch in range(8):
        try:
            v = _daq_ai.a_in(ch, AiInputMode.SINGLE_ENDED, Range.BIP10VOLTS, AInFlag.DEFAULT)
            out[f"ch{ch}"] = round(v, 5)
        except Exception as exc:
            out[f"ch{ch}"] = f"error: {exc}"
    return out


# ── USB Serial (Zephyr console / target UART) ─────────────────────────────────

@mcp.tool()
def serial_connect(port: str, baud: int = 115200) -> str:
    """Open a serial port and start buffering output into a 500-line ring buffer.

    Args:
        port: e.g. '/dev/ttyUSB1'
        baud: baud rate (default 115200)
    """
    global _serial
    if _serial is not None:
        return "Already connected — call serial_disconnect first"
    try:
        _serial = SerialGeneral(port, baud)
        _serial_buf.clear()
        t = threading.Thread(target=_serial_reader, daemon=True)
        t.start()
        return f"Connected to {port} @ {baud}"
    except Exception as exc:
        _serial = None
        return f"Failed: {exc}"


@mcp.tool()
def serial_disconnect() -> str:
    """Close the serial port and stop buffering."""
    global _serial
    if _serial is None:
        return "Not connected"
    _serial.close()
    _serial = None
    return "Disconnected"


@mcp.tool()
def serial_read(n_lines: int = 50) -> list[str]:
    """Return the most recent N lines from the serial receive buffer (max 500)."""
    with _serial_lock:
        lines = list(_serial_buf)
    return lines[-n_lines:]


@mcp.tool()
def serial_send(data: str) -> str:
    """Send a string to the serial port. A newline is appended automatically."""
    if _serial is None:
        return "Not connected"
    try:
        _serial.send_data(data + "\n")
        return f"Sent: {data!r}"
    except Exception as exc:
        return f"Error: {exc}"


# ── Data Logging ──────────────────────────────────────────────────────────────

@mcp.tool()
def log_start(
    use_dmm: bool = False,
    use_ps: bool = False,
    ps_channel: int = 1,
    ps_log_voltage: bool = True,
    ps_log_current: bool = True,
    interval_s: float = 1.0,
    suffix: str = "",
    live_plot: bool = False,
    math_columns: list[str] | None = None,
) -> str:
    """Start a timed data logging session writing to CSV in the data directory.

    Args:
        use_dmm:         Include DMM readings.
        use_ps:          Include power supply readings.
        ps_channel:      PS channel to log (1 or 2).
        ps_log_voltage:  Log PS set voltage and measured voltage.
        ps_log_current:  Log PS measured current.
        interval_s:      Seconds between samples (default 1.0).
        suffix:          Optional label appended after _MCP in the filename.
        live_plot:       If True, start a Dash live plot at http://127.0.0.1:8050.
        math_columns:    Optional list of "Name = expression" strings defining
                         computed columns evaluated after each sample.
                         Variables: DMM_Meas1, PS_Vset1, PS_Vmeas1, PS_Imeas1,
                         plus any previously defined math column names.
                         Functions: abs, round, sqrt, log, log10, exp, pow, min, max.
                         Example: ["Power_W = PS_Vmeas1 * PS_Imeas1",
                                   "Eff_pct = DMM_Meas1 / PS_Vmeas1 * 100"]

    Returns:
        CSV filename on success, or an error string.

    Example:
        log_start(use_dmm=True, use_ps=True, interval_s=2.0, suffix="boot_test",
                  math_columns=["Power_W = PS_Vmeas1 * PS_Imeas1"])
    """
    if _log_session.is_running:
        return "ERROR: session already running — call log_stop first"

    record_config = lgr.RecordConfig(
        use_dmm=use_dmm,
        use_ps=use_ps,
        ps_channel=ps_channel,
        ps_log_voltage=ps_log_voltage,
        ps_log_current=ps_log_current,
    )

    math_cfg = None
    if math_columns:
        cols = []
        for entry in math_columns:
            if "=" not in entry:
                return f"ERROR: invalid math column format (expected 'Name = expr'): {entry!r}"
            name, _, expr = entry.partition("=")
            name = name.strip()
            expr = expr.strip()
            if not name or not expr:
                return f"ERROR: invalid math column format (expected 'Name = expr'): {entry!r}"
            cols.append(MathColumn(name=name, expression=expr))
        math_cfg = MathConfig(columns=cols)

    save_dir = path_helper.get_full_data_path()
    filename = _log_session.start(
        record_config, interval_s, save_dir, suffix, live_plot, math_cfg
    )
    return filename


@mcp.tool()
def log_stop() -> dict:
    """Stop the active logging session.

    Returns:
        {"rows": n, "file": "/path/to/file.csv", "elapsed_s": t}
    """
    if not _log_session.is_running:
        return {"error": "No session running"}
    return _log_session.stop()


@mcp.tool()
def log_status() -> dict:
    """Return status of the current logging session without stopping it.

    Returns:
        {"running": bool, "rows": n, "file": path, "elapsed_s": t, "live_plot_url": ...}
    """
    return _log_session.status()


@mcp.tool()
def log_tail(n_rows: int = 10) -> list:
    """Return the last N rows collected in the current session (from memory, not disk).

    Args:
        n_rows: Number of recent rows to return (max 500).

    Returns:
        List of row dicts, e.g. [{"Time": "...", "DMM_Meas1": 3.301, ...}, ...]
    """
    return _log_session.tail(n_rows)


# ── GDB via J-Link GDB Server ─────────────────────────────────────────────────

@mcp.tool()
def gdb_query(commands: list[str], timeout_s: int = 30) -> str:
    """Run GDB commands against the live nRF52833 target via J-Link.

    Starts J-Link GDB server, connects arm-none-eabi-gdb in batch mode,
    executes all commands in order, then detaches. The ELF defaults to
    ~/Documents/NCS/WWD-n/build_n33/zephyr/zephyr.elf (set by the wrapper
    script, overridable there via the ELF env var).

    NOTE: JLinkGDBServer is launched without -noreset, so connecting RESETS
    the target. State that only occurs on a cold power-on cannot be observed
    this way — have the firmware print it instead.

    Args:
        commands: List of GDB command strings to execute.
        timeout_s: Seconds to wait. Raise well above the default when using
            breakpoints, since the run blocks until each one is hit.

    Examples:
        gdb_query(["p rtc_seconds"])
        gdb_query(["x/16wx 0x40004000"])
        gdb_query(["info threads", "bt"])
        gdb_query(["p/x *(NRF_SPIM_Type*)0x40004000"])
        gdb_query(["p my_struct.field_a", "p my_struct.field_b"])
    """
    if not commands:
        return "No commands provided"
    try:
        result = subprocess.run(
            ["/bin/bash", _GDB_SCRIPT] + commands,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        out = result.stdout
        if result.stderr:
            out += f"\n[stderr]:\n{result.stderr}"
        return out
    except subprocess.TimeoutExpired:
        return (
            f"Timeout after {timeout_s} s — is J-Link connected and target powered? "
            "If the commands set a breakpoint, raise timeout_s."
        )
    except FileNotFoundError:
        return f"GDB script not found: {_GDB_SCRIPT}"
    except Exception as exc:
        return f"Error: {exc}"


if __name__ == "__main__":
    mcp.run()
