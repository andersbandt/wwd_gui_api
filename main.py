"""Entry point for the WWD GUI application."""

import argparse
import ctypes
import logging
import sys
from colorlog import ColoredFormatter

from common.app_logging import setup_logging
from gui import gui_driver

logger = logging.getLogger(__name__)


# TODO: folder paths and structure are documented in CLAUDE.md — review that for completeness


def setup_logging(level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)

    for h in list(logger.handlers):
        logger.removeHandler(h)

    fmt = "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    formatter = ColoredFormatter(
        fmt,
        datefmt=datefmt,
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "white",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_white,bg_red",
        },
        secondary_log_colors={},
        style="%",
    )

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# Example
if __name__ == "__main__":

    log = logging.getLogger("demo")
    log.info("Colored with colorlog")




def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="A description of your script.")

    # Add command-line arguments
    parser.add_argument('-a', '--autoconnect', action='store_true', help='Enable auto-connect mode')
    parser.add_argument('-c', '--compact', action='store_true', help='Force compact mode (overrides automatic screen size detection)')
    parser.add_argument('--log-level', default='DEBUG',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Set logging level (default: DEBUG)')

    # Parse the arguments
    args = parser.parse_args()

    # Configure logging before anything else
    numeric_level = getattr(logging, args.log_level.upper(), logging.DEBUG)
    setup_logging(level=numeric_level)

    # Use the arguments to determine behavior
    autoconnect = False
    if args.autoconnect:
        logger.info("Auto-connect enabled.")
        autoconnect = True

    force_compact = False
    if args.compact:
        logger.info("Compact mode forced.")
        force_compact = True

    # Windows: set explicit App User Model ID so the taskbar uses our icon
    # rather than the generic Python icon, and allows correct taskbar pinning.
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('wwd.gui.api')

    # Linux doesn't have an equivalent App User Model ID API — not applicable.

    # Call the main function of your GUI driver
    gui_driver.main(autoconnect, force_compact)

    # quit if we reach this point
    logger.info("calling quit()")
    quit()


##############################################################
################   MAIN     ##################################
##############################################################
if __name__ == '__main__':
    main()


