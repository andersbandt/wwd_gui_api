

import numpy  # Import numpy
import matplotlib.pyplot as plt #import matplotlib library
import serial
from drawnow import *


# initialize accel / gyro arrays
a_x = []
a_y = []
a_z = []
g_x = []
g_y = []
g_z = []


# initialize serial connection
imuSer = serial.Serial('COM13', 115200)

# configure some settings
plt.ion()    #Tell matplotlib you want interactive mode to plot live data
cnt = 0

# Create a function that makes our desired plot
def makeFig():
    #plt.ylim(0,1000)                #Set the limit on the y axis
    plt.title('Sensor data')         #Set the title
    plt.grid(True)                   #Set The grid
    plt.ylabel('Axis Acceleration')  #Label the y axis
    plt.plot(a_x, 'ro-', label='Raw X Acceleration') #Set the line plot
    plt.ylim(-2500, 2500)
    plt.legend(loc='upper left')
    plt2 = plt.twinx()  #Create a new object of plt2
    plt2.plot(a_y, 'b^-', label='Raw Y Acceleration')
    #plt2.ylim(0,1000)
    plt2.legend(loc='center right')
    plt2.ticklabel_format(useOffset=False) #Compel matplotlib not to autoscale
    #plt3 = plt.twinx()
    plt.plot(a_z, 'go-', label='Raw Z Acceleration')
    plt.legend(loc='upper right')
    plt.ylim(-2500, 2500)


# while loop that loops forever
def imu_live_graph():
    while True:
        while imuSer.inWaiting() == 0:   #Wait here until there is data
            pass #do nothing

        # read line of text_data from serial and format into array
        imuStrDat = imuSer.readline()

        # dataArray = imuStrDat.strip().strip('\n')  #Split into an array
        dataArray = imuStrDat.decode(errors='ignore').strip().strip('\n')

        # Ensure that you are not working on empty line
        if dataArray:
            dataArray = dataArray.split(",")

        # Ensure that index is not out of range
        if len(dataArray) > 1:
            xAxis = int(dataArray[0]) #Convert first element to int insert in xAxis
            yAxis = int(dataArray[1]) #Convert second element to int insert in yAxis
            zAxis = int(dataArray[2]) #Convert third element to int insert in zAxis
            print(xAxis, ",", yAxis, ",", zAxis)

            a_x.append(xAxis)   #Build our x axis array by appending to accelX
            a_y.append(yAxis)   #Build our y axis array by appending to accelY
            a_z.append(zAxis)   #Build our z axis array by appending to accelZ
            drawnow(makeFig)       #Call drawnow to update our live graph
            plt.pause(.00000001)

            cnt = cnt+1

            if cnt > 100:
                a_x.pop(0)
                a_y.pop(0)
                a_z.pop(0)
            #     cnt = 0
