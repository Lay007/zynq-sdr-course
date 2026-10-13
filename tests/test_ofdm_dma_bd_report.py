"""Checks on the committed Vivado reports of the OFDM modem (issue #48).

The PS + AXI DMA block design (tools/build_block8_ofdm_dma_bd.py) must expose
both register blocks to the PS and meet timing. No OFDM build may contain
latches: an incomplete combinational assignment in the IFFT once inferred
LDCE cells that only the block design's DRC reported (as gated clocks).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BD_DIR = ROOT / "reports" / "fpga" / "block8_ofdm_dma_bd_raw"
OOC_DIR = ROOT / "reports" / "fpga" / "block8_ofdm_vivado_ooc_raw"


def test_block_design_maps_modem_and_dma_registers() -> None:
    build = json.loads((BD_DIR / "ofdm_dma_build.json").read_text(encoding="utf-8"))
    names = {segment["name"] for segment in build["segments"]}
    assert names == {"SEG_modem_0_reg0", "SEG_axi_dma_0_Reg"}
    modem = next(s for s in build["segments"] if s["name"] == "SEG_modem_0_reg0")
    assert int(modem["range"], 16) == 0x1000
    assert build["ps7_params_write_errors"] == 0
    assert build["fclk0_actual_mhz"].startswith("100")


def test_block_design_meets_timing() -> None:
    text = (BD_DIR / "ofdm_dma_timing_summary.rpt").read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"WNS\(ns\).*?\n\s*-+.*?\n\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+([0-9]+)", text)
    assert match, "design timing summary not found"
    wns, tns, failing = float(match.group(1)), float(match.group(2)), int(match.group(3))
    assert wns >= 0.0 and tns == 0.0 and failing == 0


def test_no_ofdm_build_contains_latches() -> None:
    reports = sorted(OOC_DIR.glob("*_post_route_utilization.rpt")) + [BD_DIR / "ofdm_dma_utilization.rpt"]
    assert len(reports) > 10
    with_latches = [
        r.name for r in reports
        if re.search(r"^\|\s*LD[A-Z]*\s*\|\s*[1-9]", r.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    ]
    assert not with_latches, f"latches inferred in: {with_latches}"
