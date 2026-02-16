"""Base equipment service class with common connect/disconnect lifecycle.

Encapsulates the pattern currently duplicated across 5+ tabs:
    1. Look up equipment class from registry
    2. Instantiate driver with port/address
    3. Call test_conn() to validate
    4. Store on ClassController
    5. Save model preference to XML config
    6. Track active connection

The service handles business logic only. GUI updates (labels, status
indicators, frame re-initialization) remain the tab's responsibility.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from EEequipment.equipment_manager import COMMUNICATION_ERRORS


@dataclass
class ConnectionResult:
    """Returned by connect() so the tab knows what happened without
    needing to poke at driver internals."""
    success: bool
    device_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None


class EquipmentService:
    """Abstract base for per-equipment services.

    Subclasses override:
        - `equipment_type`  : str used by get_instruments() ("dmm", "ps", etc.)
        - `usage_name`      : str key for ports_used.xml ("DMM_Serial", "PS_PyVISA", etc.)
        - `_store_on_controller(instance)` : calls the correct cc.set_xxx()
        - `_clear_from_controller()`       : sets cc.xxx = None
        - `_get_from_controller()`         : returns cc.xxx
        - `_post_connect(instance)`        : optional device-specific init after test_conn()
    """

    equipment_type: str = ""       # override in subclass
    usage_name: str = ""           # override in subclass
    connect_delay: float = 0       # seconds to wait after instantiation before test_conn

    def __init__(self, controller, registry=None):
        """
        Args:
            controller: ClassController instance (shared equipment state)
            registry: dict of {model_name: EquipmentClass} from get_instruments().
                      If None, the tab must pass it later or the subclass loads it.
        """
        self.cc = controller
        self.registry = registry or {}

    def set_registry(self, registry):
        """Allow setting or updating the registry after construction."""
        self.registry = registry

    def connect(self, port, model_name):
        """Full connect lifecycle: instantiate, test, store, persist.

        Args:
            port: Port string (e.g. "COM3", "ASRL3::INSTR", "/dev/ttyUSB0")
            model_name: Key into self.registry (e.g. "SPD3303X", "XDM1041")

        Returns:
            ConnectionResult with success flag, device_id, and any error info.
        """
        # --- validate inputs ---
        if model_name not in self.registry:
            return ConnectionResult(
                success=False,
                error=f"Unknown model '{model_name}'. Available: {list(self.registry.keys())}"
            )

        # --- check port conflict ---
        is_active, used_by = self.cc.is_port_active(port)
        if is_active and used_by != self.usage_name:
            return ConnectionResult(
                success=False,
                error=f"Port {port} is already in use by {used_by}"
            )

        # --- instantiate driver ---
        equipment_class = self.registry[model_name]
        try:
            instance = equipment_class(port)
        except Exception as e:
            return ConnectionResult(
                success=False,
                error=f"Failed to instantiate {model_name} on {port}: {e}"
            )

        # --- optional delay before test ---
        if self.connect_delay > 0:
            import time
            time.sleep(self.connect_delay)

        # --- test connection ---
        try:
            device_id = instance.test_conn()
        except COMMUNICATION_ERRORS as e:
            return ConnectionResult(
                success=False,
                error=f"Communication error during test_conn: {e}"
            )
        except Exception as e:
            return ConnectionResult(
                success=False,
                error=f"Unexpected error during test_conn: {e}"
            )

        if not device_id:
            return ConnectionResult(
                success=False,
                error=f"Device at {port} does not respond (empty ID)"
            )

        # --- success: store and persist ---
        self._store_on_controller(instance)
        self.cc.set_used_port(port, self.usage_name)
        self.cc.set_used_model(model_name, self.usage_name)
        self.cc.add_active_connection(port, self.usage_name)

        # --- device-specific post-connect ---
        post_error = self._post_connect(instance)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        return ConnectionResult(
            success=True,
            device_id=device_id,
            error=post_error,  # None unless post_connect had a non-fatal issue
            timestamp=timestamp,
        )

    def disconnect(self):
        """Disconnect the equipment and clean up controller state.

        Returns:
            ConnectionResult indicating success or any error during disconnect.
        """
        instance = self._get_from_controller()
        if instance is None:
            return ConnectionResult(success=True)  # already disconnected

        # find and remove active connection by usage name
        for port, usage in self.cc.get_active_connections().items():
            if usage == self.usage_name:
                self.cc.remove_active_connection(port)
                break

        try:
            instance.disconnect()
        except COMMUNICATION_ERRORS as e:
            self._clear_from_controller()
            return ConnectionResult(
                success=False,
                error=f"Error during disconnect: {e}"
            )

        self._clear_from_controller()
        return ConnectionResult(success=True)

    # --- hooks for subclasses ---

    def _store_on_controller(self, instance):
        """Store the driver instance on the ClassController. Override in subclass."""
        raise NotImplementedError

    def _clear_from_controller(self):
        """Clear the driver reference on the ClassController. Override in subclass."""
        raise NotImplementedError

    def _get_from_controller(self):
        """Return the current driver instance from the ClassController. Override in subclass."""
        raise NotImplementedError

    def _post_connect(self, instance):
        """Optional device-specific initialization after a successful connection.

        Override in subclass to perform things like turning outputs off,
        setting sample speed, querying channel count, etc.

        Returns:
            None on success, or a warning string for non-fatal issues.
        """
        return None
