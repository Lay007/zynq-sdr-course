#!/usr/bin/env python3
"""Run the executable course labs and create a reproducibility summary.

This script is intentionally lightweight: it runs representative Python labs
from the executable blocks and records pass/fail status plus generated artifacts.
It is used by the full-course smoke workflow and can also be executed locally.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_JSON = ROOT / "docs" / "assets" / "course_reproducibility_summary.json"
SUMMARY_MD = ROOT / "docs" / "assets" / "course_reproducibility_summary.md"


@dataclass(frozen=True)
class LabCommand:
    name: str
    command: list[str]
    expected_artifacts: list[str]


@dataclass(frozen=True)
class LabResult:
    name: str
    return_code: int
    passed: bool
    missing_artifacts: list[str]


LABS: list[LabCommand] = [
    LabCommand(
        "Block 6 / Lab 6.4 synthetic RF capture analysis",
        [sys.executable, "blocks/block_06_rf_frontend_and_ad9363/python/lab_6_4_synthetic_rf_capture_analysis.py"],
        [
            "docs/assets/lab64_synthetic_rf_capture_fft.png",
            "docs/assets/lab64_synthetic_rf_capture_time.png",
            "docs/assets/lab64_synthetic_rf_capture_metrics.json",
        ],
    ),
    LabCommand(
        "Block 7 / Lab 7.3 TX/RX loopback metrics",
        [sys.executable, "blocks/block_07_tx_rx_chains/python/lab_7_3_tx_rx_loopback_metrics.py"],
        [
            "docs/assets/lab73_tx_rx_loopback_spectrum.png",
            "docs/assets/lab73_tx_constellation.png",
            "docs/assets/lab73_rx_constellation_after_ddc.png",
            "docs/assets/lab73_tx_rx_loopback_metrics.json",
        ],
    ),
    LabCommand(
        "Block 8 / Lab 8.4 end-to-end synchronization chain",
        [sys.executable, "blocks/block_08_modulation_and_synchronization/python/lab_8_4_end_to_end_sync_chain.py"],
        [
            "docs/assets/lab84_sync_constellation_raw.png",
            "docs/assets/lab84_sync_constellation_after_timing.png",
            "docs/assets/lab84_sync_constellation_final.png",
            "docs/assets/lab84_sync_chain_metrics.json",
        ],
    ),
    LabCommand(
        "Block 9 / Lab 9.3 multi-format IQ reader",
        [sys.executable, "blocks/block_09_recording_and_analysis_tools/python/lab_9_3_multi_format_iq_reader.py"],
        [
            "docs/assets/lab93_multiformat_iq_metrics.json",
            "docs/assets/lab93_multiformat_iq_spectrum_ci16.png",
            "docs/assets/lab93_multiformat_iq_spectrum_cu8.png",
            "docs/assets/lab93_multiformat_iq_spectrum_cf32.png",
        ],
    ),
]


def run_lab(lab: LabCommand) -> LabResult:
    print(f"\n=== {lab.name} ===")
    completed = subprocess.run(lab.command, cwd=ROOT, text=True)
    missing = [p for p in lab.expected_artifacts if not (ROOT / p).is_file() or (ROOT / p).stat().st_size == 0]
    passed = completed.returncode == 0 and not missing
    return LabResult(lab.name, completed.returncode, passed, missing)


def write_summary(results: list[LabResult]) -> None:
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "passed": all(r.passed for r in results),
        "lab_count": len(results),
        "results": [asdict(r) for r in results],
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Course reproducibility summary", "", f"Overall result: **{'PASS' if payload['passed'] else 'FAIL'}**", ""]
    lines.append("| Lab | Result | Missing artifacts |")
    lines.append("|---|---:|---|")
    for r in results:
        missing = ", ".join(r.missing_artifacts) if r.missing_artifacts else "—"
        lines.append(f"| {r.name} | {'PASS' if r.passed else 'FAIL'} | {missing} |")
    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run representative executable course labs.")
    parser.add_argument("--quick", action="store_true", help="Reserved for future smaller smoke subsets; currently runs the representative set.")
    args = parser.parse_args()
    _ = args.quick

    results = [run_lab(lab) for lab in LABS]
    write_summary(results)
    for r in results:
        print(f"{r.name}: {'PASS' if r.passed else 'FAIL'}")
        if r.missing_artifacts:
            print("  Missing:", ", ".join(r.missing_artifacts))
    print(f"\nSummary JSON: {SUMMARY_JSON}")
    print(f"Summary Markdown: {SUMMARY_MD}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
