"""
@file     logger.py
@author   Anders Bandt
@date     April 2024
@brief    handle logging of application to output files
"""


# import needed modules
import logging
import csv

from datetime import datetime


def get_filename(basefilepath, name_type, name_ext, extension):
    current_datetime = datetime.now()
    # date_strf = "%Y%m%d_%H%M%S"
    date_strf = "%Y%m%d"
    formatted_datetime = current_datetime.strftime(date_strf)
    if name_ext is None:
        name_ext = ""
    filename = f"{basefilepath}/{name_type}/_{formatted_datetime}_{name_ext}.{extension}"
    return filename


#################################
#### logging  ###################
#################################

def init_log(logname, filename):
    logging.basicConfig(filename=filename,
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)
    logging.info(f"Running {logname}")
    logger = logging.getLogger(logname)
    return logger


def append_info(logger, line):
    logger.info(line)


def append_debug(logger, line):
    logger.debug(line)



#################################
#### .log (text)  ###############
#################################

def init_text(basefilepath, start_msg):
    filename = get_filename(basefilepath, # basefilepath
                            "text", # name_type (output folder)
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


#################################
#### csv  #######################
#################################

def init_csv(basefilepath, parameters):
    filename = get_filename(basefilepath, "data", ".csv")
    open_csv(filename, parameters)
    return filename


# open_csv: basically opens a .csv file with text in header columns
def open_csv(filename, headers):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)


def append_csv(filename, row_data):
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows([row_data])