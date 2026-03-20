"""Headless data logging session — no GUI dependencies.

Used by the MCP server to record instrument data to CSV independently
of the Tkinter GUI. Mirrors the core logic of guiTab_8_LOG without any
widget state.
"""

import collections
import logging
import os
import threading
import time

from common import logger as lgr
from common import path_helper
from common.csv_helper import CSVHelper
from common.math_columns import MathConfig, MathEvaluator

_log = logging.getLogger(__name__)


class LoggingSession:
    """Timed instrument recording session that writes to CSV.

    Usage::

        session = LoggingSession(cc)
        filename = session.start(record_config, interval_s=1.0, save_dir="...", suffix="MCP")
        ...
        result = session.stop()   # {"rows": n, "file": path, "elapsed_s": s}
    """

    def __init__(self, cc):
        self._cc = cc
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._csvh: CSVHelper | None = None
        self._record_config: lgr.RecordConfig | None = None
        self._interval_s: float = 1.0
        self._rows: int = 0
        self._filename: str | None = None
        self._start_time: float | None = None
        self._recent_rows: collections.deque = collections.deque(maxlen=500)
        self._lock = threading.Lock()
        self._bus = None          # Queue for live plot, or None
        self._live_state: dict = {}
        self._math_evaluator: MathEvaluator | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        record_config: lgr.RecordConfig,
        interval_s: float,
        save_dir: str,
        suffix: str = "",
        live_plot: bool = False,
        math_config: MathConfig | None = None,
    ) -> str:
        """Start recording. Returns the CSV filename (just the name, not full path).

        Args:
            record_config: Which instruments to sample.
            interval_s:    Seconds between samples.
            save_dir:      Directory to write the CSV into.
            suffix:        Extra text appended to the filename (after the MCP tag).
            live_plot:     If True, start a Dash live plot on port 8050.
            math_config:   Optional computed columns evaluated after each sample.

        Returns:
            CSV filename on success, or an error string if already running.
        """
        if self.is_running:
            return "ERROR: session already running — call log_stop first"

        self._record_config = record_config
        self._interval_s = interval_s
        self._stop_event.clear()
        self._rows = 0
        self._recent_rows.clear()
        self._bus = None
        self._math_evaluator = None

        # Validate and wire math columns before opening the CSV
        if math_config and not math_config.is_empty():
            evaluator = MathEvaluator(math_config)
            headers = lgr.build_headers(record_config)
            valid, err = evaluator.validate(headers)
            if not valid:
                return f"ERROR: math column validation failed — {err}"
            self._math_evaluator = evaluator

        # Build filename: prefix_TIMESTAMP_MCP[_suffix].csv
        prefix = path_helper.get_logger_prefix()
        mcp_suffix = f"MCP_{suffix}" if suffix else "MCP"
        filename, csvh_obj = lgr.setup_recording(
            save_dir, prefix, mcp_suffix, record_config,
            math_config=math_config if math_config and not math_config.is_empty() else None,
        )
        lgr.start_recording(csvh_obj)
        self._csvh = csvh_obj
        self._filename = os.path.join(save_dir, filename)
        self._start_time = time.monotonic()

        if live_plot:
            self._start_live_plot()

        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        _log.info("LoggingSession started: %s (%.1f s interval)", filename, interval_s)
        return filename

    def stop(self) -> dict:
        """Stop the recording thread and return a summary."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        elapsed = (
            round(time.monotonic() - self._start_time, 1)
            if self._start_time is not None
            else 0
        )
        _log.info("LoggingSession stopped: %d rows in %.1f s", self._rows, elapsed)
        return {"rows": self._rows, "file": self._filename, "elapsed_s": elapsed}

    def status(self) -> dict:
        """Return current session state without stopping."""
        elapsed = (
            round(time.monotonic() - self._start_time, 1)
            if self._start_time is not None
            else 0
        )
        result = {
            "running": self.is_running,
            "rows": self._rows,
            "file": self._filename,
            "elapsed_s": elapsed,
        }
        if self._bus is not None:
            result["live_plot_url"] = "http://127.0.0.1:8050"
        return result

    def tail(self, n: int = 10) -> list[dict]:
        """Return the last N collected rows (in-memory, not re-read from disk)."""
        with self._lock:
            rows = list(self._recent_rows)
        return rows[-n:]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _start_live_plot(self) -> None:
        from queue import Queue
        from common import plotter

        channels = []
        cfg = self._record_config
        if cfg.use_dmm:
            channels.append(lgr.COL_DMM_MEAS1)
        if cfg.use_ps:
            if cfg.ps_log_voltage:
                channels.extend([lgr.COL_PS_VSET1, lgr.COL_PS_VMEAS1])
            if cfg.ps_log_current:
                channels.append(lgr.COL_PS_IMEAS1)

        if self._math_evaluator is not None:
            channels += self._math_evaluator.config.get_column_names()

        if not channels:
            _log.warning("No channels for live plot — skipping")
            return

        self._bus = Queue(maxsize=4000)
        self._live_state = {}
        t = threading.Thread(
            target=plotter.start_live_plot,
            kwargs=dict(
                data_bus=self._bus,
                x_key=lgr.COL_TIME,
                channels=channels,
                buffer_size=3000,
                refresh_ms=500,
                x_label="Time",
                title="MCP Live Plot",
                port=8050,
                debug=False,
                state=self._live_state,
            ),
            daemon=True,
        )
        t.start()
        _log.info("Live plot started at http://127.0.0.1:8050")

    def _collect_data_row(self) -> dict:
        """Read one sample from each enabled instrument. No GUI state touched."""
        row = {lgr.COL_TIME: time.strftime("%Y-%m-%d %H:%M:%S")}
        cfg = self._record_config

        if cfg.use_dmm:
            val, _ = self._cc.dmm_service.read_value()
            row[lgr.COL_DMM_MEAS1] = val if val is not None else "ERROR"

        if cfg.use_ps:
            ch = cfg.ps_channel
            if cfg.ps_log_voltage:
                v_set = self._cc.ps_service.read_set_voltage(ch)
                v = self._cc.ps_service.read_voltage(ch)
                row[lgr.COL_PS_VSET1] = v_set if v_set is not None else "ERROR"
                row[lgr.COL_PS_VMEAS1] = v if v is not None else "ERROR"
            if cfg.ps_log_current:
                i = self._cc.ps_service.read_current(ch)
                row[lgr.COL_PS_IMEAS1] = i if i is not None else "ERROR"

        return row

    def _record_loop(self) -> None:
        while not self._stop_event.is_set():
            t_start = time.monotonic()

            try:
                row = self._collect_data_row()
                if self._math_evaluator is not None:
                    row.update(self._math_evaluator.evaluate_row(row))
            except Exception as exc:
                _log.error("LoggingSession: error collecting row: %s", exc)
                row = {lgr.COL_TIME: time.strftime("%Y-%m-%d %H:%M:%S")}

            if self._csvh is not None:
                self._csvh.add_row_from_dict(row)

            if self._bus is not None:
                try:
                    self._bus.put_nowait(row)
                except Exception:
                    pass  # bus full — drop

            with self._lock:
                self._recent_rows.append(row)
            self._rows += 1

            # Deadline-based sleep — honours stop_event for fast shutdown
            elapsed = time.monotonic() - t_start
            remaining = self._interval_s - elapsed
            if remaining > 0:
                self._stop_event.wait(remaining)
