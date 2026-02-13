"""Centralized path management for data directories."""

import os
import configparser


# TODO: add function here to retrieve config file (master.ini)
#   make it so every instance of path `config/master.ini` instead references the function?


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
    config_file_path = "config/master.ini"
    default_data_dir = "data"

    # Read data directory from config
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
        print(f"Created data directory: {full_path}")

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
