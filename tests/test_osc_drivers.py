"""Oscilloscope driver behaviour with the transport mocked out.

Two things are checked without hardware:

1. Every config.ini key the tab's controls reach is actually defined, for
   every scope model. A missing key raises ValueError at the moment the tech
   clicks the button, which is the worst time to find out.
2. The MSO64's overrides emit the TekScope commands they claim to, including
   the Keysight->Tek vocabulary translation the shared GUI depends on.
"""

import os
import re
import struct
import pytest
from unittest.mock import patch

from EEequipment.TestEquipment import ConnectionHandler
from EEequipment.DSO1014A.DSO1014A import DSO1014A
from EEequipment.DSOX4104A.DSOX4104A import DSOX4104A
from EEequipment.MSO64.MSO64 import MSO64

SCOPE_CLASSES = [DSO1014A, DSOX4104A, MSO64]


class RecordingConn(ConnectionHandler):
    """Records writes and answers queries with plausible canned values."""

    def __init__(self, responses=None, raw=b""):
        self.status = True
        self.writes = []
        self.queries = []
        self.responses = responses or {}
        self.raw = raw

    def connect(self, config):
        pass

    def disconnect(self):
        self.status = False

    def write(self, cmd):
        self.writes.append(cmd)

    def read(self):
        return "0"

    def query(self, cmd):
        self.queries.append(cmd)
        for pattern, value in self.responses.items():
            if re.search(pattern, cmd):
                return value
        # EVMsg?/SYSTem:ERRor? both read as "no error" in this form.
        return '0,"No events to report - queue empty"'

    def read_raw(self):
        return self.raw

    def query_raw(self, cmd):
        self.queries.append(cmd)
        return self.raw

    def sent(self, needle):
        return any(needle in w for w in self.writes)


def make_scope(cls, conn=None):
    """Build a driver with connection I/O bypassed, then swap in a recorder."""
    with patch("EEequipment.TestEquipment.PyVISAHandler.connect"):
        scope = cls("FAKE")
    scope.conn = conn or RecordingConn()
    return scope


# ------------------------------------------------- command set completeness --

@pytest.mark.parametrize("cls", SCOPE_CLASSES, ids=[c.__name__ for c in SCOPE_CLASSES])
def test_every_control_the_tab_exposes_resolves(cls):
    """Drive one of each control the OSC tab offers; none may raise."""
    conn = RecordingConn(responses={
        r"SCAle\?|SCALe\?": "1.0E-3",
        r"NR_Pt\?|RECOrdlength\?|POINts\?": "1000",
        r"XINcr\?|XZEro\?|YMUlt\?|YOFf\?|YZEro\?": "1.0E-3",
        r"MEASUrement:LIST\?": "NONE",
        r"RESUlts": "1.234",
        r"MEASure:": "1.234",
        r"DISPlay\?|STATE\?": "1",
    })
    scope = make_scope(cls, conn)

    scope.autoscale()
    scope.channel_on(1)
    scope.channel_off(2)
    scope.get_channel_display(1)
    scope.set_scale(1, 0.5)
    scope.set_coupling(1, "DC")
    scope.set_offset(1, 0.0)
    scope.set_timebase_scale(1e-3)
    scope.set_timebase_position(0.0)
    scope.set_trigger_source("CHANnel1")
    scope.set_trigger_level(1, 1.5)
    scope.set_trigger_slope("POSitive")
    scope.set_acq_type("NORMal")
    scope.set_acq_count(4)
    scope.run()
    scope.stop()
    scope.single()
    scope.measure_all(1)
    scope.get_enabled_channels()

    assert conn.writes, "no commands were sent"


@pytest.mark.parametrize("cls", SCOPE_CLASSES, ids=[c.__name__ for c in SCOPE_CLASSES])
def test_enabled_channels_reads_all_channels(cls):
    conn = RecordingConn(responses={r"DISPlay\?|STATE\?": "1"})
    scope = make_scope(cls, conn)
    assert scope.get_enabled_channels() == [1, 2, 3, 4]


# ------------------------------------------------------------- MSO64 quirks --

def test_mso64_translates_gui_vocabulary_to_tek():
    scope = make_scope(MSO64)
    scope.set_trigger_source("CHANnel3")
    scope.set_trigger_slope("NEGative")
    scope.set_acq_type("HRESolution")

    assert scope.conn.sent("TRIGger:A:EDGE:SOUrce CH3")
    assert scope.conn.sent("TRIGger:A:EDGE:SLOpe FALL")
    assert scope.conn.sent("ACQuire:MODe HIRes")


def test_mso64_horizontal_position_converts_seconds_to_percent():
    # 1 ms/div -> 10 ms on screen. A 1 ms delay moves the trigger 10% left.
    conn = RecordingConn(responses={r"HORizontal:SCAle\?": "1.0E-3"})
    scope = make_scope(MSO64, conn)
    scope.set_timebase_position(1e-3)

    sent = [w for w in conn.writes if "HORizontal:POSition" in w][0]
    assert float(sent.split()[-1]) == pytest.approx(40.0)


def test_mso64_horizontal_position_round_trips():
    conn = RecordingConn(responses={r"HORizontal:SCAle\?": "1.0E-3",
                                    r"HORizontal:POSition\?": "40.0"})
    scope = make_scope(MSO64, conn)
    assert scope.get_timebase_position() == pytest.approx(1e-3)


def test_mso64_measurement_adds_configures_and_reads_a_scratch_slot():
    conn = RecordingConn(responses={r"MEASUrement:LIST\?": "MEAS1,MEAS2",
                                    r"RESUlts:CURRentacq:MEAN\?": "3.3"})
    scope = make_scope(MSO64, conn)
    assert scope.measure_vpp(2) == pytest.approx(3.3)

    # MEAS1 and MEAS2 are the user's; the scratch slot must not clobber them.
    assert conn.sent('MEASUrement:ADDNew "MEAS3"')
    assert conn.sent("MEASUrement:MEAS3:TYPe PK2PK")
    assert conn.sent("MEASUrement:MEAS3:SOUrce CH2")


def test_mso64_measurement_slot_is_allocated_once_and_released():
    conn = RecordingConn(responses={r"MEASUrement:LIST\?": "NONE",
                                    r"RESUlts": "1.0"})
    scope = make_scope(MSO64, conn)
    scope.measure_vpp(1)
    scope.measure_vmax(1)
    assert len([w for w in conn.writes if "ADDNew" in w]) == 1

    scope.disconnect()
    assert conn.sent('MEASUrement:DELete "MEAS1"')


@pytest.mark.parametrize("reply", ["NAN", "9.91E+37"])
def test_mso64_unmeasurable_result_is_none(reply):
    conn = RecordingConn(responses={r"MEASUrement:LIST\?": "NONE",
                                    r"RESUlts": reply})
    scope = make_scope(MSO64, conn)
    assert scope.measure_frequency(1) is None


def test_mso64_waveform_scaling_uses_signed_codes():
    # SRIbinary is signed, unlike the Keysight's unsigned BYTE data.
    payload = struct.pack("<3b", -128, 0, 127)
    block = b"#13" + payload
    conn = RecordingConn(
        responses={r"XINcr\?": "1.0E-6", r"XZEro\?": "0.0",
                   r"YMUlt\?": "0.01", r"YOFf\?": "0.0", r"YZEro\?": "0.0",
                   r"NR_Pt\?": "3", r"RECOrdlength\?": "3"},
        raw=block)
    scope = make_scope(MSO64, conn)

    wav = scope.get_waveform_data(1)
    assert wav["y"] == pytest.approx([-1.28, 0.0, 1.27])
    assert wav["x"] == pytest.approx([0.0, 1e-6, 2e-6])
    assert conn.sent("DATa:SOUrce CH1")


def test_mso64_screenshot_saves_reads_and_cleans_up():
    png = b"\x89PNG\r\n\x1a\n" + b"payload"
    conn = RecordingConn(raw=png)
    scope = make_scope(MSO64, conn)

    assert scope.get_screenshot() == png
    assert conn.sent('SAVe:IMAGe "C:/Temp.png"')
    assert conn.sent('FILESystem:DELEte "C:/Temp.png"')
    assert any("READFile" in q for q in conn.queries)


def test_keysight_screenshot_unwraps_the_ieee_block():
    png = b"\x89PNG\r\n\x1a\n"
    conn = RecordingConn(raw=b"#18" + png + b"\n")
    scope = make_scope(DSOX4104A, conn)
    assert scope.get_screenshot() == png


PNG = b"\x89PNG\r\n\x1a\n"


def test_screenshot_to_file_writes_bytes(tmp_path):
    conn = RecordingConn(raw=b"#18" + PNG)
    scope = make_scope(DSOX4104A, conn)
    path = str(tmp_path / "shot.png")
    assert scope.screenshot_to_file(path) == path
    assert open(path, "rb").read() == PNG


def test_screenshot_accepts_a_payload_with_no_ieee_block():
    """Not every model wraps the image; a bare BMP must pass through intact."""
    bmp = b"BM" + b"\x00" * 20
    conn = RecordingConn(raw=bmp)
    scope = make_scope(DSO1014A, conn)
    assert scope.get_screenshot() == bmp


def test_screenshot_extension_follows_what_the_scope_actually_sent(tmp_path):
    """A BMP must never land on disk named .png."""
    conn = RecordingConn(raw=b"BM" + b"\x00" * 20)
    scope = make_scope(DSO1014A, conn)
    written = scope.screenshot_to_file(str(tmp_path / "shot.png"))
    assert written.endswith("shot.bmp")
    assert os.path.exists(written)
    assert not os.path.exists(str(tmp_path / "shot.png"))


def test_screenshot_rejects_data_that_is_not_an_image(tmp_path):
    """Better a warning in the prompt than a corrupt file named .png."""
    conn = RecordingConn(raw=b"#14abcd")
    scope = make_scope(DSOX4104A, conn)
    with pytest.raises(ValueError, match="recognisable image"):
        scope.screenshot_to_file(str(tmp_path / "shot.png"))
    assert os.listdir(tmp_path) == []
