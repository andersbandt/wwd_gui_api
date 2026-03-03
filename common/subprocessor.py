"""Subprocess wrapper for executing OS commands."""

# import needed modules
import logging
import subprocess

logger = logging.getLogger(__name__)


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
    logger.info(base_command)
    # os.system(base_command)
    subprocess.call(base_command, shell=True)


def execute_command(base_command, flags):
    command = [base_command] + flags
    logger.debug(command)

    try:
        result = subprocess.run(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    except FileNotFoundError:
        return False

    # Check if the command was successful
    packet = CommandPacket(
        result.stdout.decode(),
        result.stderr.decode(),
        not result.returncode,  # returncode=0 when SUCCESSFUL. Inverting for clarity
    )
    return packet


def execute_Popen(exec_path, base_command, flags):
    command = [base_command] + flags

    try:
        process = subprocess.Popen(command,
                                   cwd=exec_path,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
    except FileNotFoundError:
        return False

    packet = CommandPacket(
        stdout.decode(),
        stderr.decode(),
        False,
    )
    return packet



