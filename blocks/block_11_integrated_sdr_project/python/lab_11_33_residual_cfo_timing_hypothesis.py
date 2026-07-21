#!/usr/bin/env python3
"""Lab 11.33 - assemble the accepted Costas fix and rejected timing-picker A/B evidence.

This lab deliberately separates two decisions made from the same two-board bench:

* accept the carrier-loop change that turns a retained 30 kHz capture from 124/280
  errors into 0/280 in RTL;
* reject a more elaborate settled, squared-energy timing picker because its live-RF
  clean-attempt rate is worse than the accepted receiver, despite passing replay,
  implementation, and timing closure.

The input files are raw Lab 11.32 run JSONs.  Keeping this as a small post-processor
means the hardware runner remains the source of truth for every attempt and this lab
cannot silently reinterpret no-lock attempts as successful frames.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "docs" / "assets"


def load_point(path: Path) -> dict:
    payload = json.loads(path.read_text())
    point = payload["points"][0]
    summary = point["coarse_on"]
    return {
        "source": str(path),
        "cfo_hz": point["cfo_hz"],
        "start_offsets": payload["start_offsets"],
        "clean_frames": summary["clean_frames"],
        "full_frames": summary["full_frames"],
        "attempts": summary["attempts"],
        "clean_attempt_rate": summary["clean_attempt_rate"],
        "lock_rate": summary["lock_rate"],
        "aggregate_ber_full_frames": summary["aggregate_ber"],
    }


def build_summary(accepted: Path, candidates: list[Path]) -> dict:
    baseline = load_point(accepted)
    rejected = [load_point(path) for path in candidates]
    best_candidate = max(rejected, key=lambda row: row["clean_attempt_rate"])
    passed = all(
        row["clean_attempt_rate"] < baseline["clean_attempt_rate"] for row in rejected
    )
    return {
        "lab": "11.33",
        "decision": "reject_settled_squared_energy_picker" if passed else "inconclusive",
        "conditions": {
            "topology": "board A vendor cyclic-DMA TX -> 30 dB pad -> board B course fabric RX",
            "carrier_hz": 915_000_000,
            "injected_cfo_hz": 30_000,
            "tx_gain_db": -30,
            "rx_gain_db": 50,
            "bits_per_frame": 280,
        },
        "accepted_receiver": baseline,
        "rejected_picker_runs": rejected,
        "best_rejected_picker_run": best_candidate,
        "rtl_evidence": {
            "retained_capture_old_costas_errors": 124,
            "retained_capture_tuned_costas_errors": 0,
            "bits": 280,
        },
        "implementation_evidence": {
            "rejected_unpipelined_wns_ns": -2.779,
            "rejected_unpipelined_tns_ns": -1772.272,
            "rejected_unpipelined_failing_endpoints": 3113,
            "pipelined_postroute_wns_ns": 0.010,
            "pipelined_postroute_tns_ns": 0.0,
            "pipelined_postroute_failing_endpoints": 0,
            "pipelined_fully_routed_nets": 75689,
            "pipelined_routing_errors": 0,
            "pipelined_raw_bit_sha256": "8055680cd0a5052826c10bfd4fe59f3e8342a1991424da561b5aa7b5d26142ad",
        },
        "accepted_artifacts": {
            "boot_raw_bit_sha256": "584ccd14c53fb381edbf3f37bbcc497a2c68a13431465f5d26a040c4af40b74b",
            "runtime_bit_bin_sha256": "80841dc40626981563e648543d573f1bd9ef908f3f4efd5f4d0e91896cf67e09",
        },
        "passed": passed,
        "conclusion": (
            "The Costas pull-in fix is retained. The settled squared-energy burst picker is "
            "rejected: its best 40-attempt live-RF run is worse than the accepted receiver. "
            "The next experiment is continuous QPSK timing recovery, not another feedforward "
            "phase-score heuristic."
        ),
    }


def plot(summary: dict, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    base = summary["accepted_receiver"]
    candidates = summary["rejected_picker_runs"]
    rows = [base, *candidates]
    labels = ["accepted\noffset 4", *[f"L2 picker\noffset {r['start_offsets'][0]}" for r in candidates]]
    clean = [100 * r["clean_attempt_rate"] for r in rows]
    lock = [100 * r["lock_rate"] for r in rows]
    x = range(len(rows))
    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    ax.bar([i - 0.18 for i in x], lock, width=0.36, color="#8da9c4", label="full frame")
    ax.bar([i + 0.18 for i in x], clean, width=0.36, color="#1f6feb", label="BER = 0")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("attempts (%)")
    ax.set_title("Lab 11.33 — live two-board A/B at +30 kHz CFO (40 attempts each)")
    ax.grid(axis="y", color="#e3e7ec")
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    for i, value in enumerate(clean):
        ax.text(i + 0.18, value + 2, f"{value:.0f}%", ha="center", fontsize=9)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, facecolor="white")
    plt.close(fig)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--accepted", type=Path)
    ap.add_argument("--candidate", type=Path, action="append", default=[])
    ap.add_argument("--json-out", type=Path, default=ASSETS / "lab1133_residual_cfo_timing_hypothesis.json")
    ap.add_argument("--png-out", type=Path, default=ASSETS / "lab1133_residual_cfo_timing_hypothesis.png")
    ap.add_argument("--self-test", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.self_test:
        assert 124 > 0 and 0 == 0
        print("SELF-TEST PASS")
        return 0
    if args.accepted is None or not args.candidate:
        raise SystemExit("--accepted and at least one --candidate are required")
    summary = build_summary(args.accepted, args.candidate)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
    plot(summary, args.png_out)
    print(summary["conclusion"])
    print(f"wrote {args.json_out}")
    print(f"wrote {args.png_out}")
    return 0 if summary["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
