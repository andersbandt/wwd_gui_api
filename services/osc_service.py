"""Service layer for Oscilloscope operations."""

import csv
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from common import capture_naming
from common import path_helper
from services.equipment_service import EquipmentService, COMMUNICATION_ERRORS

logger = logging.getLogger(__name__)

# Stop measuring a channel after this many failures in a row: a scope that has
# stopped answering costs a full timeout per attempt, and eleven of those turns
# one capture into a minute of dead air.
MAX_CONSECUTIVE_FAILURES = 3

@dataclass
class CaptureResult:
    """Outcome of one capture, so the tab can report without poking at files."""
    success: bool
    name: Optional[str] = None
    index: Optional[int] = None
    csv_path: Optional[str] = None
    image_path: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


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

    # --- capture ---

    @staticmethod
    def default_capture_root():
        """Parent directory that run folders are created under."""
        return path_helper.get_data_dir("osc_data")

    def preview_capture_name(self, template, fields, run_dir, model=None):
        """Render the name the next capture would get, without touching disk.

        Raises capture_naming.TemplateError for a bad template so the tab can
        show it live as the user types.
        """
        osc = self._get_from_controller()
        model = model or (getattr(osc, "model", "") if osc else "")
        index = capture_naming.next_index(self.run_csv_path(run_dir))
        return capture_naming.render(template, fields, index, model)

    @staticmethod
    def run_csv_path(run_dir):
        """The one CSV a run appends to, named after the run folder."""
        return os.path.join(run_dir, f"{os.path.basename(os.path.normpath(run_dir))}.csv")

    def capture(self, run_dir, template, fields, channels=None,
                save_image=True, save_measurements=True):
        """Record one capture: a row of measurements and, optionally, a PNG.

        Args:
            run_dir: folder for this run; created if missing.
            template: filename template (see common.capture_naming).
            fields: {name: value} the tech set for this capture. These become
                template tokens *and* CSV columns, so the filename and the row
                can never disagree about the conditions.
            channels: channel numbers to measure; None means whatever the
                scope currently has displayed.
            save_image: also pull a screenshot back from the scope.
            save_measurements: append the measurement row to the run CSV.

        Returns a CaptureResult. A screenshot failure degrades to a warning
        rather than losing the measurements that were already read.
        """
        osc = self._get_from_controller()
        if osc is None or not self.get_status():
            return CaptureResult(False, error="No OSC connection")

        warnings = []
        model = getattr(osc, "model", "")

        try:
            os.makedirs(run_dir, exist_ok=True)
            csv_path = self.run_csv_path(run_dir)
            index = capture_naming.next_index(csv_path)
            name = capture_naming.render(template, fields, index, model)
        except (capture_naming.TemplateError, OSError) as e:
            return CaptureResult(False, error=str(e))

        if channels is None:
            try:
                channels = osc.get_enabled_channels()
            except COMMUNICATION_ERRORS as e:
                return CaptureResult(False, error=f"Can't read channel states: {e}")
        if not channels:
            return CaptureResult(
                False, error="No channels enabled — nothing to measure")

        row = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "capture": name,
            "n": index,
            "model": model,
            "channels": " ".join(str(c) for c in channels),
        }
        row.update(fields or {})

        if save_measurements:
            for ch in channels:
                values, failed = self._measure_channel(osc, ch)
                for key, val in values.items():
                    row[f"CH{ch}_{key}"] = "" if val is None else val
                if failed:
                    warnings.append(
                        f"CH{ch}: {len(failed)}/{len(values)} measurements failed "
                        f"({', '.join(failed)})")

        image_path = None
        if save_image:
            try:
                # The extension is provisional: screenshot_to_file corrects it
                # to whatever the scope actually sent, so the name has to be
                # reserved across every image extension it might become.
                image_path = osc.screenshot_to_file(
                    capture_naming.unique_path(
                        os.path.join(run_dir, f"{name}.png"),
                        extensions=capture_naming.IMAGE_EXTENSIONS))
            except COMMUNICATION_ERRORS + (NotImplementedError, ValueError, OSError) as e:
                warnings.append(f"Screenshot failed: {e}")
                image_path = None

        if save_measurements:
            try:
                self._append_row(csv_path, row)
            except OSError as e:
                return CaptureResult(False, name=name, index=index,
                                     image_path=image_path,
                                     error=f"Can't write {csv_path}: {e}",
                                     warnings=warnings)
        else:
            csv_path = None

        return CaptureResult(True, name=name, index=index, csv_path=csv_path,
                             image_path=image_path, warnings=warnings)

    @staticmethod
    def _measure_channel(osc, channel):
        """Measure one channel, surviving individual measurement failures.

        Returns (values, failed_names). A single unsupported or timed-out
        measurement must not cost the other ten -- that is what emptied the
        run CSV of every measurement column on the DSO1014A, where one query
        used X-series syntax and simply never answered.

        Gives up on the rest of the channel after MAX_CONSECUTIVE_FAILURES in
        a row: at that point the scope is not answering at all, and each
        further attempt costs a full timeout.
        """
        values = {}
        failed = []
        consecutive = 0

        for name in osc.MEASUREMENTS:
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                values[name] = None
                failed.append(name)
                continue
            try:
                values[name] = osc.measure(name, channel)
                consecutive = 0
            except Exception as e:
                logger.warning(f"CH{channel} measurement '{name}' failed: "
                               f"{type(e).__name__}: {e}")
                values[name] = None
                failed.append(name)
                consecutive += 1
                # Resynchronise, or the failed query's reply is handed to the
                # next measurement and every value after it is off by one.
                try:
                    osc.recover()
                except Exception as recover_error:
                    logger.debug(f"recover() failed: {recover_error}")

        return values, failed

    @staticmethod
    def _append_row(csv_path, row):
        """Append a row, widening the header if this capture added a column.

        A tech who introduces a new field part-way through a run should not end
        up with a second CSV or a silently dropped column, so the file is
        rewritten with the union of the old and new headers when they differ.
        """
        existing_header = []
        existing_rows = []
        if os.path.exists(csv_path):
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                existing_header = reader.fieldnames or []
                existing_rows = list(reader)

        header = list(existing_header)
        for key in row:
            if key not in header:
                header.append(key)

        if header == existing_header:
            with open(csv_path, "a", newline="") as f:
                csv.DictWriter(f, fieldnames=header).writerow(row)
            return

        logger.info(f"Rewriting {csv_path} with widened header: {header}")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header, restval="")
            writer.writeheader()
            writer.writerows(existing_rows)
            writer.writerow(row)
