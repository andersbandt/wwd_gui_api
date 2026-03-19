"""Application logging setup — call setup_logging() once from main.py."""

import logging
import logging.handlers
from pathlib import Path
from colorlog import ColoredFormatter




def setup_logging(level=logging.DEBUG, log_dir: str = "logs"):
    """Configure root logger with StreamHandler + RotatingFileHandler.

    Call once from main.py before anything else. Subsequent calls are no-ops
    (handlers are only added if the root logger has none yet).
    """
    root = logging.getLogger()

    # If you want strict idempotency based on your own handlers, use a sentinel:
    # already_configured = any(getattr(h, "_app_logging", False) for h in root.handlers)
    # if already_configured:
    #     return
    if root.handlers:
        return  # Already configured by us or someone else

    root.setLevel(level)

    datefmt = "%Y-%m-%d %H:%M:%S"
    # Base format (no color tokens) for file logs
    fmt_file_str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    # Width plan:
    # time (19) | space | level (8) | space | name (25) | space | message
    fmt_console_str = ("%(log_color)s"
        "%(asctime)s | "
        "%(levelname)-8s | "
        "%(name)-25.25s | "
        "%(message)s"
    )

    # ---- Console handler (colored if possible) ----
    sh = logging.StreamHandler()
    if ColoredFormatter is not None:
        fmt_console = ColoredFormatter(
            fmt_console_str,
            datefmt=datefmt,
            log_colors={
                "DEBUG":    "cyan",
                "INFO":     "white",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_white,bg_red",
            },
            style="%",  # OK: stdlib uses a one-char string for style
        )
    else:
        # Fallback to plain formatter if colorlog isn't installed
        fmt_console = logging.Formatter(fmt_file_str, datefmt=datefmt)
    sh.setFormatter(fmt_console)
    # Optional: mark so you can detect your own handlers later
    sh._app_logging = True
    root.addHandler(sh)

    # ---- Rotating file handler (plain, no colors) ----
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / "wwd_gui.log"

    fh = logging.handlers.RotatingFileHandler(
        filename=log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fmt_file = logging.Formatter(fmt_file_str, datefmt=datefmt)
    fh.setFormatter(fmt_file)
    fh._app_logging = True
    root.addHandler(fh)

    # Tame noisy libraries
    logging.getLogger("pyvisa").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)



