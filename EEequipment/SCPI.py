
# import needed modules
import serial



class SCPI:
    """
        Serial SCPI interface
    """
    _SIF: serial.Serial  # TODO: understand this line

    def __init__(self, port_dev, speed, timeout=2):
        self._SIF = None
        self._SIF = serial.Serial(
            port=port_dev,
            baudrate=speed,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=timeout)


    def __del__(self):
        # try:
        #     self._SIF.close()
        # except:
        #     pass
        self._SIF.close()

    def readdata(self):
        """
            read a SCPI response from the serial port terminated by CR LF
            any no-UTF8 characters are replaced by backslash-hex code
        """
        buf = bytearray(0)
        n = 0
        while True:
            data = self._SIF.read(64)
            if len(data) > 0:
                buf.extend(data)
                if len(buf) >= 2:
                    if buf[-2:] == b'\r\n':
                        break
            else:
                n = n + 1
                if n > 2:
                    buf = bytearray(0)
                    break;

        # for b in buf: print(hex(b)+' ',end='')
        # print()
        res = buf.decode(errors="backslashreplace")
        x = res.find('\r\n')
        if x == len(res) - 2:
            res = res.strip()
        else:
            res = ''
        return res

    def sendcmd(self, msg, getdata=True):
        """
            send a command over SCPI. If getdata is True, it waits for
            the response and returns it
        """
        msg = msg + '\n'
        self._SIF.write(msg.encode('ascii'))
        if getdata:
            res = self.readdata()
        else:
            res = None
        return res
