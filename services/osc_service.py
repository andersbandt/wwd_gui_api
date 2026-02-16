"""Service layer for Oscilloscope operations."""

from services.equipment_service import EquipmentService, COMMUNICATION_ERRORS


class OscService(EquipmentService):
    """Wraps Oscilloscope driver operations.

    Handles:
        - Connection lifecycle
        - Channel enable/disable and coupling
        - Timebase and trigger configuration
        - Waveform data acquisition

    Current tab usage this replaces (guiTab_10_OSC.py):
        - port_init (lines ~559-597)
        - port_close
        - Inline calls to self.cc.osc.set_channel_state(), get_waveform(), etc.
    Also used by:
        - guiTab_8_LOG.py for oscilloscope data collection during recording
    """

    equipment_type = "osc"
    usage_name = "OSC_PyVISA"

    def _store_on_controller(self, instance):
        self.cc.set_osc(instance)

    def _clear_from_controller(self):
        self.cc.set_osc(None)

    def _get_from_controller(self):
        return self.cc.osc

    # --- high-level operations ---

    @property
    def channel_count(self):
        """Get the number of channels on the connected oscilloscope."""
        osc = self._get_from_controller()
        if osc is None:
            return 0
        return getattr(osc, 'channel_count', 4)

    def set_channel_state(self, channel, enabled):
        """Enable or disable a channel.

        Args:
            channel: Channel number (1-based)
            enabled: True to enable, False to disable

        Returns:
            True on success, False on failure.
        """
        osc = self._get_from_controller()
        if osc is None:
            return False
        try:
            osc.set_channel_state(channel, enabled)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def get_channel_state(self, channel):
        """Query whether a channel is enabled.

        Returns:
            bool or None on failure.
        """
        osc = self._get_from_controller()
        if osc is None:
            return None
        try:
            return osc.get_channel_state(channel)
        except COMMUNICATION_ERRORS:
            return None

    def set_timebase(self, scale):
        """Set the horizontal timebase scale.

        Args:
            scale: Time per division in seconds

        Returns:
            True on success, False on failure.
        """
        osc = self._get_from_controller()
        if osc is None:
            return False
        try:
            osc.set_timebase(scale)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def get_waveform(self, channel):
        """Acquire waveform data from a channel.

        Args:
            channel: Channel number (1-based)

        Returns:
            Waveform data (format depends on driver), or None on failure.
        """
        osc = self._get_from_controller()
        if osc is None:
            return None
        try:
            return osc.get_waveform(channel)
        except COMMUNICATION_ERRORS:
            return None

    def get_status(self):
        """Check if oscilloscope is connected and responsive."""
        return self.cc.get_osc_status()
