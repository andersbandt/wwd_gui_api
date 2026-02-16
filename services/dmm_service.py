"""Service layer for Digital Multimeter operations."""

from services.equipment_service import EquipmentService, COMMUNICATION_ERRORS


class DMMService(EquipmentService):
    """Wraps DMM driver operations.

    Handles:
        - Connection lifecycle (connect, test, disconnect)
        - Sample speed configuration
        - Measurement reads with unit scaling

    Current tab usage this replaces (guiTab_2_DMM.py):
        - port_init (lines ~275-316)
        - port_close
        - Inline calls to self.cc.dmm.read_val(), set_sample_speed(), etc.
    """

    equipment_type = "dmm"
    usage_name = "DMM_Serial"
    connect_delay = 1  # DMM needs settling time before test_conn

    def _store_on_controller(self, instance):
        self.cc.set_dmm(instance)

    def _clear_from_controller(self):
        self.cc.set_dmm(None)

    def _get_from_controller(self):
        return self.cc.dmm

    def _post_connect(self, instance):
        """Set default sample speed after connecting."""
        try:
            instance.set_sample_speed("slow")
        except (*COMMUNICATION_ERRORS, AttributeError):
            return "Could not set default sample speed"
        return None

    # --- high-level operations ---

    def read_value(self):
        """Read current measurement from the DMM.

        Returns:
            tuple: (value_float, raw_string) or (None, error_string)
        """
        dmm = self._get_from_controller()
        if dmm is None:
            return (None, "DMM not connected")
        try:
            raw = dmm.read_val()
            return (float(raw), str(raw))
        except COMMUNICATION_ERRORS as e:
            return (None, f"Read error: {e}")
        except (ValueError, TypeError):
            return (None, f"Could not parse DMM response")

    def set_sample_speed(self, speed):
        """Set DMM sample speed.

        Args:
            speed: Speed string (e.g. "SLOW", "MED", "FAST")

        Returns:
            True on success, False on failure.
        """
        dmm = self._get_from_controller()
        if dmm is None:
            return False
        try:
            dmm.set_sample_speed(speed)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def get_status(self):
        """Check if DMM is connected and responsive."""
        return self.cc.get_dmm_status()
