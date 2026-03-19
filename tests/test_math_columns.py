"""Unit tests for common/math_columns.py.

Tests cover:
  - MathEvaluator.evaluate_row  (arithmetic, chaining, error handling)
  - MathEvaluator.validate      (duplicates, name collisions, unknown vars)
  - MathConfig serialization    (to_dict / from_dict / save / load round-trip)
"""

import pytest
from common.math_columns import (
    MathColumn,
    MathConfig,
    MathEvaluator,
    save_math_config,
    load_math_config,
)


def make_config(*defs):
    """Build a MathConfig from (name, expression) pairs."""
    return MathConfig(columns=[MathColumn(name=n, expression=e) for n, e in defs])


# ── MathEvaluator.evaluate_row ─────────────────────────────────────────────

class TestEvaluateRow:
    def test_basic_arithmetic(self):
        cfg = make_config(("Power_W", "Vmeas * Imeas"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"Vmeas": "5.0", "Imeas": "2.0"})
        assert result["Power_W"] == pytest.approx(10.0)

    def test_chained_columns(self):
        """A later math column can reference an earlier one in the same row."""
        cfg = make_config(
            ("Power_W", "V * I"),
            ("Power_mW", "Power_W * 1000"),
        )
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"V": "3.3", "I": "0.1"})
        assert result["Power_W"] == pytest.approx(0.33)
        assert result["Power_mW"] == pytest.approx(330.0)

    def test_non_numeric_value_treated_as_zero(self):
        """Non-numeric row values (e.g. 'N/A') should not crash — treated as 0.0."""
        cfg = make_config(("Out", "X + 1"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"X": "N/A"})
        assert result["Out"] == pytest.approx(1.0)

    def test_unknown_variable_returns_error_string(self):
        cfg = make_config(("Bad", "totally_unknown_var * 2"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"something_else": "1"})
        assert result["Bad"] == "ERROR"

    def test_division_by_zero_returns_error_string(self):
        cfg = make_config(("Ratio", "A / B"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"A": "1", "B": "0"})
        assert result["Ratio"] == "ERROR"

    def test_safe_math_function_sqrt(self):
        cfg = make_config(("Root", "sqrt(X)"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"X": "9"})
        assert result["Root"] == pytest.approx(3.0)

    def test_safe_constant_pi_available(self):
        cfg = make_config(("Circle", "pi * r * r"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"r": "1.0"})
        assert result["Circle"] == pytest.approx(3.14159, rel=1e-4)

    def test_unsafe_import_blocked(self):
        """Expressions that attempt imports or attribute access should produce ERROR."""
        cfg = make_config(("Evil", "__import__('os').getcwd()"))
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({})
        assert result["Evil"] == "ERROR"

    def test_failed_column_does_not_stop_subsequent_columns(self):
        """An ERROR in one column shouldn't prevent evaluation of the next."""
        cfg = make_config(
            ("Bad", "unknown_col * 2"),
            ("Good", "V + 1"),
        )
        ev = MathEvaluator(cfg)
        result = ev.evaluate_row({"V": "4.0"})
        assert result["Bad"] == "ERROR"
        assert result["Good"] == pytest.approx(5.0)


# ── MathEvaluator.validate ─────────────────────────────────────────────────

class TestValidate:
    def test_valid_config_passes(self):
        cfg = make_config(("Power_W", "V * I"))
        ok, msg = MathEvaluator(cfg).validate(["V", "I"])
        assert ok is True
        assert msg == ""

    def test_unknown_variable_fails(self):
        cfg = make_config(("Out", "missing_col * 2"))
        ok, msg = MathEvaluator(cfg).validate(["V"])
        assert ok is False
        assert "missing_col" in msg or "unknown" in msg.lower()

    def test_duplicate_math_column_name_fails(self):
        cfg = make_config(("Power", "V * I"), ("Power", "V + I"))
        ok, msg = MathEvaluator(cfg).validate(["V", "I"])
        assert ok is False
        assert "duplicate" in msg.lower()

    def test_name_collision_with_existing_column_fails(self):
        """A math column whose name already exists in instrument headers should fail."""
        cfg = make_config(("V", "V * 2"))
        ok, msg = MathEvaluator(cfg).validate(["V", "I"])
        assert ok is False
        assert "conflicts" in msg.lower() or "V" in msg

    def test_chained_reference_to_prior_math_column_passes(self):
        """Column 2 referencing column 1 should be valid — column 1 is in scope."""
        cfg = make_config(
            ("Power_W", "V * I"),
            ("Power_mW", "Power_W * 1000"),
        )
        ok, msg = MathEvaluator(cfg).validate(["V", "I"])
        assert ok is True

    def test_empty_config_passes(self):
        ok, msg = MathEvaluator(MathConfig()).validate(["V", "I"])
        assert ok is True


# ── MathConfig serialization ───────────────────────────────────────────────

class TestMathConfigSerialization:
    def test_round_trip_via_file(self, tmp_path):
        cfg = make_config(("Power_W", "V * I"), ("Eff", "Power_W / P_in"))
        filepath = str(tmp_path / "math.json")
        save_math_config(cfg, filepath)
        loaded = load_math_config(filepath)
        assert loaded.get_column_names() == ["Power_W", "Eff"]
        assert loaded.columns[0].expression == "V * I"
        assert loaded.columns[1].expression == "Power_W / P_in"

    def test_from_dict_missing_description_defaults_to_empty(self):
        d = {"math_columns": [{"name": "X", "expression": "1 + 1"}]}
        cfg = MathConfig.from_dict(d)
        assert cfg.columns[0].description == ""

    def test_to_dict_and_back(self):
        cfg = make_config(("Out", "A + B"))
        loaded = MathConfig.from_dict(cfg.to_dict())
        assert loaded.columns[0].name == "Out"
        assert loaded.columns[0].expression == "A + B"

    def test_empty_config_is_empty(self):
        cfg = MathConfig()
        assert cfg.is_empty()
        assert cfg.get_column_names() == []

    def test_get_column_names_order_preserved(self):
        cfg = make_config(("Z", "1"), ("A", "2"), ("M", "3"))
        assert cfg.get_column_names() == ["Z", "A", "M"]
