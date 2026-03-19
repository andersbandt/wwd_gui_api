"""Script runner for user-defined automation scripts.

Scripts are plain Python files in data/scripts/ with an execute() function.
They receive a ScriptContext exposing the services layer, a log callback,
and a check_stop callable for cooperative cancellation.

Scripts can also use StimulusGenerator for sweep value generation and
setup_recording / CSVHelper for structured data logging.
"""

import importlib.util
import logging
import os
import signal
import sys
import threading
import traceback
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)

_PORTS_XML = os.path.join("config", "ports_used.xml")


class ScriptStoppedError(Exception):
    """Raised by check_stop() when the user presses Stop."""
    pass


class _ScriptThread(threading.Thread):
    """Thread with a stop event for cooperative cancellation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class ScriptContext:
    """Namespace exposing equipment services to scripts.

    Scripts access equipment via:
        ctx.ps.set_voltage(1, 3.3)
        ctx.dmm.read_value()
        ctx.fg.set_frequency(1000)
        ctx.osc  (OscService)

    All methods are model-generic — they work with whatever equipment
    is currently connected through the GUI.
    """

    def __init__(self, controller):
        self.ps = controller.ps_service
        self.dmm = controller.dmm_service
        self.fg = controller.fg_service
        self.osc = controller.osc_service


class ScriptRunner:
    """Loads and executes user scripts in a _ScriptThread."""

    def __init__(self, controller, log_cb):
        """
        Args:
            controller: ClassController instance
            log_cb: Callable(str) to print messages to the GUI prompt.
                    Must be thread-safe (caller wraps with root.after()).
        """
        self.cc = controller
        self.log_cb = log_cb
        self.ctx = ScriptContext(controller)
        self._thread = None

    @staticmethod
    def list_scripts(scripts_dir):
        """Return list of .py files in the given directory.

        Args:
            scripts_dir: Path to scan for scripts

        Returns:
            list of filename strings (e.g. ["power_ramp.py", "sweep_test.py"])
        """
        if not os.path.isdir(scripts_dir):
            return []
        return sorted(
            f for f in os.listdir(scripts_dir)
            if f.endswith(".py") and not f.startswith("_")
        )

    @staticmethod
    def load_script(script_path):
        """Load a script module from a file path.

        Args:
            script_path: Full path to the .py file

        Returns:
            The loaded module

        Raises:
            FileNotFoundError: If script_path doesn't exist
            AttributeError: If the script has no execute() function
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")

        spec = importlib.util.spec_from_file_location("user_script", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not callable(getattr(module, "execute", None)):
            raise AttributeError(
                f"Script {os.path.basename(script_path)} must define an execute(ctx, log, check_stop) function"
            )

        return module

    def run(self, script_path):
        """Load and execute a script in a background thread.

        Args:
            script_path: Full path to the .py file

        Returns:
            True if the script thread was started, False on load error.
        """
        if self._thread is not None and self._thread.is_alive():
            self.log_cb("A script is already running.")
            return False

        try:
            module = self.load_script(script_path)
        except (FileNotFoundError, AttributeError) as e:
            self.log_cb(f"Script load error: {e}")
            return False

        script_name = os.path.basename(script_path)

        def _run_script():
            self.log_cb(f"--- Script started: {script_name} ---")
            try:
                result = module.execute(self.ctx, self.log_cb, self._check_stop)
                if result is not None:
                    self.log_cb(f"Script returned: {result}")
                self.log_cb(f"--- Script finished: {script_name} ---")
            except ScriptStoppedError:
                self.log_cb(f"--- Script stopped by user: {script_name} ---")
            except Exception:
                tb = traceback.format_exc()
                self.log_cb(f"--- Script error: {script_name} ---\n{tb}")
            finally:
                self._safe_shutdown()

        self._thread = _ScriptThread(target=_run_script, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Signal the running script to stop."""
        if self._thread is not None and self._thread.is_alive():
            self._thread.stop()
            self.log_cb("Stop signal sent.")

    def is_running(self):
        """Return True if a script is currently executing."""
        return self._thread is not None and self._thread.is_alive()

    def _check_stop(self):
        """Called by scripts to check if they should stop.

        Raises:
            ScriptStoppedError: If the stop button was pressed.
        """
        if self._thread is not None and self._thread.stopped():
            raise ScriptStoppedError()

    def _safe_shutdown(self):
        """Restore equipment to safe state after script ends."""
        try:
            self.ctx.ps.output_off(1)
            self.ctx.ps.output_off(2)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Standalone mode — run scripts from the terminal without the GUI
# ---------------------------------------------------------------------------

# Equipment type -> (service attribute on ClassController, registry key for get_instruments)
_EQUIPMENT_MAP = {
    "PS_PyVISA":  ("ps_service",  "ps"),
    "DMM_Serial": ("dmm_service", "dmm"),
    "FG_PyVISA":  ("fg_service",  "fg"),
    "OSC_PyVISA": ("osc_service", "osc"),
}


def _read_ports_xml():
    """Read ports_used.xml and return {usage_name: (port, model)} dict."""
    if not os.path.isfile(_PORTS_XML):
        return {}
    try:
        tree = ET.parse(_PORTS_XML)
        root = tree.getroot()
    except ET.ParseError:
        return {}

    entries = {}
    for child in root:
        usage = child.tag
        port = (child.text or "").strip()
        model = child.get("model", "").strip()
        if port and model:
            entries[usage] = (port, model)
    return entries


def _connect_equipment(controller, entries):
    """Connect equipment using ports_used.xml entries.

    Returns list of usage_names that connected successfully.
    """
    from EEequipment.equipment_manager import get_instruments

    connected = []
    for usage_name, (port, model) in entries.items():
        if usage_name not in _EQUIPMENT_MAP:
            continue

        service_attr, registry_key = _EQUIPMENT_MAP[usage_name]
        service = getattr(controller, service_attr)

        # Load registry for this equipment type
        registry = get_instruments(registry_key)
        service.set_registry(registry)

        if model not in registry:
            print(f"  [{usage_name}] model '{model}' not found in registry, skipping")
            continue

        print(f"  [{usage_name}] connecting {model} on {port}...")
        result = service.connect(port, model)
        if result.success:
            print(f"  [{usage_name}] connected: {result.device_id}")
            connected.append(usage_name)
        else:
            print(f"  [{usage_name}] failed: {result.error}")

    return connected


def standalone(script_file):
    """Run a script standalone from the terminal.

    Reads ports_used.xml for last-used equipment, connects, runs execute(),
    then shuts down. Ctrl+C triggers graceful stop.

    Usage in scripts:
        if __name__ == "__main__":
            from common.script_runner import standalone
            standalone(__file__)
    """
    # Ensure we're running from the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(script_file)))
    # Walk up until we find config/ports_used.xml or class_controller.py
    search = os.path.abspath(script_file)
    for _ in range(10):
        search = os.path.dirname(search)
        if os.path.isfile(os.path.join(search, "class_controller.py")):
            project_root = search
            break

    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.chdir(project_root)

    from class_controller import ClassController

    print(f"=== Standalone script: {os.path.basename(script_file)} ===")

    # Read saved equipment config
    entries = _read_ports_xml()
    if not entries:
        print("No saved equipment in config/ports_used.xml.")
        print("Connect equipment through the GUI first, then re-run.")
        sys.exit(1)

    print(f"Found {len(entries)} saved equipment entries:")
    for usage, (port, model) in entries.items():
        print(f"  {usage}: {model} @ {port}")

    # Set up controller and connect
    controller = ClassController()
    connected = _connect_equipment(controller, entries)

    if not connected:
        print("No equipment connected. Exiting.")
        sys.exit(1)

    print(f"\n{len(connected)} equipment connected. Running script...\n")

    # Build context
    ctx = ScriptContext(controller)
    stopped = threading.Event()

    def check_stop():
        if stopped.is_set():
            raise ScriptStoppedError()

    # Ctrl+C handler
    def _sigint(sig, frame):
        print("\nCtrl+C — stopping script...")
        stopped.set()

    signal.signal(signal.SIGINT, _sigint)

    # Load and run
    try:
        module = ScriptRunner.load_script(os.path.abspath(script_file))
        result = module.execute(ctx, print, check_stop)
        if result is not None:
            print(f"\nScript returned: {result}")
    except ScriptStoppedError:
        print("\nScript stopped by user.")
    except Exception:
        traceback.print_exc()
    finally:
        # Safe shutdown
        try:
            ctx.ps.output_off(1)
            ctx.ps.output_off(2)
        except Exception:
            pass
        controller.shutdown()
        print("=== Done ===")
