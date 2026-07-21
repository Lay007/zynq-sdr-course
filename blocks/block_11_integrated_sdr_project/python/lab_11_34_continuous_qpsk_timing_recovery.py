#!/usr/bin/env python3
"""Lab 11.34 - compare equal-budget fixed-sampler and Gardner hardware campaigns.

Acquire the two raw campaigns with the Lab 11.32 runner and the same candidate
bitstream/settings.  The only intended receiver difference is gp_ctrl[14]:

  python lab_11_32_two_board_fabric_coarse_cfo.py --json-out baseline.json
  python lab_11_32_two_board_fabric_coarse_cfo.py --timing-recovery --json-out gardner.json

This post-processor keeps no-lock attempts in the denominator, checks that the
budgets and CFO grids match, plots full-frame and BER=0 attempt rates, and emits a
single auditable Lab 11.34 JSON.  It performs no board access itself.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "docs" / "assets"


def wilson(successes: int, attempts: int, z: float = 1.96) -> list[float]:
    if attempts == 0:
        return [0.0, 0.0]
    p = successes / attempts
    denominator = 1.0 + z * z / attempts
    center = (p + z * z / (2.0 * attempts)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / attempts + z * z / (4.0 * attempts**2)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def load_campaign(path: Path, *, expect_timing: bool) -> dict:
    payload = json.loads(path.read_text())
    timing = bool(payload.get("timing_recovery", False))
    if timing != expect_timing:
        state = "enabled" if expect_timing else "disabled"
        raise ValueError(f"{path}: expected timing recovery {state}, got {timing}")
    return payload


def aggregate(payload: dict) -> dict:
    rows = [point["coarse_on"] for point in payload["points"]]
    attempts = sum(int(row["attempts"]) for row in rows)
    clean = sum(int(row["clean_frames"]) for row in rows)
    full = sum(int(row["full_frames"]) for row in rows)
    return {
        "attempts": attempts,
        "clean_frames": clean,
        "full_frames": full,
        "clean_attempt_rate": clean / attempts if attempts else 0.0,
        "clean_attempt_rate_wilson95": wilson(clean, attempts),
        "lock_rate": full / attempts if attempts else 0.0,
        "lock_rate_wilson95": wilson(full, attempts),
    }


def compare(baseline: dict, gardner: dict) -> dict:
    base_cfos = [float(point["cfo_hz"]) for point in baseline["points"]]
    gardner_cfos = [float(point["cfo_hz"]) for point in gardner["points"]]
    equal_budget = (
        base_cfos == gardner_cfos
        and baseline["start_offsets"] == gardner["start_offsets"]
        and baseline["retries_per_offset"] == gardner["retries_per_offset"]
    )
    if not equal_budget:
        raise ValueError("campaign CFO grids, offsets, or retry budgets do not match")

    base_summary = aggregate(baseline)
    gardner_summary = aggregate(gardner)
    clean_improved = gardner_summary["clean_attempt_rate"] > base_summary["clean_attempt_rate"]
    lock_preserved = gardner_summary["lock_rate"] >= base_summary["lock_rate"]
    passed = clean_improved and lock_preserved
    return {
        "lab": "11.34",
        "decision": "accept_gardner_for_long_ber" if passed else "keep_baseline_pending_more_evidence",
        "equal_budget": equal_budget,
        "conditions": {
            key: baseline.get(key)
            for key in ("carrier_hz", "tx_gain_db", "rx_gain_db", "start_offsets", "retries_per_offset")
        },
        "cfo_hz": base_cfos,
        "baseline_fixed_sampler": base_summary,
        "continuous_gardner": gardner_summary,
        "clean_rate_improved": clean_improved,
        "lock_rate_preserved": lock_preserved,
        "passed": passed,
        "sources": {
            "baseline_commit": baseline.get("repository_commit"),
            "baseline_bitstream": baseline.get("expected_course_bitstream"),
            "gardner_commit": gardner.get("repository_commit"),
            "gardner_bitstream": gardner.get("expected_course_bitstream"),
        },
        "points": [
            {
                "cfo_hz": b["cfo_hz"],
                "baseline": b["coarse_on"],
                "gardner": g["coarse_on"],
            }
            for b, g in zip(baseline["points"], gardner["points"])
        ],
        "conclusion": (
            "Gardner improves the clean-attempt rate without reducing full-frame lock; "
            "proceed to the long BER/cycle-slip campaign."
            if passed
            else "The equal-budget live A/B does not yet justify replacing the fixed sampler."
        ),
    }


def plot(summary: dict, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["fixed sampler", "Gardner"]
    rows = [summary["baseline_fixed_sampler"], summary["continuous_gardner"]]
    lock = [100.0 * row["lock_rate"] for row in rows]
    clean = [100.0 * row["clean_attempt_rate"] for row in rows]
    x = range(2)
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.bar([i - 0.18 for i in x], lock, 0.36, color="#8da9c4", label="full frame")
    ax.bar([i + 0.18 for i in x], clean, 0.36, color="#1f6feb", label="BER = 0")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("attempts (%)")
    ax.set_title("Lab 11.34 — equal-budget live timing A/B")
    ax.grid(axis="y", color="#e3e7ec")
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, facecolor="white")
    plt.close(fig)


def self_test() -> int:
    def campaign(timing: bool, clean: int, full: int) -> dict:
        return {
            "timing_recovery": timing,
            "carrier_hz": 915e6,
            "tx_gain_db": -30,
            "rx_gain_db": 50,
            "start_offsets": [0, 1],
            "retries_per_offset": 10,
            "points": [
                {
                    "cfo_hz": 30_000,
                    "coarse_on": {
                        "attempts": 20,
                        "clean_frames": clean,
                        "full_frames": full,
                    },
                }
            ],
        }

    result = compare(campaign(False, 8, 18), campaign(True, 14, 19))
    assert result["passed"]
    assert result["continuous_gardner"]["clean_attempt_rate"] == 0.7
    print("SELF-TEST PASS")
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--gardner", type=Path)
    ap.add_argument("--json-out", type=Path, default=ASSETS / "lab1134_continuous_qpsk_timing_recovery.json")
    ap.add_argument("--png-out", type=Path, default=ASSETS / "lab1134_continuous_qpsk_timing_recovery.png")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        return self_test()
    if args.baseline is None or args.gardner is None:
        raise SystemExit("--baseline and --gardner are required")
    baseline = load_campaign(args.baseline, expect_timing=False)
    gardner = load_campaign(args.gardner, expect_timing=True)
    summary = compare(baseline, gardner)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
    if not args.no_plot:
        plot(summary, args.png_out)
    print(summary["conclusion"])
    print(f"wrote {args.json_out}")
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
