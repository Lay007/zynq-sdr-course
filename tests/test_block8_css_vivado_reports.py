from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from generate_block8_css_vivado_reports import (  # noqa: E402
    parse_metrics,
    validate_metrics,
)


def test_parse_block8_css_vivado_metrics(tmp_path: Path) -> None:
    top = "css_sf7_sequential_detector"
    (tmp_path / f"{top}_utilization.rpt").write_text(
        """
| Tool Version : Vivado v.2021.1 (win64)
| Device       : 7z020-clg400
| Slice LUTs*        | 1234 | 53200 | 2.32 |
| Slice Registers    | 2345 | 106400 | 2.20 |
| Block RAM Tile     | 2.0 | 140 | 1.43 |
| DSPs               | 8 | 220 | 3.64 |
""",
        encoding="utf-8",
    )
    (tmp_path / f"{top}_timing_summary.rpt").write_text(
        """
Design Timing Summary
---------------------
WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints
-------      -------  ---------------------  -------------------
0.250        0.000    0                      4200

Clock Summary
Clock  Waveform(ns)  Period(ns)  Frequency(MHz)
-----  ------------  ----------  --------------
clk    {0.000 5.000}  10.000      100.000

Data Path Delay: 9.500ns
Logic Levels: 12
""",
        encoding="utf-8",
    )

    metrics = parse_metrics(tmp_path, "xc7z020clg400-2", 10.0)

    assert metrics["utilization"] == {
        "lut": 1234,
        "ff": 2345,
        "bram_tiles": 2.0,
        "dsp": 8,
    }
    assert metrics["latency_cycles"] == {
        "dft_transform": 16640,
        "final_input_to_done": 16644,
        "first_input_to_done": 16771,
        "symbol_initiation_interval": 16772,
    }
    assert metrics["throughput_at_target_clock"] == {
        "symbol_decisions_per_second": 5962.318,
        "sustained_input_samples_per_second": 763176.723,
    }
    assert metrics["timing"] == {
        "wns_ns": 0.25,
        "tns_ns": 0.0,
        "failing_endpoints": 0,
        "total_endpoints": 4200,
        "timing_met": True,
        "clock_name": "clk",
        "clock_period_ns": 10.0,
        "data_path_delay_ns": 9.5,
        "logic_levels": 12,
        "post_synthesis_fmax_est_mhz": 102.564,
    }
    validate_metrics(metrics)


def test_validation_rejects_incomplete_metrics() -> None:
    metrics = {
        "utilization": {"lut": 1, "ff": None, "bram_tiles": 0.0, "dsp": 0},
        "timing": {"wns_ns": None, "total_endpoints": None},
    }

    try:
        validate_metrics(metrics)
    except ValueError as error:
        assert str(error) == "Missing utilization metrics: ff"
    else:
        raise AssertionError("incomplete CSS Vivado metrics were accepted")
