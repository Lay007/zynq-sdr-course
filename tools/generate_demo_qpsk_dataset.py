#!/usr/bin/env python3
"""Generate a small deterministic QPSK CI16 dataset for replay labs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "datasets" / "demo_qpsk_capture"
DATA_FILE = DATASET_DIR / "demo_qpsk_capture.ci16"
MANIFEST_FILE = DATASET_DIR / "manifest.yaml"
METRICS_FILE = DATASET_DIR / "metrics.json"

SAMPLE_RATE_HZ = 2_400_000
SYMBOL_RATE_SPS = 300_000
SAMPLES_PER_SYMBOL = SAMPLE_RATE_HZ // SYMBOL_RATE_SPS
NUM_SYMBOLS = 2048
AMPLITUDE = 12_000
SEED = 7020


def generate_qpsk_symbols(num_symbols: int) -> np.ndarray:
    rng = np.random.default_rng(SEED)
    dibits = rng.integers(0, 4, size=num_symbols, dtype=np.uint8)
    mapping = np.array(
        [
            1 + 1j,
            -1 + 1j,
            -1 - 1j,
            1 - 1j,
        ],
        dtype=np.complex64,
    ) / np.sqrt(2.0)
    return mapping[dibits]


def write_ci16(path: Path, samples: np.ndarray) -> str:
    scaled_i = np.round(np.real(samples) * AMPLITUDE).astype("<i2")
    scaled_q = np.round(np.imag(samples) * AMPLITUDE).astype("<i2")
    interleaved = np.empty(scaled_i.size * 2, dtype="<i2")
    interleaved[0::2] = scaled_i
    interleaved[1::2] = scaled_q
    payload = interleaved.tobytes()
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def write_manifest(sha256: str, duration_s: float) -> None:
    manifest_text = f"""dataset_id: demo_qpsk_capture
version: 0.2
status: generated-local
title: Deterministic synthetic QPSK CI16 replay dataset
description: >-
  Small deterministic QPSK IQ dataset for replay, constellation analysis,
  EVM/SNR checks and CI-safe recording-tool validation.
storage: generated-local
url: null
file_name: demo_qpsk_capture.ci16
sha256: {sha256}
format: ci16
endianness: little
i_first: true
sample_rate_hz: {SAMPLE_RATE_HZ}
center_frequency_hz: null
bandwidth_hz: 600000
duration_s: {duration_s:.9f}
source: deterministic-synthetic-generator
generator: tools/generate_demo_qpsk_dataset.py
publication_status: synthetic-public
hardware:
  transmitter: synthetic generator
  receiver: offline replay
  rf_path: none
  attenuation_db: null
  tx_gain_db: null
  rx_gain_db: null
signal:
  modulation: QPSK
  symbol_rate_sps: {SYMBOL_RATE_SPS}
  samples_per_symbol: {SAMPLES_PER_SYMBOL}
  pulse_shape: rectangular
  rolloff: null
  constellation: Gray-like quadrant mapping, normalized before CI16 scaling
analysis_targets:
  - constellation plot
  - EVM estimate
  - SNR estimate
  - frequency offset estimate
  - report-ready metric table
quality_checks:
  checksum_verified: true
  clipping_observed: false
  overload_observed: false
  dc_offset_checked: true
license: MIT-compatible synthetic course fixture
notes:
  - Generated data is synthetic and contains no off-air content.
  - The CI16 file is intentionally generated locally rather than committed as raw binary.
  - Run python tools/generate_demo_qpsk_dataset.py to refresh the file and metrics.
  - Expected generated file size is 65536 bytes.
"""
    MANIFEST_FILE.write_text(manifest_text, encoding="utf-8")


def write_metrics(samples: np.ndarray, sha256: str) -> None:
    mean_i = float(np.mean(np.real(samples)))
    mean_q = float(np.mean(np.imag(samples)))
    rms = float(np.sqrt(np.mean(np.abs(samples) ** 2)))
    peak = float(np.max(np.abs(samples)))
    metrics = {
        "dataset_id": "demo_qpsk_capture",
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "symbol_rate_sps": SYMBOL_RATE_SPS,
        "samples_per_symbol": SAMPLES_PER_SYMBOL,
        "num_symbols": NUM_SYMBOLS,
        "num_samples": int(samples.size),
        "duration_s": samples.size / SAMPLE_RATE_HZ,
        "ci16_amplitude": AMPLITUDE,
        "mean_i": mean_i,
        "mean_q": mean_q,
        "rms_normalized": rms,
        "peak_normalized": peak,
        "sha256": sha256,
        "synthetic": True,
    }
    METRICS_FILE.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Write manifest and metrics without keeping the raw CI16 file. Useful for documentation refreshes.",
    )
    args = parser.parse_args()

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    symbols = generate_qpsk_symbols(NUM_SYMBOLS)
    samples = np.repeat(symbols, SAMPLES_PER_SYMBOL).astype(np.complex64)
    duration_s = samples.size / SAMPLE_RATE_HZ
    sha256 = write_ci16(DATA_FILE, samples)
    write_manifest(sha256, duration_s)
    write_metrics(samples, sha256)

    if args.metadata_only:
        DATA_FILE.unlink(missing_ok=True)

    print(f"Generated {DATA_FILE.relative_to(ROOT)}")
    print(f"SHA256 {sha256}")
    print(f"Samples {samples.size}")
    print(f"Duration {duration_s:.9f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
