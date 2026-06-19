#!/usr/bin/env python3
"""End-to-end BPSK reference package.

This script creates a deterministic BPSK burst and the handoff artifacts needed
for the main course route:

MATLAB reference -> fixed-point exports -> HDL symbol mapper -> future Zynq TX/RX

The package is intentionally synthetic so it can run locally and in CI without
RF hardware while still producing the same kinds of files that a Simulink or
FPGA flow will consume.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
BLOCK_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project"
PACKAGE_DIR = BLOCK_DIR / "assets" / "end_to_end_bpsk_reference"
DOC_ASSET_DIR = ROOT / "docs" / "assets"
MANIFEST_DIR = ROOT / "datasets" / "manifests"
Q15_SCALE = 32767.0


@dataclass(frozen=True)
class BpskConfig:
    dataset_id: str = "end_to_end_bpsk_reference_v1"
    seed: int = 20260619
    center_frequency_hz: float = 915_000_000.0
    symbol_rate_hz: float = 125_000.0
    samples_per_symbol: int = 8
    sample_rate_hz: float = 1_000_000.0
    rolloff: float = 0.35
    rrc_span_symbols: int = 8
    payload_bit_count: int = 256
    preamble_bits: tuple[int, ...] = (
        0,
        0,
        0,
        0,
        0,
        1,
        1,
        0,
        0,
        1,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        1,
        1,
        0,
        0,
        1,
        0,
        1,
        0,
    )
    leading_silence_samples: int = 384
    trailing_silence_samples: int = 640
    tx_amplitude: float = 0.82
    timing_offset_samples: int = 2
    cfo_hz: float = 650.0
    phase_offset_rad: float = 0.31
    noise_rms: float = 0.015
    attenuation_db: float = 50.0
    tx_gain_db: float = -20.0
    rx_gain_db: float = 20.0


@dataclass(frozen=True)
class BpskMetrics:
    dataset_id: str
    bit_count: int
    payload_bit_count: int
    preamble_bit_count: int
    sample_rate_hz: float
    symbol_rate_hz: float
    samples_per_symbol: int
    rrc_tap_count: int
    timing_offset_samples: int
    frequency_offset_hz: float
    phase_offset_rad: float
    ber_total: float
    ber_payload: float
    bit_errors_total: int
    bit_errors_payload: int
    evm_percent: float
    peak_level_dbfs: float
    rms_level_dbfs: float
    capture_sha256: str


def bits_to_bpsk(bits: np.ndarray) -> np.ndarray:
    return np.where(bits == 0, 1.0, -1.0).astype(np.float64)


def rrc_taps(beta: float, span_symbols: int, sps: int) -> np.ndarray:
    half_span = span_symbols * sps // 2
    t = np.arange(-half_span, half_span + 1, dtype=np.float64) / sps
    taps = np.zeros_like(t)

    for idx, ti in enumerate(t):
        if abs(ti) < 1e-12:
            taps[idx] = 1.0 - beta + 4.0 * beta / np.pi
        elif beta > 0.0 and abs(abs(ti) - 1.0 / (4.0 * beta)) < 1e-12:
            taps[idx] = (beta / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * beta))
                + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * beta))
            )
        else:
            numerator = np.sin(np.pi * ti * (1.0 - beta)) + 4.0 * beta * ti * np.cos(
                np.pi * ti * (1.0 + beta)
            )
            denominator = np.pi * ti * (1.0 - (4.0 * beta * ti) ** 2)
            taps[idx] = numerator / denominator

    taps /= np.sqrt(np.sum(taps * taps))
    return taps


def upsample(symbols: np.ndarray, sps: int) -> np.ndarray:
    y = np.zeros(len(symbols) * sps, dtype=np.complex128)
    y[::sps] = symbols.astype(np.complex128)
    return y


def apply_capture_impairments(cfg: BpskConfig, x: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(cfg.seed + 1)
    delayed = np.concatenate(
        [np.zeros(cfg.timing_offset_samples, dtype=np.complex128), x.astype(np.complex128)]
    )[: len(x)]
    t = np.arange(len(delayed), dtype=np.float64) / cfg.sample_rate_hz
    rotated = delayed * np.exp(1j * (2.0 * np.pi * cfg.cfo_hz * t + cfg.phase_offset_rad))
    noise = cfg.noise_rms * (
        rng.standard_normal(len(rotated)) + 1j * rng.standard_normal(len(rotated))
    )
    return rotated + noise


def scalar_align(ref: np.ndarray, rx: np.ndarray) -> np.ndarray:
    n = min(len(ref), len(rx))
    ref_n = ref[:n]
    rx_n = rx[:n]
    gain = np.vdot(ref_n, rx_n) / max(np.vdot(ref_n, ref_n), 1e-15)
    return rx_n / gain


def evm_percent(ref: np.ndarray, rx: np.ndarray) -> float:
    n = min(len(ref), len(rx))
    err = rx[:n] - ref[:n]
    ref_rms = max(np.sqrt(np.mean(np.abs(ref[:n]) ** 2)), 1e-15)
    return float(100.0 * np.sqrt(np.mean(np.abs(err) ** 2)) / ref_rms)


def quantize_q15(values: np.ndarray) -> np.ndarray:
    return np.clip(np.round(values * Q15_SCALE), -32767, 32767).astype(np.int16)


def write_ci16(path: Path, x: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    i = np.clip(np.round(np.real(x) * Q15_SCALE), -32768, 32767).astype("<i2")
    q = np.clip(np.round(np.imag(x) * Q15_SCALE), -32768, 32767).astype("<i2")
    raw = np.empty(2 * len(i), dtype="<i2")
    raw[0::2] = i
    raw[1::2] = q
    raw.tofile(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_vector(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    array = np.asarray(values)
    if array.ndim == 1:
        np.savetxt(path, array, fmt="%.18e")
    else:
        np.savetxt(path, array, fmt="%.18e")


def write_int_vector(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    array = np.asarray(values)
    if array.ndim == 1:
        np.savetxt(path, array, fmt="%d")
    else:
        np.savetxt(path, array, fmt="%d")


def spectrum_db(x: np.ndarray, fs: float, fft_length: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def save_spectrum(path: Path, x: np.ndarray, fs: float, title: str) -> None:
    DOC_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    freq, mag_db = spectrum_db(x, fs)
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_constellation(path: Path, symbols: np.ndarray, title: str) -> None:
    DOC_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shown = symbols[: min(256, len(symbols))]
    plt.figure(figsize=(5.0, 5.0))
    plt.scatter(np.real(shown), np.imag(shown), s=10, alpha=0.7)
    plt.grid(True, alpha=0.35)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.axis("equal")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_matched_filter_trace(
    path: Path,
    matched: np.ndarray,
    sample_start: int,
    sps: int,
    symbol_count: int,
    title: str,
) -> None:
    DOC_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shown_symbols = min(24, symbol_count)
    start = max(sample_start - 2 * sps, 0)
    stop = min(sample_start + shown_symbols * sps, len(matched))
    t = np.arange(start, stop)
    sample_positions = sample_start + np.arange(shown_symbols) * sps
    in_range = sample_positions[(sample_positions >= start) & (sample_positions < stop)]

    plt.figure(figsize=(7.4, 4.3))
    plt.plot(t, np.real(matched[start:stop]), label="matched filter real")
    plt.scatter(in_range, np.real(matched[in_range]), color="tab:red", s=18, label="symbol samples")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Amplitude")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def relative_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(
    cfg: BpskConfig,
    capture_path: Path,
    tx_path: Path,
    checksum: str,
    symbol_path: Path,
    taps_path: Path,
    bits_path: Path,
) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFEST_DIR / f"{cfg.dataset_id}.yml"
    duration_s = len(np.fromfile(capture_path, dtype="<i2")) / 2.0 / cfg.sample_rate_hz
    bandwidth_hz = cfg.symbol_rate_hz * (1.0 + cfg.rolloff)
    content = f"""dataset_id: {cfg.dataset_id}
title: End-to-end BPSK reference package
description: >-
  Deterministic synthetic BPSK burst used as the shared handoff between the
  MATLAB reference model, fixed-point export, HDL symbol mapper and future
  Zynq TX/RX validation.
storage: repo-generated
url: null
file_name: {relative_path(capture_path)}
sha256: {checksum}
format: ci16
endianness: little
sample_rate_hz: {int(cfg.sample_rate_hz)}
center_frequency_hz: {int(cfg.center_frequency_hz)}
bandwidth_hz: {int(round(bandwidth_hz))}
duration_s: {duration_s:.9f}
source: synthetic-bpsk-reference
hardware:
  transmitter: future Zynq/AD9363 BPSK path, currently synthetic reference
  receiver: future Zynq RX BER path, currently synthetic reference receiver
  monitor_receiver: RTL-SDR spectrum-only monitor in the planned hardware route
  rf_path: synthetic channel with deterministic timing, CFO, phase and AWGN
  attenuation_db: {cfg.attenuation_db:.1f}
  tx_gain_db: {cfg.tx_gain_db:.1f}
  rx_gain_db: {cfg.rx_gain_db:.1f}
signal:
  modulation: BPSK
  symbol_rate_sps: {int(cfg.symbol_rate_hz)}
  pulse_shape: RRC
  rolloff: {cfg.rolloff:.3f}
  samples_per_symbol: {cfg.samples_per_symbol}
handoff:
  config_json: {relative_path(PACKAGE_DIR / "config.json")}
  tx_reference_ci16: {relative_path(tx_path)}
  tx_bits_file: {relative_path(bits_path)}
  tx_symbols_q15_file: {relative_path(symbol_path)}
  rrc_taps_q15_file: {relative_path(taps_path)}
  matlab_reference_script: blocks/block_11_integrated_sdr_project/matlab/end_to_end_bpsk_reference.m
  rtl_symbol_mapper: blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v
analysis_targets:
  - matched filter reconstruction
  - payload BER
  - constellation after reference synchronization
  - fixed-point export for Simulink
  - HDL symbol mapper vector generation
expected_results:
  expected_modulation: BPSK
  expected_receiver: matched filter with known timing/CFO/phase
  intended_payload_ber: near zero for the synthetic reference case
quality_checks:
  checksum_verified: true
  clipping_observed: false
  overload_observed: false
  fixed_point_exports_present: true
notes:
  - Use Zynq RX as the main BER receiver path for the first hardware implementation.
  - Use RTL-SDR as an independent monitor receiver, not as the primary BER reference.
"""
    manifest_path.write_text(content, encoding="utf-8")
    package_manifest_path = PACKAGE_DIR / "manifest.yml"
    package_manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


def main() -> int:
    cfg = BpskConfig()
    if not math.isclose(
        cfg.symbol_rate_hz * cfg.samples_per_symbol,
        cfg.sample_rate_hz,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("sample_rate_hz must equal symbol_rate_hz * samples_per_symbol")

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    DOC_ASSET_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(cfg.seed)
    preamble_bits = np.asarray(cfg.preamble_bits, dtype=np.uint8)
    payload_bits = rng.integers(0, 2, size=cfg.payload_bit_count, dtype=np.uint8)
    tx_bits = np.concatenate([preamble_bits, payload_bits])
    tx_symbols = bits_to_bpsk(tx_bits)

    taps = rrc_taps(cfg.rolloff, cfg.rrc_span_symbols, cfg.samples_per_symbol)
    upsampled = upsample(tx_symbols, cfg.samples_per_symbol)
    tx_shaped = np.convolve(upsampled, taps, mode="full")
    tx_shaped *= cfg.tx_amplitude / max(np.max(np.abs(tx_shaped)), 1e-15)

    tx_capture = np.concatenate(
        [
            np.zeros(cfg.leading_silence_samples, dtype=np.complex128),
            tx_shaped,
            np.zeros(cfg.trailing_silence_samples, dtype=np.complex128),
        ]
    )
    rx_capture = apply_capture_impairments(cfg, tx_capture)

    capture_path = PACKAGE_DIR / f"{cfg.dataset_id}.ci16"
    tx_path = PACKAGE_DIR / f"{cfg.dataset_id}_tx_reference.ci16"
    write_ci16(capture_path, rx_capture)
    write_ci16(tx_path, tx_capture)
    checksum = sha256_file(capture_path)

    t = np.arange(len(rx_capture), dtype=np.float64) / cfg.sample_rate_hz
    rx_corrected = rx_capture * np.exp(-1j * (2.0 * np.pi * cfg.cfo_hz * t + cfg.phase_offset_rad))
    matched = np.convolve(rx_corrected, taps, mode="full")
    sample_start = cfg.leading_silence_samples + cfg.timing_offset_samples + len(taps) - 1
    rx_symbol_samples = matched[sample_start :: cfg.samples_per_symbol][: len(tx_symbols)]
    rx_symbol_aligned = scalar_align(tx_symbols, rx_symbol_samples)
    rx_bits = np.where(np.real(rx_symbol_aligned) >= 0.0, 0, 1).astype(np.uint8)

    total_errors = int(np.sum(rx_bits != tx_bits))
    payload_rx_bits = rx_bits[len(preamble_bits) :]
    payload_errors = int(np.sum(payload_rx_bits != payload_bits))
    total_ber = float(total_errors / max(len(tx_bits), 1))
    payload_ber = float(payload_errors / max(len(payload_bits), 1))
    peak_level_dbfs = float(20.0 * np.log10(max(np.max(np.abs(rx_capture)), 1e-15)))
    rms_level_dbfs = float(20.0 * np.log10(max(np.sqrt(np.mean(np.abs(rx_capture) ** 2)), 1e-15)))
    metrics = BpskMetrics(
        dataset_id=cfg.dataset_id,
        bit_count=int(len(tx_bits)),
        payload_bit_count=cfg.payload_bit_count,
        preamble_bit_count=int(len(preamble_bits)),
        sample_rate_hz=cfg.sample_rate_hz,
        symbol_rate_hz=cfg.symbol_rate_hz,
        samples_per_symbol=cfg.samples_per_symbol,
        rrc_tap_count=int(len(taps)),
        timing_offset_samples=cfg.timing_offset_samples,
        frequency_offset_hz=cfg.cfo_hz,
        phase_offset_rad=cfg.phase_offset_rad,
        ber_total=total_ber,
        ber_payload=payload_ber,
        bit_errors_total=total_errors,
        bit_errors_payload=payload_errors,
        evm_percent=evm_percent(tx_symbols, rx_symbol_aligned),
        peak_level_dbfs=peak_level_dbfs,
        rms_level_dbfs=rms_level_dbfs,
        capture_sha256=checksum,
    )

    config_path = PACKAGE_DIR / "config.json"
    config_path.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")

    tx_bits_path = PACKAGE_DIR / "tx_bits.txt"
    tx_symbols_float_path = PACKAGE_DIR / "tx_symbols_float.txt"
    tx_symbols_q15_path = PACKAGE_DIR / "tx_symbols_q15.txt"
    rrc_taps_float_path = PACKAGE_DIR / "rrc_taps_float.txt"
    rrc_taps_q15_path = PACKAGE_DIR / "rrc_taps_q15.txt"
    sample_plan_path = PACKAGE_DIR / "sample_plan.json"
    handoff_path = PACKAGE_DIR / "handoff_files.json"

    write_int_vector(tx_bits_path, tx_bits)
    write_vector(
        tx_symbols_float_path,
        np.column_stack([np.real(tx_symbols), np.imag(tx_symbols)]),
    )
    write_int_vector(
        tx_symbols_q15_path,
        np.column_stack([quantize_q15(np.real(tx_symbols)), np.zeros(len(tx_symbols), dtype=np.int16)]),
    )
    write_vector(rrc_taps_float_path, taps)
    write_int_vector(rrc_taps_q15_path, quantize_q15(taps))
    sample_plan_path.write_text(
        json.dumps(
            {
                "matched_filter_sample_start": int(sample_start),
                "samples_per_symbol": cfg.samples_per_symbol,
                "symbol_count": int(len(tx_symbols)),
                "leading_silence_samples": cfg.leading_silence_samples,
                "timing_offset_samples": cfg.timing_offset_samples,
                "rrc_tap_count": int(len(taps)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    handoff_path.write_text(
        json.dumps(
            {
                "config": relative_path(config_path),
                "tx_bits": relative_path(tx_bits_path),
                "tx_symbols_float": relative_path(tx_symbols_float_path),
                "tx_symbols_q15": relative_path(tx_symbols_q15_path),
                "rrc_taps_float": relative_path(rrc_taps_float_path),
                "rrc_taps_q15": relative_path(rrc_taps_q15_path),
                "tx_reference_ci16": relative_path(tx_path),
                "capture_ci16": relative_path(capture_path),
                "sample_plan": relative_path(sample_plan_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    save_spectrum(
        DOC_ASSET_DIR / "end_to_end_bpsk_reference_tx_spectrum.png",
        tx_capture,
        cfg.sample_rate_hz,
        "End-to-end BPSK reference - TX burst spectrum",
    )
    save_spectrum(
        DOC_ASSET_DIR / "end_to_end_bpsk_reference_capture_spectrum.png",
        rx_capture,
        cfg.sample_rate_hz,
        "End-to-end BPSK reference - captured burst spectrum",
    )
    save_constellation(
        DOC_ASSET_DIR / "end_to_end_bpsk_reference_constellation.png",
        rx_symbol_aligned,
        "End-to-end BPSK reference - matched-filter constellation",
    )
    save_matched_filter_trace(
        DOC_ASSET_DIR / "end_to_end_bpsk_reference_matched_filter.png",
        matched,
        sample_start,
        cfg.samples_per_symbol,
        len(tx_symbols),
        "End-to-end BPSK reference - matched filter and symbol sampling",
    )
    (DOC_ASSET_DIR / "end_to_end_bpsk_reference_metrics.json").write_text(
        json.dumps(asdict(metrics), indent=2),
        encoding="utf-8",
    )

    write_manifest(
        cfg,
        capture_path,
        tx_path,
        checksum,
        tx_symbols_q15_path,
        rrc_taps_q15_path,
        tx_bits_path,
    )

    print(f"Wrote {capture_path}")
    print(f"Wrote {tx_path}")
    print(f"Wrote {config_path}")
    print(f"Wrote {DOC_ASSET_DIR / 'end_to_end_bpsk_reference_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
