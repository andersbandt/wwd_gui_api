"""Unit tests for common/csv_helper.py.

Focuses on add_row_from_dict since it contains the only non-trivial logic
(column ordering, missing keys, None handling). The other methods are thin
wrappers around the stdlib csv module and are exercised incidentally.
"""

import pytest
from common.csv_helper import CSVHelper


@pytest.fixture
def helper(tmp_path):
    """A freshly initialized CSVHelper with three columns."""
    h = CSVHelper(str(tmp_path / "test.csv"), ["Time", "Voltage", "Current"])
    h.initialize_file()
    return h


class TestCSVHelperInit:
    def test_header_row_written_on_initialize(self, helper):
        data = helper.read_data()
        assert data[0] == ["Time", "Voltage", "Current"]

    def test_file_exists_after_initialize(self, helper):
        assert helper.file_path.exists()


class TestAddRow:
    def test_single_row_appended(self, helper):
        helper.add_row(["0.0", "3.3", "0.1"])
        data = helper.read_data()
        assert data[1] == ["0.0", "3.3", "0.1"]

    def test_multiple_rows_via_add_rows(self, helper):
        helper.add_rows([["1.0", "3.3", "0.1"], ["2.0", "3.4", "0.2"]])
        data = helper.read_data()
        assert len(data) == 3  # header + 2


class TestAddRowFromDict:
    def test_values_written_in_header_order(self, helper):
        # Dict is intentionally in a different order than the headers
        helper.add_row_from_dict({"Current": "0.5", "Time": "1.0", "Voltage": "5.0"})
        data = helper.read_data()
        assert data[1] == ["1.0", "5.0", "0.5"]

    def test_missing_key_written_as_empty_string(self, helper):
        helper.add_row_from_dict({"Time": "2.0", "Voltage": "3.3"})  # Current omitted
        data = helper.read_data()
        assert data[1] == ["2.0", "3.3", ""]

    def test_extra_key_is_silently_ignored(self, helper):
        helper.add_row_from_dict({
            "Time": "1.0", "Voltage": "3.3", "Current": "0.1", "Extra": "99"
        })
        data = helper.read_data()
        assert data[1] == ["1.0", "3.3", "0.1"]

    def test_none_value_written_as_empty_string(self, helper):
        helper.add_row_from_dict({"Time": "1.0", "Voltage": None, "Current": "0.1"})
        data = helper.read_data()
        assert data[1][1] == ""

    def test_custom_default_used_for_missing_key(self, tmp_path):
        h = CSVHelper(str(tmp_path / "custom.csv"), ["A", "B", "C"])
        h.initialize_file()
        h.add_row_from_dict({"A": "1"}, default="N/A")
        data = h.read_data()
        assert data[1] == ["1", "N/A", "N/A"]

    def test_read_data_as_dict_matches_written_values(self, helper):
        helper.add_row_from_dict({"Time": "0.5", "Voltage": "3.3", "Current": "0.2"})
        rows = helper.read_data_as_dict()
        assert rows[0]["Voltage"] == "3.3"
        assert rows[0]["Current"] == "0.2"


class TestDeleteFile:
    def test_file_removed_after_delete(self, helper):
        helper.delete_file()
        assert not helper.file_path.exists()

    def test_delete_on_nonexistent_file_does_not_raise(self, tmp_path):
        h = CSVHelper(str(tmp_path / "ghost.csv"), ["A"])
        h.delete_file()  # file was never created — should not raise
