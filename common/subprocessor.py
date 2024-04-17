"""
@file     subprocessor
@author   Anders Bandt
@date     March 2024
@brief    handles OS commands
"""


# import needed modules
import subprocess
import os
import pandas as pd
from time import sleep


class CommandPacket:
    def __init__(self, stdout, stderr, result):
        self.stdout = stdout
        self.stderr = stderr
        self.result = result
        self.string = f"STDOUT: {self.stdout}\nSTDERROR: {self.stderr}"

    def __str__(self):
        return self.string

    def get_string(self):
        return self.string


##############################################################
################   subprocess (OS shell)   ###################
##############################################################

def run_os(base_command):
    print(base_command)
    # os.system(base_command)
    subprocess.call(base_command, shell=True)


def execute_command(base_command, flags):
    command = [base_command] + flags
    print(command)
    result = subprocess.run(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    # Check if the command was successful
    packet = CommandPacket(
        result.stdout.decode(),
        result.stderr.decode(),
        not result.returncode,  # returncode=0 when SUCCESSFUL. Inverting for clarity
    )
    print(packet)
    return packet


def execute_Popen(exec_path, base_command, flags):
    command = [base_command] + flags
    print(command)
    process = subprocess.Popen(command,
                               cwd=exec_path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    #     process.wait(timeout=10)
    # Check if the command was successful
    #     if process.poll() is None:
    #         process.terminate()
    #         print("Command terminated after 10 seconds")
    packet = CommandPacket(
        stdout.decode(),
        stderr.decode(),
        False,
    )
    print(packet)
    return packet







