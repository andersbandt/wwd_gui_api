"""Service layer for Function Generator operations."""

from services.equipment_service import EquipmentService, COMMUNICATION_ERRORS


class FGService(EquipmentService):
    """Wraps Function Generator driver operations.

    Handles:
        - Connection lifecycle with output-off safety
        - Waveform configuration (shape, frequency, amplitude, offset, duty cycle)
        - Output enable/disable

    Current tab usage this replaces (guiTab_6_FG.py):
        - port_init (lines ~367-408)
        - port_close
        - Inline SCPI writes like self.cc.fg.write("OUTPut OFF")
        - Registry-based command formatting scattered through button callbacks
    Also used by:
        - guiTab_8_LOG.py for stimulus waveform control
    """

    equipment_type = "fg"
    usage_name = "FG_PyVISA"

    def _store_on_controller(self, instance):
        self.cc.set_fg(instance)

    def _clear_from_controller(self):
        self.cc.set_fg(None)

    def _get_from_controller(self):
        return self.cc.fg

    def _post_connect(self, instance):
        """Turn output off after connecting (safety)."""
        try:
            instance.write("OUTPut OFF")
        except (COMMUNICATION_ERRORS, AttributeError):
            # Some FGs may not support this command format
            return "Could not turn output off (may not be supported)"
        return None

    # --- high-level operations ---

    def output_on(self):
        """Enable function generator output.

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.write("OUTPut ON")
            return True
        except COMMUNICATION_ERRORS:
            return False

    def output_off(self):
        """Disable function generator output.

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.write("OUTPut OFF")
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_waveform(self, shape, frequency, amplitude, offset=0.0):
        """Configure waveform parameters.

        Args:
            shape: Waveform shape string (e.g. "SIN", "SQU", "RAMP")
            frequency: Frequency in Hz
            amplitude: Peak-to-peak amplitude in V
            offset: DC offset in V (default 0)

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.set_waveform(shape, frequency, amplitude, offset)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_duty_cycle(self, duty):
        """Set duty cycle for square wave.

        Args:
            duty: Duty cycle percentage (0-100)

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.set_duty_cycle(duty)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def get_status(self):
        """Check if FG is connected and responsive."""
        return self.cc.get_fg_status()
