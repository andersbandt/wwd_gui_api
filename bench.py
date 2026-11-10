"""Bench playground: talk to one instrument with the app's own drivers, no GUI.

Edit the SETTINGS block below, then run one of:

    python bench.py       runs run(dev) below, then disconnects
    python -i bench.py    runs run(dev), then leaves you at a Python prompt
                          with `dev` still connected, e.g.
                              >>> dev.measure("vpp", 1)
                              >>> dev.query("*IDN?")
                          (exit() disconnects cleanly)

Not sure what to put in SETTINGS? Leave MODEL or ADDRESS as None and run it:
it prints the models for KIND and every address VISA can see.

For a step-by-step diagnosis of a scope that won't connect or hangs, use
scope_debug.py instead.
"""

# ============================== SETTINGS ====================================

KIND = "osc"            # "osc", "ps", "dmm" or "fg"
MODEL = "MSO64"         # driver class name; None = list the models for KIND
ADDRESS = None          # e.g. "USB0::0x0699::0x0530::C012345::INSTR" or "COM5";
                        # None = list what VISA can see
BACKEND = "config"      # "config" = same as the GUI (master.ini [VISA] backend)
                        # ""       = NI-VISA / TekVISA
                        # "@py"    = pyvisa-py
TIMEOUT_MS = None       # VISA timeout override; None = the driver's config.ini


def run(dev):
    """What to do once connected. Edit freely -- uncomment what you need.

    Files go to data/bench/ (see out()).
    """
    print("IDN:", dev.query("*IDN?").strip())

    # --- Oscilloscope ---
    # print("CH1 Vpp:", dev.measure("vpp", 1))
    # print("CH1 all:", dev.measure_all(1))           # names: dev.MEASUREMENTS
    # print("saved", dev.screenshot_to_file(out("shot.png")))
    # wave = dev.get_waveform_data(1, points=1000, fmt="WORD")   # stops the scope
    # print(len(wave["y"]), "points, dt =", wave["preamble"]["x_increment"])
    # dev.run()                                          # resume after a stop

    # --- Power supply ---
    # dev.set_voltage(3.3, channel=1)
    # dev.set_current(0.100, channel=1)
    # dev.output_on(1)
    # print("V:", dev.get_voltage(1), "I:", dev.get_current(1))
    # dev.output_off(1)

    # --- Multimeter ---
    # print("reading:", dev.read_value())

    # --- Function generator ---
    # dev.set_frequency(1000, channel=1)
    # dev.set_amplitude(1.0, channel=1)

    # --- Raw SCPI, any instrument ---
    # dev.write("*CLS")
    # print(dev.query("SYSTem:ERRor?"))


# ============================================================================
# Plumbing below -- no need to edit.

import atexit
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import path_helper
from services.config_service import ConfigService
from EEequipment import equipment_manager
from EEequipment.TestEquipment import set_visa_backend, get_visa_backend


def out(filename):
    """Path for an output file under data/bench/ (created if needed)."""
    return os.path.join(path_helper.get_full_data_path("bench"), filename)


def _list_visa_resources():
    import pyvisa
    backend = get_visa_backend()
    try:
        rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
        resources = rm.list_resources()
    except Exception as e:
        print(f"  VISA ({backend or 'NI-VISA/TekVISA'}) failed: {e}")
        return
    print(f"  VISA ({backend or 'NI-VISA/TekVISA'}) sees:")
    for r in resources or ["(nothing)"]:
        print("    " + r)


def _disconnect(dev):
    try:
        if hasattr(dev, "disconnect"):
            dev.disconnect()
        else:
            dev.conn.disconnect()
        print("disconnected")
    except Exception as e:
        print(f"disconnect failed: {e}")


def main():
    config = ConfigService()
    path_helper.init_config_service(config)
    set_visa_backend(config.get_visa_backend() if BACKEND == "config" else BACKEND)

    models = equipment_manager.get_instruments(KIND)
    if MODEL not in models or ADDRESS is None:
        if MODEL not in models:
            print(f"MODEL = {MODEL!r} isn't a {KIND!r} driver. Available:")
            for name in sorted(models):
                print("    " + name)
        if ADDRESS is None:
            print("ADDRESS is None. Set it to one of these (or a COM port):")
            _list_visa_resources()
        return None

    print(f"connecting to {MODEL} at {ADDRESS} "
          f"(backend: {get_visa_backend() or 'NI-VISA/TekVISA'})")
    dev = models[MODEL](ADDRESS)
    if not getattr(dev.conn, "status", False):
        print("connect failed -- see the log output above. "
              "For a step-by-step diagnosis: python scope_debug.py")
        return None
    if TIMEOUT_MS is not None and hasattr(dev.conn, "inst"):
        dev.conn.inst.timeout = TIMEOUT_MS

    atexit.register(_disconnect, dev)
    run(dev)
    return dev


if __name__ == "__main__":
    dev = main()
