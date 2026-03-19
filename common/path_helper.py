"""Centralized path management for data directories."""

import logging
import os
import configparser

logger = logging.getLogger(__name__)

# Module-level reference to the centralized ConfigService (set at startup)
_config_svc = None


def init_config_service(config_svc):
    """Wire in the centralized ConfigService. Called once from gui_driver.main()."""
    global _config_svc
    _config_svc = config_svc


def get_config_path():
    """Get the path to the master configuration file (master.ini)."""
    return os.path.join("config", "master.ini")


def get_logger_prefix():
    """Get the recording filename prefix from master.ini [LOGGER] section."""
    if _config_svc is not None:
        return _config_svc.get_logger_prefix()

    # Fallback: read directly (before ConfigService is available)
    config_file_path = get_config_path()
    default_prefix = "AREC"

    if os.path.exists(config_file_path):
        config = configparser.ConfigParser()
        config.read(config_file_path)
        if "LOGGER" in config:
            return config["LOGGER"].get("prefix", default_prefix).strip()

    return default_prefix


def get_data_dir(subdir=None, create=True):
    """
    Get the data directory path, optionally with a subdirectory.

    Args:
        subdir: Optional subdirectory within data dir (e.g., "ps_data", "fg_data")
        create: If True, creates the directory if it doesn't exist

    Returns:
        str: Full path to data directory

    Example:
        get_data_dir()              # Returns "data"
        get_data_dir("ps_data")     # Returns "data/ps_data"
    """
    if _config_svc is not None:
        data_dir = _config_svc.get_data_dir_name()
    else:
        # Fallback: read directly (before ConfigService is available)
        config_file_path = get_config_path()
        default_data_dir = "data"

        if os.path.exists(config_file_path):
            config = configparser.ConfigParser()
            config.read(config_file_path)
            if "PATHS" in config:
                data_dir = config["PATHS"].get("data_dir", default_data_dir).strip()
            else:
                data_dir = default_data_dir
        else:
            data_dir = default_data_dir

    # Add subdirectory if specified
    if subdir:
        full_path = os.path.join(data_dir, subdir)
    else:
        full_path = data_dir

    # Create directory if it doesn't exist
    if create and not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
        logger.info(f"Created data directory: {full_path}")

    return full_path


def get_base_path():
    """
    Get the base application path (current working directory).

    Returns:
        str: Base application path
    """
    return os.getcwd()


def get_full_data_path(subdir=None, create=True):
    """
    Get the full absolute path to data directory.

    Args:
        subdir: Optional subdirectory within data dir
        create: If True, creates the directory if it doesn't exist

    Returns:
        str: Full absolute path to data directory
    """
    base_path = get_base_path()
    data_dir = get_data_dir(subdir=subdir, create=create)
    return os.path.join(base_path, data_dir)
