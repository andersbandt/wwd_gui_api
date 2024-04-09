"""
@file     guiTab_5_USB.py
@author   Anders Bandt
@date     March 2024
@brief    control device through serial (COM) port
"""


# import needed modules
import subprocess
import os

# import user defined modules
from common import subprocessor as subp



base_ccs = "C:/ti/ccs1200/ccs/ccs_base/" # for PC
# base_ccs = "C:/ti/ccs1240/ccs/ccs_base/" # for laptop


base_tools_path = base_ccs + "common/uscif/"
base_script_path = base_ccs + "scripting/"


class XDS110Exception(Exception):
    pass

#########################
#### XDS110 API  ########
#########################


def toggle_target(action):
    if action not in ["toggle", "assert", "deassert"]:
        return False
    executable_path = os.path.join(base_tools_path, "xds110/xds110reset.exe")
    packet = subp.execute_command(executable_path, ["-a", action])
    return packet


# @command ./dbgjtag -f @xds110 -S integrity
def get_jtag_integrity():
    executable_path = os.path.join(base_tools_path, "dbgjtag.exe")
    packet = subp.execute_command(executable_path, ["-f", "@xds110", "-S", "integrity"])
    return packet


def xds110_jtag_reset():
    executable_path = os.path.join(base_tools_path, "dbgjtag.exe")
    packet = subp.execute_command(executable_path, ["-f", "@xds110", "-r"])
    return packet


def xds110_reset():
    pass


def get_xds110_status():
    executable_path = os.path.join(base_tools_path, "xds110/xdsdfu.exe")
    packet = subp.execute_command(executable_path, ["-e"])

    # check if result contains search string
    search_string = "Found 0 devices"
    if search_string in packet.stdout:
        xds110_status = False
    else:
        xds110_status = True

    return [xds110_status, packet]


#########################
#### CCS BIN ############
#########################

def flash_firmware(config_type):
    if config_type == "target_power":
        config_file = "/targetConfigs/CC2642R1F.ccxml"
    elif config_type == "probe_power":
        config_file = "/targetConfigs/CC2642R1F_probe_PWR.ccxml"
    else:
        print(f"Trying config {config_type}")
        raise XDS110Exception("Bad target config type!")

    base_path = "C:/Users/ander/Documents/CCS/workspace_WWD/WWD_prog"
    packet = subp.execute_command(
        base_script_path + "examples/loadti/loadti.bat",
        [
            "-a",
            "-c",
            base_path + config_file,
            base_path + "/Debug/WWD_prog.out"
        ])
    error_words = [
        "Error code",
        "Error",
        "An attempt to connect to the XDS110 failed"
    ]
    for error_key in error_words:
        if error_key in packet.stdout:
            return [False, packet]
        elif error_key in packet.stderr:
            return [False, packet]

    return [True, packet]


