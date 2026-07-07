#!/usr/bin/env python3
"""Aggregate Lab 11.27 JSON runs into a clean-boot qualification summary."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any


def expand_paths(patterns: list[str]) -> list[Path]:
    paths = {Path(match).resolve() for pattern in patterns for match in glob.glob(pattern)}
    if not paths:
        raise FileNotFoundError("No Lab 11.27 JSON files matched the supplied patterns")
    return sorted(paths)


def aggregate_runs(paths: list[Path], start_offset: int) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    bitstream_md5s: set[str] = set()
    selected_attempts = 0
    selected_zero = 0

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        summary_mode = payload.get("summary", {}).get("mode")
        legacy_fabric = summary_mode == "qpsk_digital_loopback" and payload.get("loopback") == "fabric"
        if summary_mode != "qpsk_fabric_loopback" and not legacy_fabric:
            raise ValueError(f"{path}: expected qpsk_fabric_loopback evidence")
        bitstream_md5 = str(payload.get("bitstream", {}).get("md5") or "")
        if not bitstream_md5:
            raise ValueError(f"{path}: missing bitstream MD5")
        bitstream_md5s.add(bitstream_md5)

        attempts = [
            row for row in payload.get("sweep", []) if int(row["start_offset"]) == start_offset
        ]
        zero_attempts = [
            row
            for row in attempts
            if int(row.get("received_symbols") or 0) == int(payload["symbol_count"])
            and int(row.get("total_bit_errors") or 0) == 0
        ]
        selected_attempts += len(attempts)
        selected_zero += len(zero_attempts)
        reboot_ok = bool(payload.get("reboot_after", {}).get("ok"))
        runs.append(
            {
                "file": path.name,
                "run_tag": payload.get("run_tag"),
                "attempts_at_offset": len(attempts),
                "zero_error_attempts_at_offset": len(zero_attempts),
                "boot_success": bool(zero_attempts),
                "reboot_to_stock_ok": reboot_ok,
            }
        )

    if len(bitstream_md5s) != 1:
        raise ValueError(f"Mixed bitstream MD5 values: {sorted(bitstream_md5s)}")

    successful_boots = sum(run["boot_success"] for run in runs)
    safe_reboots = sum(run["reboot_to_stock_ok"] for run in runs)
    return {
        "mode": "qpsk_fabric_loopback_clean_boot_qualification",
        "start_offset": start_offset,
        "bitstream_md5": next(iter(bitstream_md5s)),
        "boot_sessions": len(runs),
        "successful_boot_sessions": successful_boots,
        "boot_success_rate": successful_boots / len(runs),
        "safe_reboot_sessions": safe_reboots,
        "attempts_at_offset": selected_attempts,
        "zero_error_attempts_at_offset": selected_zero,
        "zero_error_rate_at_offset": selected_zero / selected_attempts if selected_attempts else 0.0,
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+", help="JSON paths or glob patterns")
    parser.add_argument("--start-offset", type=int, default=62)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()

    summary = aggregate_runs(expand_paths(args.patterns), args.start_offset)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
