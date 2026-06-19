#!/usr/bin/env python3
"""Lab 9.4 — Read WAV IQ and analyze spectrum.

Reads a stereo WAV IQ recording referenced by a manifest, converts it to
normalized complex samples, computes FFT-based metrics, and writes report-ready
plots and metrics JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_MANIFEST = ROOT / "datasets" / "lab1_0_rtl_sdr_observation" / "manifest_narrowband_220860000.yaml"


@dataclass(frozen=True)
class WavIqMetrics:
    dataset_id: str
    sample_count_read: int
    sample_rate_hz: float
    center_frequency_hz: float
    duration_s: float
    measured_peak_hz: float
    expected_offset_hz: float
    frequency_error_hz: float
    peak_dbfs: float
    noise_floor_dbfs: float
    snr_db: float
    dc_offset_magnitude: float
    clipping_fraction: float
    channels: int
    sample_width_bytes: int
    quality_pass: bool
    iq_path: str
    manifest_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read WAV IQ from a manifest and generate offline analysis artifacts.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to WAV IQ manifest YAML or JSON.",
    )
    parser.add_argument(
        "--iq-path",
        type=Path,
        default=None,
        help="Optional explicit path to the WAV IQ file. Overrides manifest location hints.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ASSET_DIR,
        help="Directory for generated plots and metrics JSON.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported manifest format: {path}")


def resolve_iq_path(manifest: dict[str, Any], manifest_path: Path, explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path.expanduser().resolve()

    local_hint = manifest.get("local_path_hint_windows") or manifest.get("local_path")
    if local_hint:
        expanded = os.path.expandvars(str(local_hint))
        path = Path(expanded).expanduser()
        if path.exists():
            return path.resolve()

    file_name = manifest.get("file_name")
    if file_name:
        candidate = manifest_path.parent / str(file_name)
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        "Unable to locate the WAV IQ file. Pass --iq-path or add a valid local_path_hint_windows to the manifest."
    )


def read_wav_iq(path: Path, manifest: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        sample_width = w.getsampwidth()
        sample_rate_hz = float(w.getframerate())
        frame_count = w.getnframes()
        raw_frames = w.readframes(frame_count)

    if channels != 2:
        raise ValueError(f"WAV IQ reader expects stereo data, got {channels} channels in {path}")

    if sample_width == 1:
        raw = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float64)
        raw = (raw - 127.5) / 127.5
    elif sample_width == 2:
        raw = np.frombuffer(raw_frames, dtype="<i2").astype(np.float64) / 32768.0
    elif sample_width == 4:
        raw = np.frombuffer(raw_frames, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV IQ sample width: {sample_width} bytes")

    if len(raw) % channels != 0:
        raise ValueError(f"Unexpected interleaved sample count in {path}: {len(raw)}")

    matrix = raw.reshape(-1, channels)
    i_first = bool(manifest.get("i_first", True))
    i_data = matrix[:, 0]
    q_data = matrix[:, 1]
    x = i_data + 1j * q_data if i_first else q_data + 1j * i_data

    info = {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate_hz,
        "frame_count": frame_count,
        "duration_s": frame_count / sample_rate_hz,
    }
    return x, info


def get_expected_offset_hz(manifest: dict[str, Any]) -> float:
    if "expected_signal_offset_hz" in manifest:
        return float(manifest["expected_signal_offset_hz"])
    return float(manifest.get("signal", {}).get("expected_signal_offset_hz", 0.0))


def get_fft_length(manifest: dict[str, Any]) -> int:
    return int(manifest.get("processing", {}).get("fft_length", 65536))


def get_quality_expectations(manifest: dict[str, Any]) -> dict[str, float]:
    raw = manifest.get("quality_expectations", {})
    return {
        "max_clipping_fraction": float(raw.get("max_clipping_fraction", 1.0)),
        "max_dc_offset": float(raw.get("max_dc_offset", 1.0)),
        "max_frequency_error_hz": float(raw.get("max_frequency_error_hz", 1e99)),
        "min_snr_db": float(raw.get("min_snr_db", -1e99)),
    }


def spectrum_db(x: np.ndarray, sample_rate_hz: float, fft_length: int) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate_hz))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def compute_metrics(
    x: np.ndarray,
    manifest: dict[str, Any],
    wav_info: dict[str, Any],
    *,
    iq_path: Path,
    manifest_path: Path,
) -> WavIqMetrics:
    sample_rate_hz = float(manifest.get("sample_rate_hz", wav_info["sample_rate_hz"]))
    center_frequency_hz = float(manifest.get("center_frequency_hz", 0.0))
    expected_offset_hz = get_expected_offset_hz(manifest)
    fft_length = get_fft_length(manifest)
    freq, mag_db = spectrum_db(x, sample_rate_hz, fft_length)

    peak_idx = int(np.argmax(mag_db))
    measured_peak_hz = float(freq[peak_idx])
    peak_dbfs = float(mag_db[peak_idx])
    frequency_error_hz = measured_peak_hz - expected_offset_hz

    bin_width = sample_rate_hz / fft_length
    signal_mask = np.abs(freq - measured_peak_hz) < max(15e3, 20 * bin_width)
    dc_mask = np.abs(freq) < 5e3
    noise_mask = ~(signal_mask | dc_mask)
    noise_floor_dbfs = float(np.median(mag_db[noise_mask]))
    snr_db = peak_dbfs - noise_floor_dbfs

    dc_offset_magnitude = float(np.abs(np.mean(x)))
    clipping_fraction = float(np.mean((np.abs(np.real(x)) > 0.999) | (np.abs(np.imag(x)) > 0.999)))

    q = get_quality_expectations(manifest)
    quality_pass = bool(
        clipping_fraction <= q["max_clipping_fraction"]
        and dc_offset_magnitude <= q["max_dc_offset"]
        and abs(frequency_error_hz) <= q["max_frequency_error_hz"]
        and snr_db >= q["min_snr_db"]
    )

    return WavIqMetrics(
        dataset_id=str(manifest.get("dataset_id", "wav_iq_capture")),
        sample_count_read=int(len(x)),
        sample_rate_hz=sample_rate_hz,
        center_frequency_hz=center_frequency_hz,
        duration_s=float(wav_info["duration_s"]),
        measured_peak_hz=measured_peak_hz,
        expected_offset_hz=expected_offset_hz,
        frequency_error_hz=frequency_error_hz,
        peak_dbfs=peak_dbfs,
        noise_floor_dbfs=noise_floor_dbfs,
        snr_db=float(snr_db),
        dc_offset_magnitude=dc_offset_magnitude,
        clipping_fraction=clipping_fraction,
        channels=int(wav_info["channels"]),
        sample_width_bytes=int(wav_info["sample_width_bytes"]),
        quality_pass=quality_pass,
        iq_path=str(iq_path),
        manifest_path=str(manifest_path),
    )


def sanitize_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value)


def output_prefix(manifest: dict[str, Any]) -> str:
    return f"lab94_{sanitize_token(str(manifest.get('dataset_id', 'wav_iq_capture')))}"


def save_spectrum_plot(x: np.ndarray, manifest: dict[str, Any], metrics: WavIqMetrics, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    freq, mag_db = spectrum_db(x, metrics.sample_rate_hz, get_fft_length(manifest))
    path = out_dir / f"{output_prefix(manifest)}_spectrum.png"

    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db, label="WAV IQ FFT")
    plt.axvline(metrics.expected_offset_hz / 1e3, linestyle="--", label="expected offset")
    plt.axvline(metrics.measured_peak_hz / 1e3, linestyle=":", label="measured peak")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(f"Lab 9.4 — {metrics.dataset_id} spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def save_time_plot(x: np.ndarray, manifest: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = min(800, len(x))
    path = out_dir / f"{output_prefix(manifest)}_time_preview.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(np.real(x[:n]), label="I")
    plt.plot(np.imag(x[:n]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Normalized amplitude")
    plt.title(f"Lab 9.4 — {manifest.get('dataset_id', 'wav_iq_capture')} time preview")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def save_metrics_json(metrics: WavIqMetrics, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sanitize_token(metrics.dataset_id)}_metrics.json"
    path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    iq_path = resolve_iq_path(manifest, manifest_path, args.iq_path)
    x, wav_info = read_wav_iq(iq_path, manifest)
    metrics = compute_metrics(x, manifest, wav_info, iq_path=iq_path, manifest_path=manifest_path)
    spectrum_path = save_spectrum_plot(x, manifest, metrics, args.out_dir)
    time_path = save_time_plot(x, manifest, args.out_dir)
    metrics_path = save_metrics_json(metrics, args.out_dir)

    print("Lab 9.4 — Read WAV IQ and analyze spectrum")
    print(f"Manifest: {manifest_path}")
    print(f"IQ file: {iq_path}")
    print(f"Dataset ID: {metrics.dataset_id}")
    print(f"Samples read: {metrics.sample_count_read}")
    print(f"Sample rate: {metrics.sample_rate_hz:.0f} Hz")
    print(f"Center frequency: {metrics.center_frequency_hz:.0f} Hz")
    print(f"Expected offset: {metrics.expected_offset_hz:.3f} Hz")
    print(f"Measured peak: {metrics.measured_peak_hz:.3f} Hz")
    print(f"Frequency error: {metrics.frequency_error_hz:.3f} Hz")
    print(f"SNR estimate: {metrics.snr_db:.2f} dB")
    print(f"DC offset magnitude: {metrics.dc_offset_magnitude:.6f}")
    print(f"Clipping fraction: {metrics.clipping_fraction:.6e}")
    print(f"Quality pass: {metrics.quality_pass}")
    print(f"Spectrum plot: {spectrum_path}")
    print(f"Time plot: {time_path}")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
