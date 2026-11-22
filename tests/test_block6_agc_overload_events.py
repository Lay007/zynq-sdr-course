"""No-board regression for Lab 6.12 event-log interpretation."""
import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = (Path(__file__).resolve().parents[1] /
               "blocks/block_06_rf_frontend_and_ad9363/python/lab_6_12_analyze_events.py")
SPEC = importlib.util.spec_from_file_location("lab612_events", MODULE_PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_event_latency_and_count():
    result = mod.analyze([(100, "step"), (102, "lmt"), (110, "gain_change"),
                          (200, "step"), (204, "large_adc")], 1_000_000)
    assert result["event_counts"]["step"] == 2
    assert result["step_windows"][0]["first_event_latency_us"]["lmt"] == 2.0
    assert result["step_windows"][1]["first_event_latency_us"]["large_adc"] == 4.0
    assert result["lmt_first_latency_mean_us"] == 2.0


def test_no_step_has_no_claimed_latency():
    result = mod.analyze([(50, "lmt")], 100_000_000)
    assert not result["step_windows"]
    assert result["lmt_first_latency_mean_us"] is None


@pytest.mark.parametrize("rows,hz", [
    ([(2, "lmt"), (1, "step")], 1_000_000),
    ([(2, "invented")], 1_000_000),
    ([(-2, "lmt")], 1_000_000),
    ([(2, "lmt")], 0),
])
def test_invalid_data_rejected(rows, hz):
    with pytest.raises(ValueError):
        mod.analyze(rows, hz)
