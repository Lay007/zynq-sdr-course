#!/usr/bin/env python3
"""Lab 6.6 - Compare a Zynq CI16 capture against an RTL-SDR WAV observation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"
BLOCK9_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools" / "python"
if str(BLOCK9_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK9_DIR))

from lab_9_2_read_ci16_iq_and_analyze import (  # noqa: E402
    compute_metrics as compute_ci16_metrics,
    load_manifest as load_ci16_manifest,
    read_ci16,
    resolve_iq_path as resolve_ci16_path,
)
from lab_9_4_read_wav_iq_and_analyze import (  # noqa: E402
    compute_metrics as compute_wav_metrics,
    load_manifest as load_wav_manifest,
    read_wav_iq,
    resolve_iq_path as resolve_wav_path,
)


DEFAULT_ZYNQ_MANIFEST = ROOT / "datasets" / "lab6_6_zynq_rx_observation" / "manifest_fm_103119454.yaml"
DEFAULT_RTL_MANIFEST = ROOT / "datasets" / "lab1_0_rtl_sdr_observation" / "manifest_fm_103119454.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Overlay Zynq AD9361 and RTL-SDR FM observation spectra.")
    parser.add_argument("--zynq-manifest", type=Path, default=DEFAULT_ZYNQ_MANIFEST)
    parser.add_argument("--rtl-manifest", type=Path, default=DEFAULT_RTL_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=ASSET_DIR)
    parser.add_argument("--window-khz", type=float, default=600.0, help="Displayed half-span around DC in kHz.")
    return parser.parse_args()


def sanitize_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value)


def normalize_trace(mag_db: np.ndarray) -> np.ndarray:
    return mag_db - float(np.median(mag_db))


def averaged_spectrum_db(
    x: np.ndarray,
    sample_rate_hz: float,
    *,
    fft_length: int = 8192,
    segment_count: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    usable_segments = max(1, min(segment_count, len(x) // fft_length))
    usable_samples = usable_segments * fft_length
    trimmed = x[:usable_samples].reshape(usable_segments, fft_length)
    window = np.hanning(fft_length)
    coherent_gain = np.sum(window) / fft_length

    power_accum = np.zeros(fft_length, dtype=np.float64)
    for segment in trimmed:
        centered = segment - np.mean(segment)
        spec = np.fft.fftshift(np.fft.fft(centered * window, n=fft_length)) / (fft_length * coherent_gain)
        power_accum += np.abs(spec) ** 2

    power_mean = power_accum / usable_segments
    freq = np.fft.fftshift(np.fft.fftfreq(fft_length, d=1.0 / sample_rate_hz))
    mag_db = 10.0 * np.log10(np.maximum(power_mean, 1e-20))
    return freq, mag_db


def save_overlay_plot(
    zynq_freq: np.ndarray,
    zynq_mag_db: np.ndarray,
    rtl_freq: np.ndarray,
    rtl_mag_db: np.ndarray,
    *,
    window_khz: float,
    out_path: Path,
) -> None:
    zynq_norm = normalize_trace(zynq_mag_db)
    rtl_norm = normalize_trace(rtl_mag_db)

    plt.figure(figsize=(8.0, 4.8))
    plt.plot(zynq_freq / 1e3, zynq_norm, label="Zynq AD9361 RX (relative)")
    plt.plot(rtl_freq / 1e3, rtl_norm, label="RTL-SDR WAV IQ (relative)", alpha=0.85)
    plt.xlim(-window_khz, window_khz)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude above median, dB")
    plt.title("Lab 6.6 - Zynq vs RTL-SDR FM observation")
    plt.legend(loc="best")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=180)
    plt.close()


def main() -> None:
    args = parse_args()
    zynq_manifest_path = args.zynq_manifest.resolve()
    rtl_manifest_path = args.rtl_manifest.resolve()

    zynq_manifest = load_ci16_manifest(zynq_manifest_path)
    rtl_manifest = load_wav_manifest(rtl_manifest_path)

    zynq_iq_path = resolve_ci16_path(zynq_manifest, zynq_manifest_path, None)
    rtl_iq_path = resolve_wav_path(rtl_manifest, rtl_manifest_path, None)

    zynq_x = read_ci16(zynq_iq_path, zynq_manifest)
    rtl_x, rtl_info = read_wav_iq(rtl_iq_path, rtl_manifest)

    zynq_metrics = compute_ci16_metrics(zynq_x, zynq_manifest, iq_path=zynq_iq_path, manifest_path=zynq_manifest_path)
    rtl_metrics = compute_wav_metrics(rtl_x, rtl_manifest, rtl_info, iq_path=rtl_iq_path, manifest_path=rtl_manifest_path)

    zynq_freq, zynq_mag_db = averaged_spectrum_db(zynq_x, zynq_metrics.sample_rate_hz)
    rtl_freq, rtl_mag_db = averaged_spectrum_db(rtl_x, rtl_metrics.sample_rate_hz)

    dataset_token = sanitize_token(f"{zynq_metrics.dataset_id}_vs_{rtl_metrics.dataset_id}")
    plot_path = args.out_dir / f"lab66_{dataset_token}_spectrum.png"
    save_overlay_plot(
        zynq_freq,
        zynq_mag_db,
        rtl_freq,
        rtl_mag_db,
        window_khz=args.window_khz,
        out_path=plot_path,
    )

    summary = {
        "zynq": asdict(zynq_metrics),
        "rtl_sdr": asdict(rtl_metrics),
        "comparison": {
            "window_khz": float(args.window_khz),
            "sample_rate_match": zynq_metrics.sample_rate_hz == rtl_metrics.sample_rate_hz,
            "center_frequency_delta_hz": zynq_metrics.center_frequency_hz - rtl_metrics.center_frequency_hz,
            "overlay_fft_length": 8192,
            "overlay_segment_count": 32,
            "note": (
                "Spectra are averaged across short segments and median-normalized before overlay. Compare spectral shape and occupancy, "
                "not absolute calibrated amplitude."
            ),
        },
    }
    metrics_path = args.out_dir / f"lab66_{dataset_token}_metrics.json"
    metrics_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Lab 6.6 - Receiver comparison")
    print(f"Zynq manifest: {zynq_manifest_path}")
    print(f"RTL manifest: {rtl_manifest_path}")
    print(f"Overlay plot: {plot_path}")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
