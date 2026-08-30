#!/usr/bin/env python3
"""Export observable diagnostic plots for the Lab 11.38 offline QPSK receiver.

This module is intentionally a thin visualization layer over
``lab_11_38_offline_qpsk_rx``.  It reuses the same format adapters, rational
resampler, committed RRC, CFO estimator and frame acquisition functions rather
than implementing a second receiver.

The plots are diagnostic evidence only.  A plot generated from ``--self-test``
is synthetic/reference evidence, not a hardware-RX claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lab_11_38_offline_qpsk_rx as rx  # noqa: E402


def _prepare(samples: np.ndarray, sample_rate_hz: float) -> dict:
    """Run the same public RX stages while retaining arrays needed for plots."""
    _, reference_symbols, taps = rx.load_course_reference()
    normalized, _, _ = rx.remove_dc_and_normalize(samples)
    up, down = rx.rational_ratio(sample_rate_hz, rx.MODEL_SAMPLE_RATE_HZ)
    model_samples = rx.rational_resample(normalized, up, down)
    model_samples, _, _ = rx.remove_dc_and_normalize(model_samples)
    matched = np.convolve(model_samples, taps, mode="full")
    acquisition = rx.acquire_frame(matched, reference_symbols)

    phase = int(acquisition["sample_phase"])
    start = int(acquisition["frame_symbol_index"])
    raw_symbol_stream = matched[phase::rx.SPS]
    raw_frame = raw_symbol_stream[start : start + rx.FRAME_SYMBOLS]

    return {
        "model_samples": model_samples,
        "matched": matched,
        "raw_frame": raw_frame,
        "equalized_frame": np.asarray(acquisition["equalized_symbols"]),
        "sync_metric": np.asarray(acquisition["sync_metric_trace"]),
        "sample_phase": phase,
        "frame_symbol_index": start,
        "cfo_hz": float(acquisition["cfo_hz"]),
        "sync_metric_peak": float(acquisition["sync_metric"]),
        "resample_up": up,
        "resample_down": down,
    }


def _save_spectrum(samples: np.ndarray, output: Path) -> None:
    count = min(len(samples), 65536)
    if count < 64:
        raise ValueError("capture is too short for a useful spectrum")
    segment = samples[:count]
    window = np.hanning(count)
    spectrum = np.fft.fftshift(np.fft.fft(segment * window))
    power = 20.0 * np.log10(np.maximum(np.abs(spectrum), 1e-12))
    power -= np.max(power)
    frequency_khz = np.fft.fftshift(np.fft.fftfreq(count, d=1.0 / rx.MODEL_SAMPLE_RATE_HZ)) / 1e3

    fig, ax = plt.subplots()
    ax.plot(frequency_khz, power)
    ax.set_xlabel("Frequency offset, kHz")
    ax.set_ylabel("Relative magnitude, dB")
    ax.set_title("Lab 11.38: spectrum after input normalization/resampling")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _save_sync_metric(metric: np.ndarray, frame_index: int, output: Path) -> None:
    fig, ax = plt.subplots()
    ax.plot(np.arange(metric.size), metric)
    ax.axvline(frame_index, linestyle="--")
    ax.set_xlabel("Candidate frame-start symbol")
    ax.set_ylabel("Normalized preamble correlation")
    ax.set_title("Lab 11.38: automatic frame synchronization")
    ax.set_ylim(bottom=0.0)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _save_constellation(symbols: np.ndarray, title: str, output: Path) -> None:
    fig, ax = plt.subplots()
    ax.scatter(symbols.real, symbols.imag, s=18, alpha=0.75)
    ax.axhline(0.0, linewidth=0.8)
    ax.axvline(0.0, linewidth=0.8)
    ax.set_xlabel("I")
    ax.set_ylabel("Q")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _save_matched_filter_timing(
    matched: np.ndarray,
    sample_phase: int,
    frame_symbol_index: int,
    output: Path,
) -> None:
    frame_start_sample = sample_phase + frame_symbol_index * rx.SPS
    left = max(0, frame_start_sample - 4 * rx.SPS)
    right = min(len(matched), frame_start_sample + 24 * rx.SPS)
    index = np.arange(left, right)
    selected = np.arange(frame_start_sample, right, rx.SPS)

    fig, ax = plt.subplots()
    ax.plot(index, np.abs(matched[left:right]))
    valid = selected[selected < len(matched)]
    ax.scatter(valid, np.abs(matched[valid]), s=24)
    ax.axvline(frame_start_sample, linestyle="--")
    ax.set_xlabel("Model-rate sample index")
    ax.set_ylabel("|matched filter output|")
    ax.set_title(f"Lab 11.38: selected timing phase = {sample_phase} / {rx.SPS}")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def render_diagnostics(samples: np.ndarray, sample_rate_hz: float, output_dir: Path) -> dict:
    """Create one file per diagnostic view and return machine-readable provenance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    data = _prepare(samples, sample_rate_hz)

    paths = {
        "spectrum": output_dir / "spectrum.png",
        "sync_metric": output_dir / "sync-metric.png",
        "constellation_before": output_dir / "constellation-before-carrier-correction.png",
        "constellation_after": output_dir / "constellation-after-carrier-correction.png",
        "matched_filter_timing": output_dir / "matched-filter-timing.png",
    }

    _save_spectrum(data["model_samples"], paths["spectrum"])
    _save_sync_metric(data["sync_metric"], data["frame_symbol_index"], paths["sync_metric"])
    _save_constellation(
        data["raw_frame"],
        "Lab 11.38: acquired symbols before carrier correction",
        paths["constellation_before"],
    )
    _save_constellation(
        data["equalized_frame"],
        "Lab 11.38: recovered QPSK constellation",
        paths["constellation_after"],
    )
    _save_matched_filter_timing(
        data["matched"],
        data["sample_phase"],
        data["frame_symbol_index"],
        paths["matched_filter_timing"],
    )

    return {
        "evidence_scope": "offline-diagnostics-only",
        "hardware_rx_claimed": False,
        "model_sample_rate_hz": rx.MODEL_SAMPLE_RATE_HZ,
        "resample_up": int(data["resample_up"]),
        "resample_down": int(data["resample_down"]),
        "sample_phase": int(data["sample_phase"]),
        "frame_symbol_index": int(data["frame_symbol_index"]),
        "cfo_hz": float(data["cfo_hz"]),
        "sync_metric_peak": float(data["sync_metric_peak"]),
        "plots": {name: str(path) for name, path in paths.items()},
    }


def _load_capture(capture: Path, metadata_path: Path) -> tuple[np.ndarray, float, str | None]:
    metadata = rx.load_metadata(metadata_path)
    iq_format, sample_rate_hz, declared_count = rx.validate_metadata(metadata)
    samples = rx.read_iq(capture, iq_format)
    if declared_count is not None and declared_count != samples.size:
        raise ValueError(
            f"metadata sample_count={declared_count}, but capture contains {samples.size} complex samples"
        )
    return samples, sample_rate_hz, metadata.get("recording_id")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", nargs="?", type=Path, help="raw .ci16/.cu8/.cf32 capture")
    parser.add_argument("--metadata", type=Path, help="JSON sidecar; defaults to capture basename + .json")
    parser.add_argument("--plot-dir", type=Path, required=True, help="directory for diagnostic PNG files")
    parser.add_argument("--self-test", action="store_true", help="render diagnostics from the synthetic reference capture")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        samples = rx.synthetic_reference_capture()
        sample_rate_hz = rx.MODEL_SAMPLE_RATE_HZ
        recording_id = "synthetic-reference"
    else:
        if args.capture is None:
            raise SystemExit("capture path is required unless --self-test is used")
        metadata_path = args.metadata or rx.default_metadata_path(args.capture)
        samples, sample_rate_hz, recording_id = _load_capture(args.capture, metadata_path)

    report = render_diagnostics(samples, sample_rate_hz, args.plot_dir)
    report["recording_id"] = recording_id
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
