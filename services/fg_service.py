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
        except (*COMMUNICATION_ERRORS, AttributeError):
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

    def set_shape(self, shape):
        """Set waveform shape using the registry command.

        Args:
            shape: Waveform shape string (e.g. "SIN", "SQU", "RAMP")

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            cmd = fg.registry.get_command(fg.model, "command", "set_shape")
            cmd = cmd.format(value=shape)
            fg.write(cmd)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_frequency(self, value):
        """Set output frequency.

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.set_frequency(value)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_duty(self, value):
        """Set duty cycle percentage.

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.set_duty(value)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_amplitude(self, value):
        """Set output amplitude.

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.set_amplitude(value)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def set_offset(self, value):
        """Set DC offset.

        Returns:
            True on success, False on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return False
        try:
            fg.set_offset(value)
            return True
        except COMMUNICATION_ERRORS:
            return False

    def get_frequency(self):
        """Query current frequency from the device.

        Returns:
            str response or None on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return None
        try:
            cmd = fg.registry.get_command(fg.model, "command", "get_frequency")
            return fg.query(cmd)
        except COMMUNICATION_ERRORS:
            return None

    def get_shape(self):
        """Query current waveform shape from the device.

        Returns:
            str response or None on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return None
        try:
            cmd = fg.registry.get_command(fg.model, "command", "get_shape")
            return fg.query(cmd)
        except COMMUNICATION_ERRORS:
            return None

    def get_duty(self):
        """Query current duty cycle from the device.

        Returns:
            str response, "N/A" if command not in registry, or None on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return None
        try:
            cmd = fg.registry.get_command(fg.model, "command", "get_duty")
            return fg.query(cmd)
        except ValueError:
            return "N/A"
        except COMMUNICATION_ERRORS:
            return None

    def get_amplitude(self):
        """Query current amplitude from the device.

        Returns:
            str response, "N/A" if command not in registry, or None on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return None
        try:
            cmd = fg.registry.get_command(fg.model, "command", "get_amplitude")
            return fg.query(cmd)
        except ValueError:
            return "N/A"
        except COMMUNICATION_ERRORS:
            return None

    def get_offset(self):
        """Query current offset from the device.

        Returns:
            str response, "N/A" if command not in registry, or None on failure.
        """
        fg = self._get_from_controller()
        if fg is None:
            return None
        try:
            cmd = fg.registry.get_command(fg.model, "command", "get_offset")
            return fg.query(cmd)
        except ValueError:
            return "N/A"
        except COMMUNICATION_ERRORS:
            return None

    def get_status(self):
        """Check if FG is connected and responsive."""
        return self.cc.get_fg_status()
