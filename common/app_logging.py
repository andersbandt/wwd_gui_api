"""Application logging setup — call setup_logging() once from main.py."""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(level=logging.DEBUG, log_dir: str = "logs"):
    """Configure root logger with StreamHandler + RotatingFileHandler.

    Call once from main.py before anything else. Subsequent calls are no-ops
    (handlers are only added if the root logger has none yet).
    """
    root = logging.getLogger()
    if root.handlers:
        return  # Already configured

    root.setLevel(level)

    fmt_console = logging.Formatter("%(levelname)-8s %(name)-30s %(message)s")
    fmt_file = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)-30s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    sh = logging.StreamHandler()
    sh.setFormatter(fmt_console)
    root.addHandler(sh)

    # Rotating file handler
    Path(log_dir).mkdir(exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        Path(log_dir) / "wwd_gui.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt_file)
    root.addHandler(fh)
