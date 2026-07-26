"""Binary host<->device command protocol for the WWD-n firmware's dedicated
command channel (cdc_acm_uart1 — a second, independent ttyACM interface from
the console/log ttyACM0). Mirrors src/comm/protocol.h/.c in the WWD-n repo.

Frame format, both directions:
    [0]        STX      0xAA
    [1]        CMD      1 byte
    [2:3]      LEN      uint16 big-endian, payload length
    [4:4+LEN)  PAYLOAD
    [+4]       CRC32    big-endian, standard (zlib-compatible) CRC32 over
                         CMD + LEN(big-endian) + PAYLOAD
"""

import logging
import struct
import time
import zlib

import serial

logger = logging.getLogger(__name__)

STX = 0xAA

CMD_PING = 0x01
CMD_DUMP_START = 0x02
CMD_DUMP_DATA = 0x03
CMD_DUMP_DONE = 0x04
CMD_ERASE = 0x05
CMD_SET_RATE = 0x06
CMD_GET_RATE = 0x07
CMD_ACK = 0x7E
CMD_ERR = 0x7F

# ICM-42670 discrete ODR steps — see accel_freq_to_param()/gyro_freq_to_param()
# in ICM_42670.c. imu_set_odr() on the firmware rejects anything else.
VALID_IMU_ODR_HZ = (25, 50, 100, 200, 400, 800)

ERR_NAMES = {
    0x00: "NONE",
    0x01: "UNKNOWN_CMD",
    0x02: "NOT_IMPLEMENTED",
    0x03: "NVS_NOT_READY",
    0x04: "NVS_READ_FAIL",
    0x05: "BAD_RATE",
}


class ProtocolError(Exception):
    """Raised on framing/CRC errors or an explicit CMD_ERR from the device."""


class ConnectionLostError(ProtocolError):
    """Raised when the underlying serial port drops mid-operation (device
    unplugged, USB re-enumeration, relay flakiness, etc). A subclass of
    ProtocolError so existing `except ProtocolError` call sites still catch
    it, but callers that want to react specifically (e.g. reset a "connected"
    status indicator) can catch this instead."""


class DeviceProtocol:
    """Thin client for the WWD-n binary command channel.

    Not thread-safe — callers running commands from a background thread
    (recommended for DUMP, which can take well over a minute) must not also
    call from the GUI thread concurrently.
    """

    def __init__(self, port, baud_rate=115200, timeout=2):
        self.port = port
        self.baud_rate = baud_rate
        self.ser = serial.Serial(port, baud_rate, timeout=timeout)  # SerialException here is the caller's to catch
        self.serStatus = True
        self._buf = bytearray()
        time.sleep(0.3)
        try:
            self.ser.reset_input_buffer()
        except (serial.SerialException, OSError) as e:
            self.serStatus = False
            self.ser.close()
            raise ConnectionLostError(f"lost connection to {port} right after opening: {e}") from e

    def close(self):
        try:
            self.ser.close()
        finally:
            self.serStatus = False

    # ------------------------------------------------------------------
    # Framing
    # ------------------------------------------------------------------

    @staticmethod
    def _build_frame(cmd, payload=b""):
        hdr = bytes([STX, cmd]) + struct.pack(">H", len(payload))
        crc = zlib.crc32(bytes([cmd]) + struct.pack(">H", len(payload)) + payload) & 0xFFFFFFFF
        return hdr + payload + struct.pack(">I", crc)

    def _fill(self, n_min, timeout):
        t0 = time.time()
        while len(self._buf) < n_min:
            try:
                chunk = self.ser.read(4096)
            except (serial.SerialException, OSError) as e:
                # termios raises a plain OSError (e.g. "Input/output error")
                # when the underlying tty disappears out from under an open
                # fd — pyserial doesn't wrap that as SerialException.
                self.serStatus = False
                raise ConnectionLostError(f"lost connection to {self.port}: {e}") from e
            if chunk:
                self._buf += chunk
            if time.time() - t0 > timeout:
                raise TimeoutError(f"timed out waiting for {n_min} byte(s), have {len(self._buf)}")

    def _read_frame(self, timeout=5):
        """Reads and validates one frame. Returns (cmd, payload)."""
        t0 = time.time()
        while True:
            self._fill(1, timeout=timeout)
            if self._buf[0] == STX:
                break
            self._buf.pop(0)
            if time.time() - t0 > timeout:
                raise TimeoutError("timed out resyncing to STX")

        self._fill(4, timeout=timeout)
        cmd = self._buf[1]
        length = struct.unpack(">H", self._buf[2:4])[0]
        total = 4 + length + 4
        self._fill(total, timeout=timeout)

        frame = bytes(self._buf[:total])
        del self._buf[:total]

        payload = frame[4:4 + length]
        rx_crc = struct.unpack(">I", frame[4 + length:4 + length + 4])[0]
        calc_crc = zlib.crc32(bytes([cmd]) + struct.pack(">H", length) + payload) & 0xFFFFFFFF

        if rx_crc != calc_crc:
            raise ProtocolError(f"CRC mismatch on cmd 0x{cmd:02x} (rx=0x{rx_crc:08x} calc=0x{calc_crc:08x})")

        if cmd == CMD_ERR:
            for_cmd = payload[0] if len(payload) > 0 else -1
            err_code = payload[1] if len(payload) > 1 else -1
            err_name = ERR_NAMES.get(err_code, f"0x{err_code:02x}")
            raise ProtocolError(f"device returned ERR for cmd 0x{for_cmd:02x}: {err_name}")

        return cmd, payload

    def _send(self, cmd, payload=b""):
        try:
            self.ser.reset_input_buffer()
            self._buf.clear()
            self.ser.write(self._build_frame(cmd, payload))
        except (serial.SerialException, OSError) as e:
            self.serStatus = False
            raise ConnectionLostError(f"lost connection to {self.port}: {e}") from e

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def ping(self, timeout=5):
        self._send(CMD_PING)
        cmd, payload = self._read_frame(timeout=timeout)
        return cmd == CMD_ACK and len(payload) == 1 and payload[0] == CMD_PING

    def dump(self, progress_callback=None, frame_timeout=15):
        """Requests a full flash dump. Blocks until CMD_DUMP_DONE.

        progress_callback(bytes_received, total_bytes_if_known) is called
        after every frame if provided.

        Returns (data: bytes, device_crc32: int). Raises ProtocolError if the
        host-reconstructed CRC doesn't match the device's.
        """
        self._send(CMD_DUMP_START)
        cmd, payload = self._read_frame(timeout=frame_timeout)
        if cmd != CMD_ACK:
            raise ProtocolError(f"expected ACK for DUMP_START, got cmd 0x{cmd:02x}")

        # ACK payload = echoed cmd(1) + total_bytes(4BE). Older firmware
        # without the total-size extension sends just the 1-byte ACK.
        total_expected = struct.unpack(">I", payload[1:5])[0] if len(payload) >= 5 else None

        data = bytearray()
        while True:
            cmd, payload = self._read_frame(timeout=frame_timeout)

            if cmd == CMD_DUMP_DATA:
                # payload = addr(4BE) + raw flash bytes; addr is informational
                # (frames arrive in order) so only the data is kept here.
                data += payload[4:]
                if progress_callback:
                    progress_callback(len(data), total_expected)
            elif cmd == CMD_DUMP_DONE:
                total, device_crc = struct.unpack(">II", payload)
                host_crc = zlib.crc32(bytes(data)) & 0xFFFFFFFF
                if total != len(data):
                    raise ProtocolError(f"dump size mismatch: device says {total}, received {len(data)}")
                if host_crc != device_crc:
                    raise ProtocolError(f"dump CRC mismatch: device=0x{device_crc:08x} host=0x{host_crc:08x}")
                return bytes(data), device_crc
            else:
                raise ProtocolError(f"unexpected cmd 0x{cmd:02x} during dump")

    def erase(self, timeout=20):
        """Erases the whole on-device flash log. Blocking (several seconds on
        the MT29F2G01 — the default timeout leaves headroom). Irreversible;
        callers should confirm with the user before calling this. Raises
        ProtocolError on failure (e.g. NVS not ready)."""
        self._send(CMD_ERASE)
        cmd, payload = self._read_frame(timeout=timeout)
        if cmd != CMD_ACK:
            raise ProtocolError(f"expected ACK for ERASE, got cmd 0x{cmd:02x}")

    def get_rate(self, timeout=5):
        """Returns (imu_odr_hz, temp_interval_sec) currently in effect on the device."""
        self._send(CMD_GET_RATE)
        cmd, payload = self._read_frame(timeout=timeout)
        if cmd != CMD_ACK or len(payload) < 5:
            raise ProtocolError(f"expected rate ACK for GET_RATE, got cmd 0x{cmd:02x}")
        return struct.unpack(">HH", payload[1:5])

    def set_rate(self, imu_odr_hz, temp_interval_sec, timeout=5):
        """Applies new rates immediately. imu_odr_hz must be one of
        VALID_IMU_ODR_HZ; temp_interval_sec is 1-3600. Returns the
        (imu_odr_hz, temp_interval_sec) actually in effect after the call
        (echoed back by the device). Raises ProtocolError(...BAD_RATE) if
        either value was rejected — in that case neither was changed."""
        payload = struct.pack(">HH", imu_odr_hz, temp_interval_sec)
        self._send(CMD_SET_RATE, payload)
        cmd, resp = self._read_frame(timeout=timeout)
        if cmd != CMD_ACK or len(resp) < 5:
            raise ProtocolError(f"expected rate ACK for SET_RATE, got cmd 0x{cmd:02x}")
        return struct.unpack(">HH", resp[1:5])
