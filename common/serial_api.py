import time
import serial
import serial.tools.list_ports



def show_ports():
    # Get a list of all available serial ports
    ports = serial.tools.list_ports.comports()

    # Print information about each port
    for port in ports:
        print(f"Device: {port.device}, Description: {port.description}")



# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial(
    port='COM7',
    baudrate=9600,
    parity=serial.PARITY_ODD,
    stopbits=serial.STOPBITS_TWO,
    bytesize=serial.SEVENBITS
)


inp = 1

msg = " "
while 1:
    msg = " "
    while ser.inWaiting() > 0:
        read = ser.read(1)
        #print(read)
        msg += read.decode("UTF-8")
        print(msg)
    # print(msg)

    # OTHER METHOD LEVERAGING KEYBOARD INPUT???
    # # get keyboard input
    # inp = input(">> ")

    #
    # if inp == 'exit':
    #     ser.close()
    #     exit()
    # else:
    #     # send the character to the device
    #     # (note that I happend a \r\n carriage return and line feed to the characters - this is requested by my device)
    #     ser.write(inp + '\r\n')
    #     out = ''
    #     # let's wait one second before reading output (let's give device time to answer)
    #     time.sleep(1)
    #     while ser.inWaiting() > 0:
    #         out += ser.read(1)
    #
    #     if out != '':
    #         print(">>" + out)