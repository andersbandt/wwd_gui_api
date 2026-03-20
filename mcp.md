# MCP Server — Lab Bench Tool Access for Claude Code

## Goal

MCP server wrapping the existing instrument service layer so Claude Code can
directly read/control lab equipment during embedded development sessions.

```
Claude Code  ──MCP──  mcp_server.py
                           ├── ClassController
                           │     ├── cc.ps_service    → SPD3303X (PyVISA @py)
                           │     └── cc.dmm_service   → XDM1041 (serial)
                           ├── USBRelayController     → 4-ch USB relay (USB HID)
                           ├── USB-201 DAQ            → 8-ch analog input (uldaq)
                           ├── SerialGeneral          → /dev/ttyUSB* (Zephyr UART)
                           └── gdb_query.sh           → nRF52832 via J-Link + GDB
```

## Status: Operational

`mcp_server.py` exists at repo root. Confirmed working: PS + DMM auto-connect at startup, voltage set/readback verified (3.3 V → DMM reads 3.3011 V).

## Install

```bash
pip install mcp
```

Register in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "lab": {
      "command": "python",
      "args": ["/home/anders/Documents/GitHub/wwd_gui_api/mcp_server.py"]
    }
  }
}
```

## Permissions

To allow all lab tools without per-call prompts, add this to `.claude/settings.local.json`:

```json
"mcp__lab__*"
```

in the `permissions.allow` array. This covers all 21 tools in one rule.

## Startup Behavior

On launch the server:
1. Initializes `ConfigService` so the `@py` VISA backend is active (`config/master.ini [VISA] backend = @py`)
2. Connects USB relay (auto-discovered via USB HID, no port needed)
3. Connects USB-201 DAQ (auto-discovered via uldaq, no port needed)
4. Reads `config/ports_used.xml` and auto-connects PS + DMM to their last-used ports/models

## Tools

### Utility
| Tool | Description |
|---|---|
| `get_status()` | Connection status of all equipment |
| `list_ports()` | Enumerate available serial ports |

### Power Supply (SPD3303X)
| Tool | Description |
|---|---|
| `ps_connect(port, model)` | Connect (normally auto-connected at startup) |
| `ps_board_power(on)` | Channel 1 on/off — main board power toggle |
| `ps_output(channel, on)` | Any channel on/off |
| `ps_set_voltage(channel, volts)` | Set target voltage |
| `ps_set_current(channel, amps)` | Set current limit |
| `ps_read_voltage(channel)` | Read measured voltage |
| `ps_read_current(channel)` | Read measured current |

### DMM (XDM1041)
| Tool | Description |
|---|---|
| `dmm_connect(port, model)` | Connect (normally auto-connected at startup) |
| `dmm_read()` | Read current measurement (value + unit) |
| `dmm_set_rate(speed)` | `'slow'` / `'medium'` / `'fast'` |

### USB Relay (4-channel)
| Tool | Description |
|---|---|
| `relay_set(channel, state)` | ch1=ARDUINO, ch2=na, ch3=MICRO-USB, ch4=FTDI_IC |
| `relay_get_all()` | State of all channels with labels |

### USB-201 DAQ (8-channel analog input)
| Tool | Description |
|---|---|
| `daq_read_channel(channel)` | Read one channel (0–7), returns volts |
| `daq_read_all()` | Read all 8 channels at once |

### USB Serial (Zephyr UART console)
| Tool | Description |
|---|---|
| `serial_connect(port, baud)` | Open port, start 500-line ring buffer |
| `serial_disconnect()` | Close port |
| `serial_read(n_lines)` | Return last N lines from buffer |
| `serial_send(data)` | Write string to target (newline appended) |

**Log saving convention:** Save MCP serial captures to `data/text_data/TEXT_YYYYMMDDHHMMSS_MCP.log` (same directory as GUI logs, `_MCP` postfix distinguishes source).

### GDB (nRF52832 via J-Link)
| Tool | Description |
|---|---|
| `gdb_query(commands)` | Run list of GDB commands in batch mode |

`gdb_query` calls `~/Documents/NCS/WWD-n/debug/gdb_query.sh` which manages
the J-Link GDB server lifecycle automatically. ELF must be built at
`~/Documents/NCS/WWD-n/build/zephyr/zephyr.elf`.

Example:
```python
gdb_query(["p rtc_seconds", "p rtc_tick_hz"])
gdb_query(["x/16wx 0x40004000"])
gdb_query(["info threads", "bt"])
```

## SPD3303X Reconnect Procedure

The PS VISA address is **not stable** between sessions (serial number in the address changes). On reconnect:

1. Enumerate VISA resources to find the current address:
   ```bash
   python -c "import pyvisa; rm = pyvisa.ResourceManager('@py'); print(rm.list_resources())"
   ```
   Look for the `USB0::62700::5168::...` entry.

2. USB reset + 3s settle before connecting:
   ```bash
   python -c "import usb.core, time; usb.core.find(idVendor=62700, idProduct=5168).reset(); time.sleep(3)"
   ```

3. Call `ps_connect` — first attempt will get EOVERFLOW (drains stale USBTMC data), call again — second succeeds. If not, repeat step 2.

4. After reconnecting, always re-set voltage: `ps_set_voltage(channel=1, volts=3.3)`

## Known Issues

- **Live plot x-axis**: Dash live plot (`log_start(..., live_plot=True)`) starts and returns HTTP 200 but does not render data. Root cause: string `Time` column likely not parsed correctly as a time axis by Plotly. Workaround: use `log_tail()` for inline data inspection, or open the CSV after stopping.

## Design Notes

- **No Tkinter dependency** — `ClassController` and all services are GUI-independent
- **Working directory** — server `chdir`s to repo root at startup so all relative
  config paths (`config/ports_used.xml`, `EEequipment/usbrelay/config.ini`) resolve correctly
- **`xds110_api` excluded** — no XDS110 on this bench; add back if needed
- **Relay/DAQ auto-init** — discovered by USB enumeration, no port config required
- **Cleanup on exit** — `atexit` handler turns off PS outputs and disconnects equipment
