#!/usr/bin/env python3
"""Lab 9.1 - IQ file format and metadata.

Demonstrates IQ binary formats (CI16, CU8, CF32), generates a small synthetic
tone file for each, writes a metadata JSON sidecar, and verifies that the
sidecar contains the minimum required fields for reproducible analysis.

Run without arguments to generate all three format examples and print a
compliance report.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_OUT_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools" / "assets"

REQUIRED_METADATA_FIELDS = [
    "sample_rate_hz",
    "center_frequency_hz",
    "iq_format",
    "endianness",
    "i_first",
    "sample_count",
]


@dataclass(frozen=True)
class FormatExample:
    name: str
    iq_format: str
    endianness: str
    dtype: str
    scale_factor: float
    offset: float


FORMATS = [
    FormatExample("CI16", "ci16", "little", "<i2", 32767.0, 0.0),
    FormatExample("CU8",  "cu8",  "little", "B",   127.5,  127.5),
    FormatExample("CF32", "cf32", "little", "<f4", 1.0,    0.0),
]


def make_tone(sample_rate_hz: float, freq_hz: float, sample_count: int, amplitude: float = 0.5) -> np.ndarray:
    n = np.arange(sample_count)
    return amplitude * np.exp(1j * 2.0 * np.pi * freq_hz / sample_rate_hz * n)


def write_ci16(path: Path, iq: np.ndarray) -> None:
    samples = np.empty(len(iq) * 2, dtype="<i2")
    samples[0::2] = np.round(iq.real * 32767.0).clip(-32768, 32767).astype("<i2")
    samples[1::2] = np.round(iq.imag * 32767.0).clip(-32768, 32767).astype("<i2")
    path.write_bytes(samples.tobytes())


def write_cu8(path: Path, iq: np.ndarray) -> None:
    samples = np.empty(len(iq) * 2, dtype=np.uint8)
    samples[0::2] = np.round(iq.real * 127.5 + 127.5).clip(0, 255).astype(np.uint8)
    samples[1::2] = np.round(iq.imag * 127.5 + 127.5).clip(0, 255).astype(np.uint8)
    path.write_bytes(samples.tobytes())


def write_cf32(path: Path, iq: np.ndarray) -> None:
    samples = np.empty(len(iq) * 2, dtype="<f4")
    samples[0::2] = iq.real.astype("<f4")
    samples[1::2] = iq.imag.astype("<f4")
    path.write_bytes(samples.tobytes())


def read_ci16(path: Path, sample_count: int) -> np.ndarray:
    raw = np.frombuffer(path.read_bytes(), dtype="<i2")
    iq = raw[0::2].astype(np.float64) / 32768.0 + 1j * raw[1::2].astype(np.float64) / 32768.0
    return iq[:sample_count]


def read_cu8(path: Path, sample_count: int) -> np.ndarray:
    raw = np.frombuffer(path.read_bytes(), dtype=np.uint8).astype(np.float64)
    i = (raw[0::2] - 127.5) / 127.5
    q = (raw[1::2] - 127.5) / 127.5
    return (i + 1j * q)[:sample_count]


def read_cf32(path: Path, sample_count: int) -> np.ndarray:
    raw = np.frombuffer(path.read_bytes(), dtype="<f4")
    return (raw[0::2].astype(np.float64) + 1j * raw[1::2].astype(np.float64))[:sample_count]


def build_metadata(
    fmt: FormatExample,
    sample_rate_hz: float,
    center_frequency_hz: float,
    sample_count: int,
    expected_offset_hz: float,
    iq_path: Path,
) -> dict[str, Any]:
    return {
        "sample_rate_hz": sample_rate_hz,
        "center_frequency_hz": center_frequency_hz,
        "iq_format": fmt.iq_format,
        "endianness": fmt.endianness,
        "i_first": True,
        "sample_count": sample_count,
        "expected_signal_offset_hz": expected_offset_hz,
        "gain_settings": {"rx_hardwaregain_db": 35, "gain_control_mode": "manual"},
        "iq_path": str(iq_path),
        "file_size_bytes": iq_path.stat().st_size,
    }


def check_metadata_compliance(metadata: dict[str, Any]) -> list[str]:
    missing = [f for f in REQUIRED_METADATA_FIELDS if f not in metadata]
    return missing


def measure_peak_hz(iq: np.ndarray, sample_rate_hz: float) -> float:
    spectrum = np.abs(np.fft.fftshift(np.fft.fft(iq * np.hanning(len(iq)))))
    freqs = np.fft.fftshift(np.fft.fftfreq(len(iq), 1.0 / sample_rate_hz))
    return float(freqs[np.argmax(spectrum)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lab 9.1 — IQ file format and metadata demonstration."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for generated IQ files and metadata.",
    )
    parser.add_argument("--sample-rate-hz", type=float, default=2_400_000.0)
    parser.add_argument("--center-frequency-hz", type=float, default=915_000_000.0)
    parser.add_argument("--tone-offset-hz", type=float, default=100_000.0)
    parser.add_argument("--sample-count", type=int, default=65_536)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ASSET_DIR / "lab91_iq_format_compliance_report.json",
        help="Path for the compliance report JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    iq_ref = make_tone(
        sample_rate_hz=args.sample_rate_hz,
        freq_hz=args.tone_offset_hz,
        sample_count=args.sample_count,
    )

    report: dict[str, Any] = {
        "sample_rate_hz": args.sample_rate_hz,
        "center_frequency_hz": args.center_frequency_hz,
        "tone_offset_hz": args.tone_offset_hz,
        "sample_count": args.sample_count,
        "formats": [],
    }

    writers = {"ci16": write_ci16, "cu8": write_cu8, "cf32": write_cf32}
    readers = {"ci16": read_ci16, "cu8": read_cu8, "cf32": read_cf32}

    for fmt in FORMATS:
        iq_path = out_dir / f"lab91_synthetic_tone_{fmt.iq_format}.{fmt.iq_format}"
        writers[fmt.iq_format](iq_path, iq_ref)

        metadata = build_metadata(
            fmt=fmt,
            sample_rate_hz=args.sample_rate_hz,
            center_frequency_hz=args.center_frequency_hz,
            sample_count=args.sample_count,
            expected_offset_hz=args.tone_offset_hz,
            iq_path=iq_path,
        )
        meta_path = iq_path.with_suffix(".metadata.json")
        meta_path.write_text(json.dumps(metadata, indent=2))

        iq_loaded = readers[fmt.iq_format](iq_path, args.sample_count)
        peak_hz = measure_peak_hz(iq_loaded, args.sample_rate_hz)
        freq_error_hz = abs(peak_hz - args.tone_offset_hz)

        missing = check_metadata_compliance(metadata)
        compliance_pass = len(missing) == 0 and freq_error_hz < args.sample_rate_hz / args.sample_count * 2

        entry: dict[str, Any] = {
            "format": fmt.iq_format,
            "iq_file": str(iq_path),
            "metadata_file": str(meta_path),
            "file_size_bytes": iq_path.stat().st_size,
            "measured_peak_hz": round(peak_hz, 1),
            "frequency_error_hz": round(freq_error_hz, 1),
            "missing_metadata_fields": missing,
            "compliance_pass": compliance_pass,
        }
        report["formats"].append(entry)

        status = "PASS" if compliance_pass else "FAIL"
        print(f"[{status}] {fmt.name:5s}  peak={peak_hz:+.0f} Hz  error={freq_error_hz:.1f} Hz  "
              f"missing={missing or 'none'}  size={iq_path.stat().st_size} B")

    report_path: Path = args.json_out
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nCompliance report: {report_path}")

    all_pass = all(e["compliance_pass"] for e in report["formats"])
    if not all_pass:
        raise SystemExit("One or more format checks failed — see report above.")


if __name__ == "__main__":
    main()
