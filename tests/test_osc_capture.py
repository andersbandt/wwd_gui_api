"""Capture naming and run-CSV behaviour for the OSC tab. No hardware needed."""

import os
import csv
import pytest

from common import capture_naming
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

    def __init__(self, screenshot_error=None, enabled=(1,)):
        self.screenshot_error = screenshot_error
        self.enabled = list(enabled)

    def get_enabled_channels(self):
        return self.enabled

    def measure_all(self, channel):
        return {"vpp": 1.5 * channel, "vavg": None}

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
