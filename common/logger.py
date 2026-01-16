"""
@file     logger.py
@author   Anders Bandt
@date     April 2024
@brief    handle logging of application to output files
"""

# import needed modules
import logging
from analysis import csv_helper as csvh
import os
from time import strftime, localtime
from fpdf import FPDF
from datetime import datetime
from dataclasses import dataclass

from analysis.csv_helper import CSVHelper

log_folder = "data" # master program folder for all output data. tag:hardcode


#################################
#### file stuff  ################
#################################

def build_log_name(prefix, file_str_ext):
    # FILENAME SETUP
    recName = prefix + "_" + strftime('%Y%m%d%H%M%S', localtime())
    if file_str_ext is not None:
        recName += "_" + file_str_ext
    recName += ".csv"
    return recName


# TODO: evaluate this function compared to the more recent one above
def get_filename(basefilepath, folder, name_ext, extension):
    current_datetime = datetime.now()
    date_strf = "%Y%m%d"
    formatted_datetime = current_datetime.strftime(date_strf)
    if name_ext is None:
        name_ext = ""
    filename = f"{basefilepath}/{log_folder}/{folder}/_{formatted_datetime}_{name_ext}.{extension}"
    return filename


#################################
#### .log (text_data)  ##########
#################################

def init_text(basefilepath, data_folder, start_msg):
    filename = get_filename(basefilepath, # basefilepath
                            data_folder, # (output folder)
                            None, # name_ext
                            "log") # .extension
    open_text(filename, start_msg)
    print("Text file output started!!!")
    print("\toutput started at file: ", filename)
    return filename


def open_text(filename, log_start_msg):
    with open(filename, mode='a', newline='') as file:
        file.write(log_start_msg)


def append_text(filename, data):
    with open(filename, mode='a', newline='') as file:
        file.write(data)


#################################################
#### AAL (advanced abstracted logging  ##########
#################################################

@dataclass
class RecordConfig:
    use_ser: bool = False
    use_dmm: bool = False
    use_ps: bool = False
    ps_channels: int = 1  # will be set to 2 if user confirms and PS supports it
    serial_params: str = None


def create_record_config(use_ser, use_dmm, use_ps, ps_channels, serial_params):
    config = RecordConfig(use_ser=use_ser, use_dmm=use_dmm, use_ps=use_ps, ps_channels=ps_channels, serial_params=serial_params)
    return config


def parse_serial_params(raw: str):
    """
    Parse comma-separated serial params. Raises ValueError if format is invalid.
    Rules:
      - No empty segments (no leading/trailing commas, no consecutive commas)
      - Whitespace around names is allowed and stripped
    """
    raw = (raw or "").strip()
    if not raw:
        # Let caller decide how to warn; return empty list to keep logic simple.
        return []

    parts = [p.strip() for p in raw.split(",")]
    if any(p == "" for p in parts):
        raise ValueError(
            "Invalid serial parameter format. "
            "No consecutive or leading/trailing commas allowed. Example: SN,BoardRev,FW"
        )
    return parts


def build_headers(record_config: RecordConfig):
    # SETUP CSV HEADER PARAMETERS
    headers = ["Time"]

    # Serial/user-entered metadata (if selected)
    if record_config.use_ser:
        parts = parse_serial_params(record_config.serial_params)
        if parts is None:
            return False
        headers += parts

    # DMM selected?
    if record_config.use_dmm:
        # dmm_params = ["DMM_Range", "DMM_Func1", "DMM_Meas1"]
        dmm_params = ["DMM_Meas1"]
        headers += dmm_params

    # Power Supply selected?
    if record_config.use_ps:
        ps_params = ["PS_Vset1", "PS_Vmeas1", "PS_Imeas1"]

        # TODO: have to get creative about detecting status
        # if self.cc.get_ps_status():
        if 1:
            if record_config.ps_channels > 1:
                ps_params += ["PS_Vset2", "PS_Vmeas2", "PS_Imeas2"]

        headers += ps_params

    return headers


# ---------------------------
# Orchestrator (single call)
# ---------------------------

def setup_recording(data_dir: str, prefix: str, ext_text: str, config: RecordConfig):
    """
    High-level setup that:
      1) Creates the filename
      2) Builds the headers (may alert/confirm via callbacks)
      3) Initializes the CSV file
    Returns: (filename, headers, csv_helper, updated_config)
    """
    rec_name = build_log_name(prefix, ext_text)
    headers = build_headers(config)
    csvobj = csvh.init_csvh(data_dir, rec_name, headers)
    return rec_name, csvobj


def start_recording(csvobj: CSVHelper):
    csvobj.initialize_file()
