"""
@file     guiTab_5_USB.py
@author   Anders Bandt
@date     March 2024
@brief    control device through serial (COM) port
"""


# import needed modules
import subprocess
import os
import pandas as pd
from time import sleep
from datetime import datetime


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


##############################################################
################   DATA and .csv FUNCS   #####################
##############################################################

### data loading functions
def load_csv(filepath, columns=['timestamp', 'fifo', 'data']):
    print(f"Attempting to open a .csv using columns: \n\t{columns}")
    try:
        # Load data from CSV file
        df = pd.read_csv(filepath)
    except pd.errors.EmptyDataError:
        print("Pandas says data is empty! No columns to parse from file")
        return None
    # # Extract columns
    pandas_data = df[columns]
    if len(pandas_data[columns[0]].tolist()) == 0:
        print("File seems to be .csv but there is no data!")
        return None
    return pandas_data


datetime_format = "%Y-%m-%d %H:%M:%S.%f" # need to add an extra space at the end because of my printout?


def create_datetime(timestamp_array):
    datetime_arr = []
    for timestamp_str in timestamp_array:
        tmp = datetime.strptime(timestamp_str, datetime_format)
        datetime_arr.append(tmp)
    return datetime_arr


