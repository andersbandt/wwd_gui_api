"""Centralized configuration service for master.ini parsing."""

import logging
import os
import configparser
from dataclasses import dataclass
from typing import List

from common.path_helper import get_config_path, resolve_path

logger = logging.getLogger(__name__)


@dataclass
class TargetConfig:
    """Parsed [Target] section from a config file."""
    power_type: int
    ps_channel: int
    debug_config: int
    vdds: float
    usb_relay: int
    toggle_power_delay: int


class ConfigService:
    """Loads and caches master.ini configuration at startup.

    All master.ini reads go through this class so the file is parsed once.
    """

    def __init__(self, config_path=None):
        self._path = config_path or get_config_path()
        self._config = configparser.ConfigParser()

        if os.path.exists(self._path):
            self._config.read(self._path)
        else:
            logger.warning(f"ConfigService: {self._path} not found, using defaults.")

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def get_theme_file(self) -> str:
        """Return the absolute path to the theme JSON file (e.g. '<root>/config/darcula.json')."""
        default_theme = resolve_path("config", "darcula.json")

        if "THEME" not in self._config:
            logger.warning("Missing [THEME] section in config. Using default theme.")
            return default_theme

        theme_file = self._config["THEME"].get("theme_file", "darcula.json").strip()

        if not theme_file.startswith("config/"):
            theme_file = f"config/{theme_file}"
        theme_file = resolve_path(theme_file)

        if not os.path.exists(theme_file):
            logger.warning(f"Theme file {theme_file} does not exist. Using default theme.")
            return default_theme

        logger.info(f"Using theme: {theme_file}")
        return theme_file

    # ------------------------------------------------------------------
    # Autoconnect
    # ------------------------------------------------------------------

    def get_autoconnect_flags(self, num_tabs: int = 10) -> List[bool]:
        """Return a list of per-tab auto-connect booleans."""
        if "AUTOCONNECT" not in self._config:
            raise KeyError("Missing [AUTOCONNECT] section in config.")

        flags = []
        for i in range(1, num_tabs + 1):
            val = self._config["AUTOCONNECT"][f"tab_{i}"]
            flags.append(val.strip().upper() == "YES")
        return flags

    # ------------------------------------------------------------------
    # DMM
    # ------------------------------------------------------------------

    def get_dmm_rate(self) -> str:
        """Return validated DMM rate ('slow', 'medium', or 'fast')."""
        rate = "fast"

        if "DMM" in self._config:
            rate = self._config["DMM"].get("rate", "fast").strip()

        valid_rates = ["slow", "medium", "fast"]
        if rate not in valid_rates:
            logger.warning(f"Invalid DMM rate '{rate}' in config. Using 'fast'.")
            rate = "fast"

        logger.info(f"DMM default rate: {rate}")
        return rate

    # ------------------------------------------------------------------
    # USB
    # ------------------------------------------------------------------

    def get_baud_rate(self) -> int:
        """Return the USB baud rate (default 9600)."""
        default_baud = 9600

        if "USB" not in self._config:
            logger.warning(f"[USB] section not found in config. Using default baud rate: {default_baud}")
            return default_baud

        try:
            baud_rate = self._config["USB"].getint("baud_rate", default_baud)
            logger.info(f"Using baud rate from config: {baud_rate}")
            return baud_rate
        except ValueError:
            logger.warning(f"Invalid baud rate in config. Using default: {default_baud}")
            return default_baud

    # ------------------------------------------------------------------
    # Logger
    # ------------------------------------------------------------------

    def get_logger_prefix(self) -> str:
        """Return the recording filename prefix (default 'AREC')."""
        default_prefix = "AREC"
        if "LOGGER" in self._config:
            return self._config["LOGGER"].get("prefix", default_prefix).strip()
        return default_prefix

    # ------------------------------------------------------------------
    # VISA
    # ------------------------------------------------------------------

    def get_visa_backend(self) -> str:
        """Return the PyVISA backend string.

        Empty string / missing key → NI-VISA default (pyvisa.ResourceManager()).
        '@py' → pyvisa-py (no NI-VISA installation required).
        """
        if "VISA" not in self._config:
            return ""
        return self._config["VISA"].get("backend", "").strip()

    # ------------------------------------------------------------------
    # Power supply
    # ------------------------------------------------------------------

    def get_ps_output_off_on_connect(self) -> bool:
        """Return whether PS outputs should be forced off right after connecting (default True)."""
        if "PS" not in self._config:
            return True
        return self._config["PS"].getboolean("output_off_on_connect", True)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def get_relay_open_on_exit(self) -> bool:
        """Return whether relay channels should be opened on application exit (default True)."""
        if "SHUTDOWN" not in self._config:
            return True
        return self._config["SHUTDOWN"].getboolean("relay_open_on_exit", True)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def get_data_dir_name(self) -> str:
        """Return the raw data directory name (default 'data'). No directory creation."""
        default_data_dir = "data"
        if "PATHS" in self._config:
            return self._config["PATHS"].get("data_dir", default_data_dir).strip()
        return default_data_dir

    # ------------------------------------------------------------------
    # Target
    # ------------------------------------------------------------------

    def get_target_config(self) -> TargetConfig:
        """Return the parsed [Target] section from the cached master.ini."""
        return self._parse_target_section(self._config)

    @staticmethod
    def load_target_config_from_file(file_path: str) -> TargetConfig:
        """Parse [Target] from an arbitrary .ini file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file {file_path} does not exist.")

        config = configparser.ConfigParser()
        config.read(file_path)
        return ConfigService._parse_target_section(config)

    @staticmethod
    def _parse_target_section(config: configparser.ConfigParser) -> TargetConfig:
        """Extract a TargetConfig from any ConfigParser that has a [Target] section."""
        section = config["Target"]
        return TargetConfig(
            power_type=int(section["power_type"]),
            ps_channel=int(section["ps_channel"]),
            debug_config=int(section["debug_config"]),
            vdds=float(section["vdds"]),
            usb_relay=int(section["usb_relay"]),
            toggle_power_delay=int(section.get("toggle_power_delay", "6")),
        )
