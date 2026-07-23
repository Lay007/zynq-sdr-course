#!/usr/bin/env python3
"""Post-condition for a course overlay build: does the artifact match the requested mode?

Why this exists. `rebuild_vendor_xpr_snapshot_course_overlay.tcl` defaults to overlay mode
`gpreg_only`; the course modem needs `COURSE_OVERLAY_MODE=bridge_txrx_mux`. Launched without that
variable the flow completes with zero errors, exports an XSA, prints "Rebuilt patched snapshot
overlay project", and reports comfortable timing (WNS +0.344 ns, all nets routed) -- for a design
that does not contain the modem at all. Every signal a human normally trusts said success.

The only reliable tell was the shape of the design: 13,887 LUTs and no DSPs against 35,724 LUTs and
176 DSPs for a real course build. So this script checks the artifact against the intent instead of
against "did the tool exit 0", and refuses to be satisfied by a green report about the wrong thing.

Note what is deliberately NOT used as evidence: the routed timing summary lists only the worst paths
per clock group, so the absence of course cell names there proves nothing when timing is comfortably
met. That was a wrong inference made once already.

    python verify_course_build.py --mode bridge_txrx_mux
    python verify_course_build.py --mode gpreg_only --build-dir tmp/other/zc702
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD = ROOT / "tmp" / "vendor_xpr_course_overlay" / "zc702"

# A bridge build carries the QPSK modem: its multipliers and matched filters dominate the DSP
# column, which a vendor-only shell simply does not use. Thresholds sit far from both observed
# populations (course 35,724 LUT / 176 DSP, vendor-only 13,887 LUT / 0 DSP).
MODE_EXPECTATIONS = {
    "bridge_txrx_mux": {"min_luts": 25000, "min_dsps": 100, "modem": True},
    "bridge_rx_only": {"min_luts": 20000, "min_dsps": 60, "modem": True},
    "gpreg_only": {"min_luts": 0, "min_dsps": 0, "modem": False},
}


def parse_utilization(path: Path) -> dict[str, int]:
    """Pull the flat resource counts out of a Vivado utilization report."""
    wanted = {"Slice LUTs": "luts", "Slice Registers": "regs",
              "Block RAM Tile": "bram", "DSPs": "dsps"}
    found: dict[str, int] = {}
    for line in path.read_text(errors="ignore").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 3:
            continue
        for label, key in wanted.items():
            if cells[1] == label and key not in found:
                try:
                    found[key] = int(cells[2])
                except ValueError:
                    pass
    return found


def parse_timing(path: Path) -> dict[str, float] | None:
    text = path.read_text(errors="ignore")
    marker = text.find("Design Timing Summary")
    if marker < 0:
        return None
    for line in text[marker:].splitlines():
        nums = re.findall(r"-?\d+\.\d+|\bNA\b", line)
        if len(nums) >= 4 and line.strip() and not line.strip().startswith("-"):
            try:
                return {"wns": float(nums[0]), "tns": float(nums[1]),
                        "whs": float(nums[2]), "ths": float(nums[3])}
            except ValueError:
                continue
    return None


def parse_route(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in path.read_text(errors="ignore").splitlines():
        m = re.search(r"#\s+of\s+(.*?)\.*\s*:\s*(\d+)", line)
        if not m:
            continue
        label = m.group(1).strip().lower()
        if "routable nets" in label:
            out["routable"] = int(m.group(2))
        elif "fully routed" in label:
            out["routed"] = int(m.group(2))
        elif "routing errors" in label:
            out["errors"] = int(m.group(2))
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=sorted(MODE_EXPECTATIONS))
    ap.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD)
    ap.add_argument("--allow-timing-fail", action="store_true",
                    help="report negative slack without failing (a timing-closure sweep may want this)")
    args = ap.parse_args()

    impl = args.build_dir / "zc702.runs" / "impl_1"
    expect = MODE_EXPECTATIONS[args.mode]
    problems: list[str] = []

    util_path = impl / "system_top_utilization_placed.rpt"
    if not util_path.is_file():
        print(f"FAIL: no utilization report at {util_path}")
        return 1
    util = parse_utilization(util_path)
    print(f"utilization: LUTs={util.get('luts')} regs={util.get('regs')} "
          f"BRAM={util.get('bram')} DSPs={util.get('dsps')}")

    if expect["modem"]:
        if util.get("luts", 0) < expect["min_luts"]:
            problems.append(f"LUTs {util.get('luts')} < {expect['min_luts']}: the course modem is "
                            f"missing -- most likely COURSE_OVERLAY_MODE was not set to {args.mode}")
        if util.get("dsps", 0) < expect["min_dsps"]:
            problems.append(f"DSPs {util.get('dsps')} < {expect['min_dsps']}: no modem multipliers "
                            f"in the placed design")

    route_path = impl / "system_top_route_status.rpt"
    if route_path.is_file():
        route = parse_route(route_path)
        print(f"route: {route.get('routed')}/{route.get('routable')} fully routed, "
              f"{route.get('errors')} error(s)")
        if route.get("errors", 1) != 0:
            problems.append(f"{route.get('errors')} routing error(s)")
        if route.get("routed") != route.get("routable"):
            problems.append("not every routable net is fully routed")
    else:
        problems.append("no route status report")

    timing_path = impl / "system_top_timing_summary_routed.rpt"
    timing = parse_timing(timing_path) if timing_path.is_file() else None
    if timing:
        print(f"timing: WNS={timing['wns']:+.3f} TNS={timing['tns']:+.3f} "
              f"WHS={timing['whs']:+.3f} THS={timing['ths']:+.3f} ns")
        bad = [k for k in ("wns", "whs") if timing[k] < 0] + \
              [k for k in ("tns", "ths") if timing[k] < 0]
        if bad and not args.allow_timing_fail:
            problems.append(f"timing not met ({', '.join(sorted(set(bad))).upper()})")
    else:
        problems.append("no routed timing summary")

    bit = impl / "system_top.bit"
    if bit.is_file():
        print(f"bitstream: {bit.stat().st_size} bytes\nsha256: {sha256(bit)}")
    else:
        problems.append("no bitstream produced")

    if problems:
        print(f"\nFAIL ({len(problems)}):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"\nPASS: artifact matches overlay mode '{args.mode}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
