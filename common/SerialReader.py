
# import needed modules
from datetime import datetime
import pandas as pd
import csv
import pandas.errors
import serial
from drawnow import *

# import user created modules
from common import Serial


class SerialReader(Serial.Serial):
    def __init__(self, port):
        # initialize serial connection
        self.serObj = serial.Serial(port, 115200)

        # set up some variables
        self.afe_adc = []
        self.plot_cnt = 0


# TODO: make this more modular with parameters
    def init_data_process(self, basefilepath, parameters, filename_ext=None):
        # configure .csv output file
        prefix = basefilepath + "data"  # store in base filepath with "data_" as file prefix
        extension = "csv"
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y%m%d_%H%M%S")
        if filename_ext is None:
            filename = f"{prefix}_{formatted_datetime}.{extension}"
        else:
            filename = f"{prefix}_{formatted_datetime}_{filename_ext}.{extension}"

        self.open_csv(filename, parameters)

        # while loop that loops forever
        while True:
            # while self.serObj.inWaiting() == 0: # Wait here until there is data
            #     pass
            data_array = self.get_data(printmode=True)
            if data_array is not None:
                print(data_array)
                self.append_csv(filename, data_array)


# TODO: compare this to the one its overriding in Serial parent class
    def get_data(self, data_mode, printmode=False):
        serStrDatp = self.serObj.read_until()
        try:
            serStrDat = serStrDatp.decode('utf-8').strip().strip('\n')
        except UnicodeDecodeError as e:
            # serStrDat = serStrDatp.hex()
            raise e
        # serStrDat = self.serObj.read(1).decode('utf-8')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        # dataArray = serStrDat.decode(errors='ignore').strip().strip('\n')
        if printmode:
            print(serStrDat)
        if data_mode == "data":
            if "DATA," in serStrDat:
                data_array = serStrDat.split(',')
                data_array.append(timestamp)
                return data_array
        elif data_mode == "raw":
            return serStrDat
        else:
            raise Exception("ERROR: undefined data mode for SerialReader")
            return False


    def close(self):
        print("Stopping serial data processing")
        plt.close()
        self.serObj.close()

    def open_csv(self, filename, headers):
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

    def append_csv(self, filename, row_data):
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows([row_data])

    # Create a function that makes our desired plot
    def makeFig(self):
        plt.title('Sensor data')  # Set the title
        plt.grid(True)  # Set The grid
        plt.ylabel('Axis Acceleration')  # Label the y axis
        plt.plot(self.afe_adc, 'ro-', label='AFE data')  # Set the line plot

    def live_plot(self, data):
        plt.ion()
        update_frequency = 10

        # Ensure that index is not out of range
        if len(data) > 1:
            adc = int(data[2])
            self.afe_adc.append(adc)

            # trim array
            self.plot_cnt = self.plot_cnt + 1
            if self.plot_cnt > 100:
                self.afe_adc.pop(0)

        if self.plot_cnt % update_frequency == 0:
            drawnow(self.makeFig)
            # self.makeFig() # GPT suggested not using drawnow() but I haven't gotten this to work
            plt.pause(.00000001)



