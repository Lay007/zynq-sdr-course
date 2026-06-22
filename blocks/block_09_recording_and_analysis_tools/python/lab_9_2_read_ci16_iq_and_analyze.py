#!/usr/bin/env python3
"""Lab 9.2 - Read CI16 IQ and analyze spectrum.

By default the script regenerates the synthetic Lab 9.2 CI16 fixture. It can
also analyze a real capture referenced by a YAML/JSON manifest, which makes it
usable for offline AD9361/RTL-SDR dataset checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
BLOCK_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools"
ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_MANIFEST = BLOCK_DIR / "assets" / "example_ci16_capture_metadata.json"
DEFAULT_IQ_PATH = BLOCK_DIR / "assets" / "lab92_synthetic_ci16_tone.ci16"


@dataclass(frozen=True)
class Ci16IqMetrics:
    dataset_id: str
    sample_count_read: int
    sample_rate_hz: float
    center_frequency_hz: float
    duration_s: float
    expected_offset_hz: float
    measured_peak_hz: float
    frequency_error_hz: float
    peak_dbfs: float
    noise_floor_dbfs: float
    snr_db: float
    dc_offset_magnitude: float
    clipping_fraction: float
    quality_pass: bool
    iq_path: str
    manifest_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read CI16 IQ and generate offline analysis artifacts.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to CI16 manifest/metadata JSON or YAML.",
    )
    parser.add_argument(
        "--iq-path",
        type=Path,
        default=None,
        help="Optional explicit path to the CI16 IQ file. Overrides manifest location hints.",
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


def get_expected_offset_hz(manifest: dict[str, Any]) -> float:
    if "expected_signal_offset_hz" in manifest:
        return float(manifest["expected_signal_offset_hz"])
    return float(manifest.get("signal", {}).get("expected_signal_offset_hz", 0.0))


def get_fft_length(manifest: dict[str, Any]) -> int:
    return int(manifest.get("processing", {}).get("fft_length", 65536))


def get_peak_search_window_hz(manifest: dict[str, Any]) -> tuple[float, float] | None:
    analysis = manifest.get("analysis", {})
    if "peak_search_half_span_hz" not in analysis:
        return None
    return (
        float(analysis.get("peak_search_center_hz", get_expected_offset_hz(manifest))),
        float(analysis["peak_search_half_span_hz"]),
    )


def get_quality_expectations(manifest: dict[str, Any]) -> dict[str, float]:
    raw = manifest.get("quality_expectations", {})
    return {
        "max_clipping_fraction": float(raw.get("max_clipping_fraction", 1.0)),
        "max_dc_offset": float(raw.get("max_dc_offset", 1.0)),
        "max_frequency_error_hz": float(raw.get("max_frequency_error_hz", 1e99)),
        "min_snr_db": float(raw.get("min_snr_db", -1e99)),
    }


def write_synthetic_ci16(path: Path, manifest: dict[str, Any], seed: int = 92) -> None:
    fs = float(manifest["sample_rate_hz"])
    n = int(manifest["sample_count"])
    offset = get_expected_offset_hz(manifest)
    rng = np.random.default_rng(seed)

    t = np.arange(n) / fs
    tone = 0.55 * np.exp(1j * 2.0 * np.pi * offset * t)
    spur = 0.025 * np.exp(1j * 2.0 * np.pi * (offset + 420e3) * t)
    noise = 0.018 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    dc = 0.010 - 0.006j
    x = tone + spur + noise + dc

    scale = 32767.0
    i = np.clip(np.round(np.real(x) * scale), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * scale), -32768, 32767).astype("<i2")
    interleaved = np.empty(2 * n, dtype="<i2")
    if bool(manifest.get("i_first", True)):
        interleaved[0::2] = i
        interleaved[1::2] = q
    else:
        interleaved[0::2] = q
        interleaved[1::2] = i
    path.parent.mkdir(parents=True, exist_ok=True)
    interleaved.tofile(path)


def resolve_iq_path(
    manifest: dict[str, Any],
    manifest_path: Path,
    explicit_path: Path | None,
    *,
    default_generated_path: Path | None = None,
) -> Path:
    if explicit_path is not None:
        return explicit_path.expanduser().resolve()

    local_hint = manifest.get("local_path_hint_windows") or manifest.get("local_path")
    if local_hint:
        expanded = os.path.expandvars(str(local_hint))
        hinted = Path(expanded).expanduser()
        if hinted.exists():
            return hinted.resolve()

    manifest_path_hint = manifest.get("path")
    if manifest_path_hint:
        candidate = Path(str(manifest_path_hint))
        if not candidate.is_absolute():
            candidate = manifest_path.parent / candidate
        if candidate.exists():
            return candidate.resolve()

    file_name = manifest.get("file_name")
    if file_name:
        candidate = manifest_path.parent / str(file_name)
        if candidate.exists():
            return candidate.resolve()

    if default_generated_path is not None and default_generated_path.exists():
        return default_generated_path.resolve()

    raise FileNotFoundError(
        "Unable to locate the CI16 IQ file. Pass --iq-path or add a valid file_name/path/local_path_hint_windows."
    )


def read_ci16(path: Path, manifest: dict[str, Any]) -> np.ndarray:
    dtype = "<i2" if manifest.get("endianness", "little") == "little" else ">i2"
    raw = np.fromfile(path, dtype=dtype)
    if len(raw) % 2 != 0:
        raise ValueError(f"CI16 file has odd int16 count: {len(raw)}")

    a = raw[0::2].astype(np.float64) / 32768.0
    b = raw[1::2].astype(np.float64) / 32768.0
    if bool(manifest.get("i_first", True)):
        return a + 1j * b
    return b + 1j * a


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
    *,
    iq_path: Path,
    manifest_path: Path,
) -> Ci16IqMetrics:
    sample_rate_hz = float(manifest["sample_rate_hz"])
    center_frequency_hz = float(manifest.get("center_frequency_hz", 0.0))
    expected_offset_hz = get_expected_offset_hz(manifest)
    fft_length = get_fft_length(manifest)
    freq, mag_db = spectrum_db(x, sample_rate_hz, fft_length)

    peak_search_window = get_peak_search_window_hz(manifest)
    if peak_search_window is not None:
        center_hz, half_span_hz = peak_search_window
        peak_mask = np.abs(freq - center_hz) <= max(half_span_hz, 0.0)
        if np.any(peak_mask):
            candidate_indices = np.flatnonzero(peak_mask)
            peak_idx = int(candidate_indices[int(np.argmax(mag_db[peak_mask]))])
        else:
            peak_idx = int(np.argmax(mag_db))
    else:
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

    return Ci16IqMetrics(
        dataset_id=str(manifest.get("dataset_id", "ci16_capture")),
        sample_count_read=int(len(x)),
        sample_rate_hz=sample_rate_hz,
        center_frequency_hz=center_frequency_hz,
        duration_s=float(len(x) / sample_rate_hz),
        expected_offset_hz=expected_offset_hz,
        measured_peak_hz=measured_peak_hz,
        frequency_error_hz=frequency_error_hz,
        peak_dbfs=peak_dbfs,
        noise_floor_dbfs=noise_floor_dbfs,
        snr_db=float(snr_db),
        dc_offset_magnitude=dc_offset_magnitude,
        clipping_fraction=clipping_fraction,
        quality_pass=quality_pass,
        iq_path=str(iq_path),
        manifest_path=str(manifest_path),
    )


def sanitize_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value)


def output_prefix(manifest: dict[str, Any], manifest_path: Path) -> str:
    if manifest_path.resolve() == DEFAULT_MANIFEST.resolve():
        return "lab92_ci16_iq"
    return f"lab92_{sanitize_token(str(manifest.get('dataset_id', 'ci16_capture')))}"


def save_spectrum_plot(
    x: np.ndarray,
    manifest: dict[str, Any],
    metrics: Ci16IqMetrics,
    out_dir: Path,
    manifest_path: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    freq, mag_db = spectrum_db(x, metrics.sample_rate_hz, get_fft_length(manifest))
    path = out_dir / f"{output_prefix(manifest, manifest_path)}_spectrum.png"

    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db, label="CI16 IQ FFT")
    plt.axvline(metrics.expected_offset_hz / 1e3, linestyle="--", label="expected offset")
    plt.axvline(metrics.measured_peak_hz / 1e3, linestyle=":", label="measured peak")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(f"Lab 9.2 - {metrics.dataset_id} spectrum")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def save_time_plot(x: np.ndarray, manifest: dict[str, Any], out_dir: Path, manifest_path: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = min(800, len(x))
    path = out_dir / f"{output_prefix(manifest, manifest_path)}_time_preview.png"
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(np.real(x[:n]), label="I")
    plt.plot(np.imag(x[:n]), label="Q")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Normalized amplitude")
    plt.title(f"Lab 9.2 - {manifest.get('dataset_id', 'ci16_capture')} time preview")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def save_metrics_json(metrics: Ci16IqMetrics, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = "lab92_ci16_iq" if Path(metrics.manifest_path).resolve() == DEFAULT_MANIFEST.resolve() else sanitize_token(
        metrics.dataset_id
    )
    path = out_dir / f"{prefix}_metrics.json"
    path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)

    if manifest_path == DEFAULT_MANIFEST.resolve() and args.iq_path is None:
        write_synthetic_ci16(DEFAULT_IQ_PATH, manifest)
        iq_path = DEFAULT_IQ_PATH.resolve()
    else:
        iq_path = resolve_iq_path(
            manifest,
            manifest_path,
            args.iq_path,
            default_generated_path=DEFAULT_IQ_PATH if manifest_path == DEFAULT_MANIFEST.resolve() else None,
        )

    x = read_ci16(iq_path, manifest)
    metrics = compute_metrics(x, manifest, iq_path=iq_path, manifest_path=manifest_path)
    spectrum_path = save_spectrum_plot(x, manifest, metrics, args.out_dir, manifest_path)
    time_path = save_time_plot(x, manifest, args.out_dir, manifest_path)
    metrics_path = save_metrics_json(metrics, args.out_dir)

    print("Lab 9.2 - Read CI16 IQ and analyze spectrum")
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
