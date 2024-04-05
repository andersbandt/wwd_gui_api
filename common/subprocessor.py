# import needed modules
import subprocess
import os
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
    # Check if the command was successful
    packet = CommandPacket(
        stdout.decode(),
        stderr.decode(),
        False,
    )
    print(packet)
    return packet


# def execute_command(base_command, flags):
#     executable_path = os.path.join(base_command)
#     command = [executable_path] + flags
#     print(command)
#     result = None
#     try:
#         result = subprocess.run(command,
#                                 stdout=subprocess.PIPE,
#                                 stderr=subprocess.PIPE,
#                                 timeout=60)
#     except subprocess.TimeoutExpired:
#         print("Command timed out after 60 seconds.")

# try:
#     process = subprocess.Popen(command,
#                                stdout=subprocess.PIPE,
#                                stderr=subprocess.PIPE)
#     process.wait(timeout=10)
#     if process.poll() is None:
#         process.terminate()
#         print("Command terminated after 10 seconds")
# except subprocess.TimeoutExpired:
#     print("Command timed out after 10 seconds.")

# # Check if the command was successful
# print(result.stdout.decode())
# if result.returncode == 0:
#     print("COMMAND EXECUTED SUCCESSFULLY")
#     print(result.stderr.decode())
#     return result.stdout.decode()
# else:
#     print("ERROR WITH COMMAND")
#     print(result.stderr.decode())
#     return False


##############################################################
################   DATA and .csv FUNCS   #####################
##############################################################

### data loading functions

def load_csv(filepath, columns=['timestamp', 'fifo', 'data']):
    print(f"Attempting to open a .csv using columns: \n\t{columns}")
    try:
        # Load data from CSV file
        df = pd.read_csv(filepath)
    except pandas.errors.EmptyDataError:
        print("Pandas says data is empty! No columns to parse from file")
        return None
    # # Extract columns
    pandas_data = df[columns]
    if len(pandas_data['timestamp'].tolist()) == 0:
        print("File seems to be .csv but there is no data!")
        return None
    return pandas_data
