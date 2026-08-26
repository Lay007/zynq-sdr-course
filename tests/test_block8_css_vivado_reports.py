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
    utilization = """
| Tool Version : Vivado v.2021.1 (win64)
| Device       : 7z020-clg400
| Slice LUTs*        | 1234 | 53200 | 2.32 |
| Slice Registers    | 2345 | 106400 | 2.20 |
| Block RAM Tile     | 2.0 | 140 | 1.43 |
| DSPs               | 8 | 220 | 3.64 |
"""
    timing = """
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
"""
    for stage in ("post_synthesis", "post_route"):
        (tmp_path / f"{top}_{stage}_utilization.rpt").write_text(
            utilization, encoding="utf-8"
        )
        (tmp_path / f"{top}_{stage}_timing_summary.rpt").write_text(
            timing, encoding="utf-8"
        )
    (tmp_path / f"{top}_post_route_status.rpt").write_text(
        """
Design Route Status
       # of routable nets..................... :        4567 :
           # of fully routed nets............. :        4567 :
       # of nets with routing errors.......... :           0 :
""",
        encoding="utf-8",
    )
    (tmp_path / f"{top}_post_route_drc.rpt").write_text(
        """
| Design State : Fully Routed
Violations found: 2
| Rule   | Severity | Description | Violations |
| DPOP-1 | Warning  | Pipelining  | 2          |
""",
        encoding="utf-8",
    )

    metrics = parse_metrics(tmp_path, "xc7z020clg400-2", 10.0)

    expected_utilization = {
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
    expected_timing = {
        "wns_ns": 0.25,
        "tns_ns": 0.0,
        "failing_endpoints": 0,
        "total_endpoints": 4200,
        "timing_met": True,
        "clock_name": "clk",
        "clock_period_ns": 10.0,
        "data_path_delay_ns": 9.5,
        "logic_levels": 12,
        "fmax_est_mhz": 102.564,
    }
    assert metrics["post_synthesis"] == {
        "utilization": expected_utilization,
        "timing": expected_timing,
    }
    assert metrics["post_route"] == {
        "utilization": expected_utilization,
        "timing": expected_timing,
        "route_status": {
            "design_state": "Fully Routed",
            "routable_nets": 4567,
            "fully_routed_nets": 4567,
            "unrouted_nets": 0,
            "nets_with_routing_errors": 0,
            "fully_routed": True,
        },
        "drc": {
            "violations": 2,
            "error_violations": 0,
            "errors_present": False,
        },
    }
    validate_metrics(metrics)


def test_validation_rejects_incomplete_metrics() -> None:
    metrics = {
        "post_synthesis": {
            "utilization": {"lut": 1, "ff": None, "bram_tiles": 0.0, "dsp": 0},
            "timing": {"wns_ns": None, "total_endpoints": None},
        },
        "post_route": {
            "utilization": {"lut": 1, "ff": 1, "bram_tiles": 0.0, "dsp": 0},
            "timing": {"wns_ns": 0.1, "total_endpoints": 1},
            "route_status": {},
            "drc": {},
        },
    }

    try:
        validate_metrics(metrics)
    except ValueError as error:
        assert str(error) == "Missing post_synthesis utilization metrics: ff"
    else:
        raise AssertionError("incomplete CSS Vivado metrics were accepted")


def test_validation_rejects_unrouted_implementation() -> None:
    complete_stage = {
        "utilization": {"lut": 1, "ff": 1, "bram_tiles": 0.0, "dsp": 0},
        "timing": {"wns_ns": 0.1, "total_endpoints": 1},
    }
    metrics = {
        "post_synthesis": complete_stage,
        "post_route": {
            **complete_stage,
            "route_status": {
                "design_state": "Fully Routed",
                "routable_nets": 10,
                "fully_routed_nets": 9,
                "unrouted_nets": 1,
                "nets_with_routing_errors": 0,
                "fully_routed": False,
            },
            "drc": {
                "violations": 0,
                "error_violations": 0,
                "errors_present": False,
            },
        },
    }

    try:
        validate_metrics(metrics)
    except ValueError as error:
        assert str(error) == "Vivado implementation is not fully routed"
    else:
        raise AssertionError("unrouted CSS implementation was accepted")
