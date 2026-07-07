from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from generate_integrated_vivado_reports import (  # noqa: E402
    parse_integrated_metrics,
    validate_integrated_metrics,
)


def test_parse_integrated_metrics_extracts_route_timing_and_resources() -> None:
    utilization = """
| Tool Version : Vivado v.2021.1
| Device       : 7z020-clg400
| Slice LUTs*        | 1234 | 53200 | 2.32 |
| Slice Registers    | 2345 | 106400 | 2.20 |
| Block RAM Tile     | 12.5 | 140 | 8.93 |
| DSPs               | 20 | 220 | 9.09 |
"""
    timing = """
Design Timing Summary
---------------------
WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints
-------      -------  ---------------------  -------------------
0.125        0.000    0                      4200
"""
    route = """
# of routable nets..................... :       30000 :
    # of fully routed nets............. :       30000 :
# of nets with routing errors.......... :           0 :
"""

    metrics = parse_integrated_metrics(utilization, timing, route)

    assert metrics["utilization"] == {"lut": 1234, "ff": 2345, "bram_tiles": 12.5, "dsp": 20}
    assert metrics["timing"]["wns_ns"] == 0.125
    assert metrics["timing"]["timing_met"] is True
    assert metrics["route"] == {
        "routable_nets": 30000,
        "fully_routed_nets": 30000,
        "routing_errors": 0,
        "unrouted_nets": 0,
        "fully_routed": True,
    }
    validate_integrated_metrics(metrics)


def test_validation_rejects_timing_failure() -> None:
    metrics = {
        "utilization": {"lut": 1, "ff": 2, "bram_tiles": 0.0, "dsp": 0},
        "timing": {"wns_ns": -0.1, "tns_ns": -1.0, "timing_met": False},
        "route": {"routing_errors": 0, "fully_routed": True},
    }

    try:
        validate_integrated_metrics(metrics)
    except ValueError as error:
        assert str(error) == "Routed design does not meet timing"
    else:
        raise AssertionError("A timing failure must not be promoted")

    validate_integrated_metrics(metrics, require_timing=False)
