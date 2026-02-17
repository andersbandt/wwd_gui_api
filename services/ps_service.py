"""Service layer for Power Supply operations."""

from services.equipment_service import EquipmentService, COMMUNICATION_ERRORS


class PSService(EquipmentService):
    """Wraps Power Supply driver operations.

    Handles:
        - Connection lifecycle with post-connect safety (outputs off)
        - Channel output control (on/off, voltage, current)
        - Status reads (voltage, current per channel)

    Current tab usage this replaces (guiTab_5_PS.py):
        - port_init (lines ~364-408)
        - port_close
        - Inline calls to self.cc.ps.output_on/off(), set_voltage(), etc.
    Also used by:
        - guiTab_8_LOG.py for stimulus control and data collection
        - guiTab_3_XDS110.py for target power sequencing
        - gui_driver.py shutdown sequence
    """

    equipment_type = "ps"
    usage_name = "PS_PyVISA"

    def _store_on_controller(self, instance):
        self.cc.set_ps(instance)

    def _clear_from_controller(self):
        self.cc.set_ps(None)

    def _get_from_controller(self):
        return self.cc.ps

    def _post_connect(self, instance):
        """Turn all outputs off after connecting (safety)."""
        try:
            instance.output_off(1)
            instance.output_off(2)
        except (*COMMUNICATION_ERRORS, AttributeError) as e:
            return f"Could not turn outputs off: {e}"
        return None

    # --- high-level operations ---

    @property
    def channel_count(self):
        """Get the number of channels on the connected PS."""
        ps = self._get_from_controller()
        if ps is None:
            return 0
        return getattr(ps, 'channel_count', 2)

    def output_on(self, channel):
        """Enable output on the given channel.

        Returns:
            True on success, False on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return False
        try:
            ps.output_on(channel)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def output_off(self, channel):
        """Disable output on the given channel.

        Returns:
            True on success, False on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return False
        try:
            ps.output_off(channel)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_voltage(self, channel, voltage):
        """Set voltage on the given channel.

        Returns:
            True on success, False on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return False
        try:
            ps.set_voltage(voltage, channel=channel)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_current(self, channel, current):
        """Set current limit on the given channel.

        Returns:
            True on success, False on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return False
        try:
            ps.set_current(current, channel=channel)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def read_voltage(self, channel):
        """Read measured voltage on the given channel.

        Returns:
            float or None on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return None
        try:
            return ps.get_voltage(channel)
        except COMMUNICATION_ERRORS:
            return None

    def read_current(self, channel):
        """Read measured current on the given channel.

        Returns:
            float or None on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return None
        try:
            return ps.get_current(channel)
        except COMMUNICATION_ERRORS:
            return None

    def read_set_voltage(self, channel):
        """Read the set (target) voltage on the given channel.

        Returns:
            float or None on failure.
        """
        ps = self._get_from_controller()
        if ps is None:
            return None
        try:
            return ps.get_set_voltage(channel)
        except COMMUNICATION_ERRORS:
            return None

    def get_status(self):
        """Check if PS is connected and responsive."""
        return self.cc.get_ps_status()

    def safe_shutdown(self):
        """Turn off all outputs then disconnect. Used during app shutdown."""
        ps = self._get_from_controller()
        if ps is None:
            return
        try:
            ps.output_off(1)
            ps.output_off(2)
        except COMMUNICATION_ERRORS:
            pass
        self.disconnect()
