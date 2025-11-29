
# import needed modules
import pyvisa
import time

import platform
print(platform.architecture())


try:
    # Open Connection Keysight Visa
    rm = pyvisa.ResourceManager()
    print("PyVISA Version:", pyvisa.__version__)
    print("Backend:", rm.visalib)
    print("Available Resources:", rm.list_resources())


    # Connect to VISA Address
    # GPIB Connection: 'GPIP0::xx::INSTR'
    myinst = rm.open_resource("GPIB0::2::INSTR")
    myinst.write_termination = '\r\n'
    myinst.read_termination = '\r\n'
    myinst.timeout = 3 * 1000
    time.sleep(0.5)

    ### *IDN? TEST
    # print(f"IDN query: {myinst.query("*IDN?")}")
    # myinst.write("F1")
    print(f"ID query: {myinst.query("?")}")


    ### DMM TEST
    # print(myinst.query("MEAS?"))


    # POWER SUPPLY TEST
    # generate voltage level output in sequence
    # myinst.write('OUTPut ON')
    # listMode = [0, 1, 2, 3, 5, 10]
    # for v in listMode:
    #     print(f"Writing voltage ... {v}")
    #     myinst.write(':SOURce:VOLTage:LEVel:IMMediate:AMPLitude %G' % v)
    #     time.sleep(0.25)


    # Close Connection
    myinst.close()
    print
    'close instrument connection'
except Exception as err:
    print(err)
finally:
    # perform clean up operations
    print("\nprogram complete!")