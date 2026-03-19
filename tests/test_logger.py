"""Unit tests for common/logger.py.

Tests cover:
  - parse_serial_params  (string parsing and validation)
  - build_headers        (column ordering and conditional inclusion)
  - StimulusConfig       (validate method branches)
  - StimulusGenerator    (step count and value correctness)
"""

import pytest
from common.logger import (
    parse_serial_params,
    build_headers,
    RecordConfig,
    OscRecordConfig,
    StimulusConfig,
    StimulusType,
    SweepMode,
    StepMode,
    StimulusGenerator,
    COL_TIME,
    COL_SERIAL,
    COL_DMM_MEAS1,
    COL_PS_VSET1, COL_PS_VMEAS1, COL_PS_IMEAS1,
    COL_PS_VSET2, COL_PS_VMEAS2, COL_PS_IMEAS2,
    COL_FG_FREQ, COL_FG_WAVEFORM,
    COL_STIM_PS_VOLTAGE,
    COL_STIMULUS_STEP,
)


# ── parse_serial_params ────────────────────────────────────────────────────

class TestParseSerialParams:
    def test_basic_comma_separated(self):
        assert parse_serial_params("SN,BoardRev,FW") == ["SN", "BoardRev", "FW"]

    def test_whitespace_around_names_is_stripped(self):
        assert parse_serial_params("SN , BoardRev , FW") == ["SN", "BoardRev", "FW"]

    def test_empty_string_returns_empty_list(self):
        assert parse_serial_params("") == []

    def test_none_returns_empty_list(self):
        assert parse_serial_params(None) == []

    def test_single_field(self):
        assert parse_serial_params("SN") == ["SN"]

    def test_trailing_comma_raises(self):
        with pytest.raises(ValueError):
            parse_serial_params("SN,BoardRev,")

    def test_leading_comma_raises(self):
        with pytest.raises(ValueError):
            parse_serial_params(",SN,BoardRev")

    def test_consecutive_commas_raise(self):
        with pytest.raises(ValueError):
            parse_serial_params("SN,,BoardRev")


# ── build_headers ──────────────────────────────────────────────────────────

class TestBuildHeaders:
    def _cfg(self, **kwargs):
        return RecordConfig(**kwargs)

    def test_always_starts_with_time(self):
        assert build_headers(self._cfg())[0] == COL_TIME

    def test_nothing_enabled_yields_only_time(self):
        assert build_headers(self._cfg()) == [COL_TIME]

    def test_dmm_enabled(self):
        headers = build_headers(self._cfg(use_dmm=True))
        assert COL_DMM_MEAS1 in headers

    def test_ps_channel_1_includes_only_ch1_columns(self):
        headers = build_headers(self._cfg(use_ps=True, ps_channel=1))
        assert COL_PS_VSET1 in headers
        assert COL_PS_VMEAS1 in headers
        assert COL_PS_IMEAS1 in headers
        assert COL_PS_VSET2 not in headers
        assert COL_PS_VMEAS2 not in headers
        assert COL_PS_IMEAS2 not in headers

    def test_ps_channel_2_includes_both_channels(self):
        headers = build_headers(self._cfg(use_ps=True, ps_channel=2))
        for col in [COL_PS_VSET1, COL_PS_VMEAS1, COL_PS_IMEAS1,
                    COL_PS_VSET2, COL_PS_VMEAS2, COL_PS_IMEAS2]:
            assert col in headers

    def test_fg_enabled(self):
        headers = build_headers(self._cfg(use_fg=True))
        assert COL_FG_FREQ in headers
        assert COL_FG_WAVEFORM in headers

    def test_serial_with_named_columns(self):
        headers = build_headers(self._cfg(use_ser=True, serial_params="SN,BoardRev"))
        assert "SN" in headers
        assert "BoardRev" in headers
        assert COL_SERIAL not in headers

    def test_serial_with_no_params_uses_fallback_column(self):
        headers = build_headers(self._cfg(use_ser=True, serial_params=""))
        assert COL_SERIAL in headers

    def test_stimulus_columns_appended_at_end(self):
        stim = StimulusConfig(
            enabled=True,
            stimulus_type=StimulusType.PS_VOLTAGE,
            start_value=1.0, stop_value=5.0, step_value=1.0,
        )
        headers = build_headers(self._cfg(use_dmm=True), stimulus_config=stim)
        assert headers[-2] == COL_STIM_PS_VOLTAGE
        assert headers[-1] == COL_STIMULUS_STEP

    def test_disabled_stimulus_adds_no_columns(self):
        stim = StimulusConfig(enabled=False, stimulus_type=StimulusType.PS_VOLTAGE)
        headers = build_headers(self._cfg(), stimulus_config=stim)
        assert headers == [COL_TIME]

    def test_osc_columns_included_when_configured(self):
        osc_cfg = OscRecordConfig(channels={1: ["vpp", "frequency"]})
        headers = build_headers(self._cfg(use_osc=True, osc_config=osc_cfg))
        assert "OSC_CH1_Vpp" in headers
        assert "OSC_CH1_Frequency" in headers

    def test_column_order_time_ser_dmm_ps_fg(self):
        """Time → SER → DMM → PS → FG ordering must be preserved."""
        cfg = self._cfg(use_ser=True, serial_params="SN",
                        use_dmm=True, use_ps=True, ps_channel=1, use_fg=True)
        h = build_headers(cfg)
        assert h.index(COL_TIME) < h.index("SN") < h.index(COL_DMM_MEAS1) \
               < h.index(COL_PS_VSET1) < h.index(COL_FG_FREQ)


# ── StimulusConfig.validate ────────────────────────────────────────────────

class TestStimulusConfigValidate:
    def _stim(self, **kwargs):
        defaults = dict(
            enabled=True,
            stimulus_type=StimulusType.PS_VOLTAGE,
            start_value=1.0, stop_value=5.0, step_value=1.0,
        )
        defaults.update(kwargs)
        return StimulusConfig(**defaults)

    def test_disabled_config_always_valid(self):
        ok, _ = StimulusConfig(enabled=False).validate()
        assert ok is True

    def test_no_stimulus_type_fails(self):
        ok, _ = self._stim(stimulus_type=StimulusType.NONE).validate()
        assert ok is False

    def test_same_start_and_stop_fails(self):
        ok, _ = self._stim(start_value=3.0, stop_value=3.0).validate()
        assert ok is False

    def test_step_larger_than_range_fails(self):
        ok, _ = self._stim(start_value=1.0, stop_value=2.0, step_value=5.0).validate()
        assert ok is False

    def test_zero_step_value_fails(self):
        ok, _ = self._stim(step_value=0.0).validate()
        assert ok is False

    def test_negative_settling_time_fails(self):
        ok, _ = self._stim(settling_time=-0.1).validate()
        assert ok is False

    def test_valid_config_passes(self):
        ok, msg = self._stim().validate()
        assert ok is True
        assert msg == ""

    def test_num_steps_mode_less_than_2_fails(self):
        ok, _ = self._stim(step_mode=StepMode.NUM_STEPS, step_value=1).validate()
        assert ok is False

    def test_num_steps_mode_2_or_more_passes(self):
        ok, _ = self._stim(step_mode=StepMode.NUM_STEPS, step_value=5).validate()
        assert ok is True


# ── StimulusGenerator ──────────────────────────────────────────────────────

class TestStimulusGenerator:
    def _gen(self, **kwargs):
        defaults = dict(
            enabled=True,
            stimulus_type=StimulusType.PS_VOLTAGE,
            start_value=1.0, stop_value=5.0, step_value=1.0,
            sweep_mode=SweepMode.LINEAR,
            step_mode=StepMode.INCREMENT,
        )
        defaults.update(kwargs)
        return StimulusGenerator(StimulusConfig(**defaults))

    def test_linear_step_count(self):
        gen = self._gen(start_value=0.0, stop_value=4.0, step_value=1.0)
        assert len(gen) == 5

    def test_linear_values_correct(self):
        gen = self._gen(start_value=1.0, stop_value=3.0, step_value=1.0)
        assert list(gen) == pytest.approx([1.0, 2.0, 3.0])

    def test_num_steps_mode_count(self):
        gen = self._gen(step_mode=StepMode.NUM_STEPS, step_value=5)
        assert len(gen) == 5

    def test_num_steps_mode_includes_start_and_stop(self):
        gen = self._gen(start_value=0.0, stop_value=10.0,
                        step_mode=StepMode.NUM_STEPS, step_value=3)
        values = list(gen)
        assert values[0] == pytest.approx(0.0)
        assert values[-1] == pytest.approx(10.0)

    def test_log_sweep_start_and_end_values(self):
        gen = self._gen(start_value=10.0, stop_value=1000.0,
                        sweep_mode=SweepMode.LOGARITHMIC,
                        step_mode=StepMode.NUM_STEPS, step_value=3)
        values = list(gen)
        assert len(values) == 3
        assert values[0] == pytest.approx(10.0)
        assert values[-1] == pytest.approx(1000.0)

    def test_log_sweep_rejects_nonpositive_start(self):
        with pytest.raises(ValueError):
            self._gen(start_value=0.0, stop_value=100.0,
                      sweep_mode=SweepMode.LOGARITHMIC,
                      step_mode=StepMode.NUM_STEPS, step_value=5)

    def test_generator_is_re_iterable(self):
        """Iterating twice should yield the same values."""
        gen = self._gen(start_value=0.0, stop_value=2.0, step_value=1.0)
        assert list(gen) == list(gen)

    def test_disabled_generator_is_empty(self):
        gen = StimulusGenerator(StimulusConfig(enabled=False))
        assert len(gen) == 0
        assert list(gen) == []
