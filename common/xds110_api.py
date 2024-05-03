"""
@file     xds110_api.py
@author   Anders Bandt
@date     March 2024
@brief    control the XDS110
"""


# import needed modules
import subprocess
import os
import platform

# import user defined modules
from common import subprocessor as subp


# get operating system information
os_name = platform.system()
print(f"Operating system is currently: {os_name}")

# set PATH information for XDS110 API
if os_name == "Windows":
    base_ccs = "C:/ti/ccs1200/ccs/" # for PC
    # base_ccs = "C:/ti/ccs1240/ccs/ccs_base/" # for laptop
    base_project_path = "C:/Users/ander/Documents/CCS/workspace_WWD/WWD_prog/"
elif os_name == "Linux":
    base_ccs = "/home/anders/ti/ccs1200/ccs/ccs_base/"
    base_project_path = None
else:
    print("Undefined operating system to set for XDS110-API paths!!!")
    raise BaseException

# set common paths based on information above
base_tools_path = base_ccs + "ccs_base/common/uscif/"
base_script_path = base_ccs + "ccs_base/scripting/"

# set XDS110 API information
if os_name == "Windows":
    xds110_reset_cmd = "xds110/xds110reset.exe"
    xds110_jtag_cmd = "dbgjtag.exe"
    xds110_xds_cmd = "xds110/xdsdfu.exe"
    gmake_cmd = base_ccs + "utils/bin/gmake.exe"
elif os_name == "Linux":
    xds110_reset_cmd = "xds110/xds110reset"
    xds110_jtag_cmd = "dbgjtag"
    xds110_xds_cmd = "xds110/xdsdfu"
    gmake_cmd = base_ccs + "utils/bin/gmake"



class XDS110Exception(Exception):
    pass

#########################
#### XDS110 API  ########
#########################


def toggle_target(action):
    if action not in ["toggle", "assert", "deassert"]:
        return False
    executable_path = os.path.join(base_tools_path, xds110_reset_cmd)
    packet = subp.execute_command(executable_path, ["-a", action])
    return packet


# @command ./dbgjtag -f @xds110 -S integrity
def get_jtag_integrity():
    executable_path = os.path.join(base_tools_path, xds110_jtag_cmd)
    packet = subp.execute_command(executable_path, ["-f", "@xds110", "-S", "integrity"])
    return packet


def xds110_jtag_reset():
    executable_path = os.path.join(base_tools_path, xds110_jtag_cmd)
    packet = subp.execute_command(executable_path, ["-f", "@xds110", "-r"])
    return packet


def xds110_reset():
    pass


def get_xds110_status():
    executable_path = os.path.join(base_tools_path, xds110_xds_cmd)
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


    packet = subp.execute_command(
        base_script_path + "examples/loadti/loadti.bat",
        [
            "-a",
            "-c",
            base_project_path + config_file,
            base_project_path + "/Debug/WWD_prog.out"
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


