"""Capture naming and run-CSV behaviour for the OSC tab. No hardware needed."""

import os
import csv
import pytest

from common import capture_naming
from services import osc_service
from services.osc_service import OscService


# ---------------------------------------------------------------- naming ----

def test_render_uses_fields_and_pads_counter():
    name = capture_naming.render(
        "{prefix}_Vin{Vin}_T{Temp}_{n:03d}",
        {"prefix": "psu_ripple", "Vin": "13.5", "Temp": "25"}, 7)
    assert name == "psu_ripple_Vin13.5_T25_007"


def test_render_sanitizes_values_that_would_break_a_path():
    name = capture_naming.render("{prefix}_{n}", {"prefix": "load step/50%"}, 1)
    assert "/" not in name
    assert name == "load_step_50%_1"


def test_render_rejects_unknown_token():
    with pytest.raises(capture_naming.TemplateError) as e:
        capture_naming.render("{Vout}_{n}", {"Vin": "12"}, 1)
    assert "Vout" in str(e.value)


def test_render_rejects_malformed_template():
    with pytest.raises(capture_naming.TemplateError):
        capture_naming.render("{n:03", {}, 1)


def test_render_rejects_empty_result():
    with pytest.raises(capture_naming.TemplateError):
        capture_naming.render("{prefix}", {"prefix": "///"}, 1)


@pytest.mark.parametrize("name,valid", [
    ("Vin", True), ("load_current", True), ("_x1", True),
    ("2Vin", False), ("in-rush", False), ("", False), ("V in", False),
])
def test_field_name_validation(name, valid):
    assert capture_naming.is_valid_field_name(name) is valid


def test_unique_path_avoids_clobbering(tmp_path):
    target = tmp_path / "shot.png"
    target.write_bytes(b"x")
    assert capture_naming.unique_path(str(target)).endswith("shot_2.png")


def test_unique_path_considers_other_image_extensions(tmp_path):
    """A .bmp already on disk must block the matching .png name.

    The scope decides the real format, so the stem is what has to be unique.
    """
    (tmp_path / "shot.bmp").write_bytes(b"BM")
    taken = capture_naming.unique_path(str(tmp_path / "shot.png"),
                                       extensions=capture_naming.IMAGE_EXTENSIONS)
    assert taken.endswith("shot_2.png")


def test_next_index_counts_data_rows(tmp_path):
    csv_path = tmp_path / "run.csv"
    assert capture_naming.next_index(str(csv_path)) == 1
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "capture"])
        w.writerow(["t", "a"])
        w.writerow(["t", "b"])
    assert capture_naming.next_index(str(csv_path)) == 3


# -------------------------------------------------------------- capture ----

class FakeScope:
    """Minimal stand-in for a connected oscilloscope."""
    model = "MSO64"
    channel_count = 4
    MEASUREMENTS = ("vpp", "vavg", "frequency")

    def __init__(self, screenshot_error=None, enabled=(1,), failing=()):
        self.screenshot_error = screenshot_error
        self.enabled = list(enabled)
        # Measurement names that raise, as an unsupported command does.
        self.failing = set(failing)
        self.recovered = 0

    def get_enabled_channels(self):
        return self.enabled

    def measure(self, name, channel):
        if name in self.failing:
            raise TimeoutError(f"{name} timed out")
        if name == "vavg":
            return None          # measurable in principle, no value right now
        return 1.5 * channel

    def recover(self):
        self.recovered += 1

    def screenshot_to_file(self, path):
        if self.screenshot_error:
            raise self.screenshot_error
        with open(path, "wb") as f:
            f.write(b"\x89PNG")
        return path


class FakeController:
    def __init__(self, osc):
        self.osc = osc

    def get_osc_status(self):
        return self.osc is not None


def make_service(osc):
    return OscService(FakeController(osc))


def test_capture_writes_row_and_image(tmp_path):
    svc = make_service(FakeScope())
    run_dir = str(tmp_path / "run")
    result = svc.capture(run_dir, "{prefix}_{n:03d}", {"prefix": "psu"})

    assert result.success
    assert result.name == "psu_001"
    assert os.path.exists(result.image_path)

    with open(result.csv_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["prefix"] == "psu"
    assert rows[0]["CH1_vpp"] == "1.5"
    # A measurement the scope can't make is blank, not the string "None".
    assert rows[0]["CH1_vavg"] == ""


def test_one_failing_measurement_does_not_lose_the_others(tmp_path):
    """The DSO1014A regression: a single unsupported query emptied the row.

    vrms used X-series syntax the 1000 series ignores, so the query timed out,
    and because measure_all was all-or-nothing the CSV ended up with no
    measurement columns at all.
    """
    scope = FakeScope(failing=("vpp",))
    svc = make_service(scope)
    result = svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "psu"})

    assert result.success
    with open(result.csv_path) as f:
        row = next(csv.DictReader(f))
    assert row["CH1_vpp"] == "", "the failed measurement is blank"
    assert row["CH1_frequency"] == "1.5", "the ones after it still ran"
    assert any("vpp" in w for w in result.warnings), "the failure is reported"


def test_failed_measurement_resynchronises_the_transport(tmp_path):
    """A timed-out query leaves its reply queued for the next read."""
    scope = FakeScope(failing=("vpp",))
    svc = make_service(scope)
    svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "psu"})
    assert scope.recovered == 1


def test_measurements_stop_after_repeated_failures(tmp_path):
    """A scope that has stopped answering must not cost a timeout per name."""
    calls = []

    class DeadScope(FakeScope):
        def measure(self, name, channel):
            calls.append(name)
            raise TimeoutError("no reply")

    svc = make_service(DeadScope())
    result = svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "psu"})

    assert result.success, "an unresponsive channel still records the capture"
    assert len(calls) == osc_service.MAX_CONSECUTIVE_FAILURES


def test_capture_counter_advances_across_calls(tmp_path):
    svc = make_service(FakeScope())
    run_dir = str(tmp_path / "run")
    names = [svc.capture(run_dir, "{prefix}_{n:03d}", {"prefix": "psu"}).name
             for _ in range(3)]
    assert names == ["psu_001", "psu_002", "psu_003"]


def test_capture_widens_header_when_a_field_is_added_mid_run(tmp_path):
    svc = make_service(FakeScope())
    run_dir = str(tmp_path / "run")
    svc.capture(run_dir, "{prefix}_{n}", {"prefix": "psu"})
    svc.capture(run_dir, "{prefix}_{n}", {"prefix": "psu", "Temp": "40"})

    with open(svc.run_csv_path(run_dir)) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2, "a new field must not start a second CSV"
    assert rows[0]["Temp"] == ""
    assert rows[1]["Temp"] == "40"


def test_screenshot_failure_degrades_to_warning(tmp_path):
    svc = make_service(FakeScope(screenshot_error=OSError("no disk")))
    result = svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "psu"})

    assert result.success, "measurements must survive a failed screenshot"
    assert result.image_path is None
    assert any("Screenshot failed" in w for w in result.warnings)
    assert os.path.exists(result.csv_path)


def test_capture_without_connection_fails_cleanly(tmp_path):
    svc = make_service(None)
    result = svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "psu"})
    assert not result.success
    assert "connection" in result.error.lower()


def test_capture_with_no_channels_enabled_fails_cleanly(tmp_path):
    svc = make_service(FakeScope(enabled=()))
    result = svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "psu"})
    assert not result.success
    assert "channel" in result.error.lower()


def test_capture_bad_template_reports_before_writing(tmp_path):
    svc = make_service(FakeScope())
    run_dir = str(tmp_path / "run")
    result = svc.capture(run_dir, "{Vout}_{n}", {"prefix": "psu"})
    assert not result.success
    assert not os.path.exists(svc.run_csv_path(run_dir))


def test_measurements_can_be_skipped_for_image_only_captures(tmp_path):
    svc = make_service(FakeScope())
    run_dir = str(tmp_path / "run")
    result = svc.capture(run_dir, "{prefix}_{n}", {"prefix": "psu"},
                         save_measurements=False)
    assert result.success
    assert result.csv_path is None
    assert os.path.exists(result.image_path)
    assert not os.path.exists(svc.run_csv_path(run_dir))


# ------------------------------------------------------------- waveform ----

class WaveScope(FakeScope):
    """FakeScope that can also stop and hand back waveform data."""

    def __init__(self, wave_error_channels=(), lengths=None, **kwargs):
        super().__init__(**kwargs)
        self.wave_error_channels = set(wave_error_channels)
        self.lengths = lengths or {}
        self.calls = []

    def stop(self):
        self.calls.append("stop")

    def measure(self, name, channel):
        self.calls.append("measure")
        return super().measure(name, channel)

    def get_waveform_data(self, channel, points=0, fmt="BYTE"):
        self.calls.append(("wave", channel, fmt))
        if channel in self.wave_error_channels:
            raise TimeoutError("block read timed out")
        n = self.lengths.get(channel, 5)
        x_inc = 1e-9
        return {"x": [i * x_inc for i in range(n)],
                "y": [channel + 0.1 * i for i in range(n)],
                "preamble": {"x_increment": x_inc, "x_origin": 0.0,
                             "y_increment": 0.01}}


def test_waveform_csv_shares_one_time_column(tmp_path):
    scope = WaveScope(enabled=(1, 2))
    svc = make_service(scope)
    result = svc.capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf"},
                         save_image=False, save_waveform=True, waveform_format="csv")

    assert result.success, result.error
    assert result.waveform_path.endswith("wf_1.csv")
    with open(result.waveform_path) as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ["time_s", "CH1", "CH2"]
    assert len(rows) == 5
    assert float(rows[4]["CH2"]) == pytest.approx(2.4)
    # 16-bit transfer, so a 12-bit scope's resolution isn't truncated.
    assert ("wave", 1, "WORD") in scope.calls

    with open(result.csv_path) as f:
        assert list(csv.DictReader(f))[0]["waveform_file"] == "wf_1.csv"


def test_waveform_stops_scope_before_measuring(tmp_path):
    """Measurements and data must come from the same frozen acquisition."""
    scope = WaveScope()
    make_service(scope).capture(str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf"},
                                save_image=False, save_waveform=True)
    assert scope.calls[0] == "stop"
    assert scope.calls.index("measure") < scope.calls.index(("wave", 1, "WORD"))


def test_waveform_csv_unequal_lengths_get_own_time_columns(tmp_path):
    scope = WaveScope(enabled=(1, 2), lengths={1: 5, 2: 3})
    result = make_service(scope).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf"},
        save_image=False, save_waveform=True)

    with open(result.waveform_path) as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ["time_CH1_s", "CH1", "time_CH2_s", "CH2"]
    assert len(rows) == 5
    assert rows[4]["CH2"] == ""          # padded, not invented


def test_waveform_mat_contents(tmp_path):
    scipy_io = pytest.importorskip("scipy.io")
    scope = WaveScope(enabled=(1, 3))
    result = make_service(scope).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf", "Vin": "12"},
        save_image=False, save_waveform=True, waveform_format="mat")

    assert result.waveform_path.endswith("wf_1.mat")
    mat = scipy_io.loadmat(result.waveform_path, squeeze_me=True)
    assert mat["t"].shape == (5,)
    assert mat["CH3"][0] == pytest.approx(3.0)
    assert mat["fs"] == pytest.approx(1e9)
    assert list(mat["channels"]) == [1, 3]
    assert mat["meta"]["Vin"] == "12"
    assert mat["meta"]["model"] == "MSO64"


def test_one_failed_channel_download_keeps_the_others(tmp_path):
    scope = WaveScope(enabled=(1, 2), wave_error_channels=(2,))
    result = make_service(scope).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf"},
        save_image=False, save_waveform=True)

    assert result.success
    assert any("CH2 waveform download failed" in w for w in result.warnings)
    with open(result.waveform_path) as f:
        assert list(csv.DictReader(f))[0].keys() == {"time_s", "CH1"}


def test_all_downloads_failing_degrades_to_warning(tmp_path):
    scope = WaveScope(wave_error_channels=(1,))
    result = make_service(scope).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf"},
        save_image=False, save_waveform=True)

    assert result.success, "measurements must survive a failed waveform download"
    assert result.waveform_path is None
    assert any("Waveform not saved" in w for w in result.warnings)
    with open(result.csv_path) as f:
        assert "waveform_file" not in list(csv.DictReader(f))[0]


def test_unknown_waveform_format_fails_before_touching_scope(tmp_path):
    scope = WaveScope()
    result = make_service(scope).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "wf"},
        save_waveform=True, waveform_format="dat")
    assert not result.success
    assert scope.calls == []


def test_unresponsive_scope_skips_remaining_channels(tmp_path):
    """One channel where nothing answers means the rest would only time out too."""
    scope = FakeScope(enabled=(1, 2, 3), failing=FakeScope.MEASUREMENTS)
    result = make_service(scope).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "x"}, save_image=False)

    assert result.success
    assert any("CH2: measurements skipped" in w for w in result.warnings)
    assert any("CH3: measurements skipped" in w for w in result.warnings)
    with open(result.csv_path) as f:
        row = list(csv.DictReader(f))[0]
    assert row["CH3_vpp"] == ""


def test_capture_reports_progress(tmp_path):
    seen = []
    make_service(FakeScope(enabled=(1, 2))).capture(
        str(tmp_path / "run"), "{prefix}_{n}", {"prefix": "x"}, progress=seen.append)
    assert seen == ["Measuring CH1...", "Measuring CH2...", "Saving screenshot..."]
