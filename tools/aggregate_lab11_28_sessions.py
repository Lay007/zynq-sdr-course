#!/usr/bin/env python3
"""Aggregate Lab 11.28 multi-burst metrics across independent RF sessions."""

from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np


def expand_paths(patterns: list[str]) -> list[Path]:
    paths = {Path(match).resolve() for pattern in patterns for match in glob.glob(pattern)}
    if not paths:
        raise FileNotFoundError("No Lab 11.28 metrics files matched the supplied patterns")
    return sorted(paths)


def wilson_interval(count: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    proportion = count / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total))
        / denominator
    )
    lower = max(center - half_width, 0.0)
    upper = min(center + half_width, 1.0)
    if lower < 1e-15:
        lower = 0.0
    if upper > 1.0 - 1e-15:
        upper = 1.0
    return [float(lower), float(upper)]


def distribution(values: list[float]) -> dict[str, float]:
    data = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(data)),
        "median": float(np.median(data)),
        "mean": float(np.mean(data)),
        "p95": float(np.quantile(data, 0.95)),
        "max": float(np.max(data)),
        "std": float(np.std(data)),
    }


def aggregate_sessions(paths: list[Path]) -> dict[str, Any]:
    sessions: list[dict[str, Any]] = []
    frames: list[dict[str, Any]] = []
    bitstream_md5s: set[str] = set()
    common_configs: set[tuple[Any, ...]] = set()

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("analysis_mode") != "multi_burst":
            raise ValueError(f"{path}: expected multi_burst Lab 11.28 metrics")
        session = payload.get("session") or {}
        md5 = str(session.get("bitstream_md5") or "")
        if not md5:
            raise ValueError(f"{path}: missing session bitstream MD5")
        bitstream_md5s.add(md5)
        common_configs.add(
            (
                session.get("center_frequency_hz"),
                session.get("transmitter_sample_rate_hz"),
                session.get("rtl_sample_rate_hz"),
                session.get("tx_attenuation_db"),
                session.get("rtl_tuner_gain_db10"),
                payload.get("symbol_rate_hz"),
                payload.get("symbol_count"),
            )
        )
        burst = payload.get("burst_analysis") or {}
        summary = burst.get("summary") or {}
        detected_frames = [row for row in burst.get("frames", []) if row.get("detected")]
        frames.extend(detected_frames)
        commanded = int(summary.get("commanded_burst_count") or 0)
        detected = int(summary.get("detected_burst_count") or 0)
        zero = int(summary.get("zero_error_burst_count") or 0)
        safe_reboot = bool(session.get("reboot_to_stock_ok"))
        success = commanded > 0 and detected == commanded and zero == detected and safe_reboot
        sessions.append(
            {
                "file": path.name,
                "dataset_id": payload.get("dataset_id"),
                "run_tag": session.get("run_tag"),
                "capture_sha256": payload.get("capture_sha256"),
                "commanded_bursts": commanded,
                "detected_bursts": detected,
                "zero_error_bursts": zero,
                "compared_bits": int(summary.get("compared_bits_total") or 0),
                "bit_errors": int(summary.get("bit_errors_total") or 0),
                "aggregate_ber": summary.get("aggregate_ber"),
                "median_evm_percent": summary.get("evm_percent", {}).get("median"),
                "median_snr_from_evm_db": summary.get("snr_from_evm_db", {}).get("median"),
                "median_frequency_shift_hz": summary.get("frequency_shift_hz", {}).get("median"),
                "clipping_fraction": payload.get("raw_clipping_fraction"),
                "reboot_to_stock_ok": safe_reboot,
                "session_success": success,
            }
        )

    if len(bitstream_md5s) != 1:
        raise ValueError(f"Mixed bitstream MD5 values: {sorted(bitstream_md5s)}")
    if len(common_configs) != 1:
        raise ValueError("Session RF/modem configurations do not match")
    if not frames:
        raise ValueError("No detected frames found across the supplied sessions")

    session_count = len(sessions)
    successful_sessions = sum(int(row["session_success"]) for row in sessions)
    commanded_total = sum(row["commanded_bursts"] for row in sessions)
    detected_total = sum(row["detected_bursts"] for row in sessions)
    zero_total = sum(row["zero_error_bursts"] for row in sessions)
    compared_bits = sum(row["compared_bits"] for row in sessions)
    bit_errors = sum(row["bit_errors"] for row in sessions)
    frame_errors = detected_total - zero_total
    config = next(iter(common_configs))

    return {
        "mode": "qpsk_ota_cross_session_qualification",
        "bitstream_md5": next(iter(bitstream_md5s)),
        "config": {
            "center_frequency_hz": config[0],
            "transmitter_sample_rate_hz": config[1],
            "rtl_sample_rate_hz": config[2],
            "tx_attenuation_db": config[3],
            "rtl_tuner_gain_db10": config[4],
            "symbol_rate_hz": config[5],
            "symbol_count": config[6],
        },
        "session_count": session_count,
        "successful_sessions": successful_sessions,
        "session_success_rate": successful_sessions / session_count,
        "session_success_rate_wilson_95": wilson_interval(successful_sessions, session_count),
        "safe_reboot_sessions": sum(int(row["reboot_to_stock_ok"]) for row in sessions),
        "commanded_bursts": commanded_total,
        "detected_bursts": detected_total,
        "detection_rate": detected_total / commanded_total if commanded_total else None,
        "zero_error_bursts": zero_total,
        "zero_error_burst_rate": zero_total / detected_total,
        "zero_error_burst_rate_wilson_95": wilson_interval(zero_total, detected_total),
        "frame_errors": frame_errors,
        "frame_error_rate": frame_errors / detected_total,
        "compared_bits": compared_bits,
        "bit_errors": bit_errors,
        "aggregate_ber": bit_errors / compared_bits,
        "aggregate_ber_wilson_95": wilson_interval(bit_errors, compared_bits),
        "zero_error_ber_upper_95_rule_of_three": (
            3.0 / compared_bits if bit_errors == 0 else None
        ),
        "evm_percent": distribution([float(row["evm_percent"]) for row in frames]),
        "snr_from_evm_db": distribution(
            [float(row["snr_from_evm_db"]) for row in frames]
        ),
        "frequency_shift_hz": distribution(
            [float(row["total_frequency_shift_hz"]) for row in frames]
        ),
        "normalized_correlation": distribution(
            [float(row["normalized_correlation"]) for row in frames]
        ),
        "session_median_evm_percent": distribution(
            [float(row["median_evm_percent"]) for row in sessions]
        ),
        "session_median_frequency_shift_hz": distribution(
            [float(row["median_frequency_shift_hz"]) for row in sessions]
        ),
        "sessions": sessions,
    }


def save_plot(path: Path, summary: dict[str, Any]) -> None:
    sessions = summary["sessions"]
    indices = np.arange(len(sessions))
    labels = [str(row["run_tag"]).rsplit("_", 1)[-1] for row in sessions]
    fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
    axes[0].bar(indices, [row["bit_errors"] for row in sessions])
    axes[0].set_ylabel("Bit errors")
    axes[0].set_ylim(0.0, max(1.0, axes[0].get_ylim()[1]))
    if all(row["bit_errors"] == 0 for row in sessions):
        axes[0].text(0.5, 0.5, "All sessions: zero bit errors", ha="center", transform=axes[0].transAxes)
    axes[1].plot(indices, [row["median_evm_percent"] for row in sessions], "o-")
    axes[1].set_ylabel("Median EVM, %")
    axes[2].plot(indices, [row["median_frequency_shift_hz"] for row in sessions], "o-")
    axes[2].set_ylabel("Median CFO, Hz")
    axes[2].set_xlabel("Independent session")
    axes[2].set_xticks(indices, labels)
    for axis in axes:
        axis.grid(True)
    fig.suptitle("RTL-SDR OTA QPSK cross-session qualification")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+", help="Metrics JSON paths or glob patterns")
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--plot-out", type=Path, default=None)
    args = parser.parse_args()

    summary = aggregate_sessions(expand_paths(args.patterns))
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.plot_out is not None:
        save_plot(args.plot_out, summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
