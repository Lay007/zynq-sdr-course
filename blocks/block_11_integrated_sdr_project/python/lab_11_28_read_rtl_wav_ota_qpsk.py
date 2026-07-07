#!/usr/bin/env python3
"""Lab 11.28 - Demodulate the runtime QPSK ROM frame from an RTL-SDR WAV."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
BLOCK11_PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
if str(BLOCK11_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK11_PYTHON_DIR))

from end_to_end_bpsk_reference import evm_percent, rrc_taps, scalar_align  # noqa: E402
from lab_11_14_stock_shell_bpsk_ota import (  # noqa: E402
    repo_relative_or_str,
    save_constellation,
    save_spectrum,
)
from lab_11_20_read_rtl_wav_ota_bpsk_ber import (  # noqa: E402
    crop_active_window,
    estimate_coarse_frequency_candidates,
    load_manifest,
    mix_frequency,
    read_wav_iq,
    resample_complex_linear,
    resolve_iq_path,
    sanitize_token,
)


DOC_ASSET_DIR = ROOT / "docs" / "assets"
FRAME_BITS_MEM = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "rtl" / "bpsk_frame_bits.mem"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--iq-path", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=DOC_ASSET_DIR)
    parser.add_argument("--symbol-count", type=int, default=None)
    parser.add_argument("--skip-samples", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=6_000_000)
    parser.add_argument("--analysis-window-samples", type=int, default=16_384)
    parser.add_argument("--coarse-candidate-count", type=int, default=7)
    parser.add_argument("--coarse-search-span-hz", type=float, default=1_500_000.0)
    parser.add_argument("--sync-symbol-count", type=int, default=16)
    parser.add_argument("--candidate-count", type=int, default=24)
    parser.add_argument("--run-tag", default=None)
    return parser.parse_args()


def load_reference(symbol_count: int) -> tuple[np.ndarray, np.ndarray]:
    bits = np.array(
        [int(token, 0) for token in FRAME_BITS_MEM.read_text(encoding="utf-8").split()],
        dtype=np.uint8,
    )
    needed = symbol_count * 2
    if len(bits) < needed:
        raise ValueError(f"QPSK reference needs {needed} bits, but {FRAME_BITS_MEM} has {len(bits)}")
    bits = bits[:needed]
    i_axis = np.where(bits[0::2] == 0, 1.0, -1.0)
    q_axis = np.where(bits[1::2] == 0, 1.0, -1.0)
    symbols = (i_axis + 1j * q_axis) / math.sqrt(2.0)
    return bits, symbols.astype(np.complex128)


def candidate_rank(candidate: dict[str, Any]) -> tuple[int, float, float]:
    return (
        int(candidate["bit_errors_total"]),
        float(candidate["evm_percent"]),
        -float(candidate["correlation_abs"]),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_frame(
    matched: np.ndarray,
    *,
    tx_bits: np.ndarray,
    tx_symbols: np.ndarray,
    sps: int,
    sample_rate_hz: float,
    sync_symbol_count: int,
    candidate_count: int,
) -> dict[str, Any]:
    sync_count = min(max(sync_symbol_count, 4), len(tx_symbols))
    sync = tx_symbols[:sync_count]
    best: dict[str, Any] | None = None

    for conjugated in (False, True):
        oriented = np.conj(matched) if conjugated else matched
        for sample_phase in range(sps):
            sampled = oriented[sample_phase::sps]
            if len(sampled) < len(tx_symbols):
                continue
            corr = np.correlate(sampled, sync, mode="valid")
            valid_count = len(sampled) - len(tx_symbols) + 1
            if valid_count <= 0:
                continue
            corr = corr[:valid_count]
            ranked = np.argsort(np.abs(corr))[-max(candidate_count, 1) :]
            for symbol_index in ranked.tolist():
                raw_frame = sampled[symbol_index : symbol_index + len(tx_symbols)]
                ratio = raw_frame * np.conj(tx_symbols)
                phase = np.unwrap(np.angle(ratio))
                n = np.arange(len(raw_frame), dtype=np.float64)
                slope, _ = np.polyfit(n, phase, 1)
                cfo_corrected = raw_frame * np.exp(-1j * slope * n)
                aligned = scalar_align(tx_symbols, cfo_corrected)
                rx_bits = np.empty(len(tx_bits), dtype=np.uint8)
                rx_bits[0::2] = np.real(aligned) < 0.0
                rx_bits[1::2] = np.imag(aligned) < 0.0
                errors = int(np.sum(rx_bits != tx_bits))
                evm = float(evm_percent(tx_symbols, aligned))
                residual_cfo_hz = float(slope * sample_rate_hz / (2.0 * np.pi * sps))
                candidate = {
                    "bit_errors_total": errors,
                    "ber_total": float(errors / len(tx_bits)),
                    "evm_percent": evm,
                    "snr_from_evm_db": float(-20.0 * math.log10(max(evm / 100.0, 1e-15))),
                    "correlation_abs": float(abs(corr[symbol_index])),
                    "sample_phase": sample_phase,
                    "symbol_index": int(symbol_index),
                    "matched_filter_start_sample": int(sample_phase + symbol_index * sps),
                    "conjugated": conjugated,
                    "residual_cfo_hz": residual_cfo_hz,
                    "rx_symbols": aligned,
                    "rx_bits": rx_bits,
                }
                if best is None or candidate_rank(candidate) < candidate_rank(best):
                    best = candidate

    if best is None:
        raise RuntimeError("Unable to find a complete QPSK frame in the analysis window")
    return best


def analyze(
    x: np.ndarray,
    *,
    capture_sample_rate_hz: float,
    expected_signal_offset_hz: float,
    symbol_rate_hz: float,
    analysis_sample_rate_hz: float,
    sps: int,
    rolloff: float,
    span_symbols: int,
    tx_bits: np.ndarray,
    tx_symbols: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, dict[str, Any], list[float]]:
    occupied_bandwidth_hz = symbol_rate_hz * (1.0 + rolloff)
    coarse_candidates = estimate_coarse_frequency_candidates(
        x,
        capture_sample_rate_hz,
        expected_signal_offset_hz=expected_signal_offset_hz,
        occupied_bandwidth_hz=occupied_bandwidth_hz,
        candidate_count=args.coarse_candidate_count,
        coarse_search_span_hz=args.coarse_search_span_hz,
    )
    taps = rrc_taps(rolloff, span_symbols, sps)
    best: dict[str, Any] | None = None
    best_window: np.ndarray | None = None

    for coarse_hz in coarse_candidates:
        shifted = mix_frequency(x, capture_sample_rate_hz, coarse_hz)
        resampled = resample_complex_linear(shifted, capture_sample_rate_hz, analysis_sample_rate_hz)
        window, window_start = crop_active_window(resampled, args.analysis_window_samples)
        window = window - np.mean(window)
        matched = np.convolve(window, taps, mode="full")
        detection = detect_frame(
            matched,
            tx_bits=tx_bits,
            tx_symbols=tx_symbols,
            sps=sps,
            sample_rate_hz=analysis_sample_rate_hz,
            sync_symbol_count=args.sync_symbol_count,
            candidate_count=args.candidate_count,
        )
        detection["coarse_frequency_hz"] = float(coarse_hz)
        detection["analysis_window_start_sample"] = int(window_start)
        residual = float(detection["residual_cfo_hz"])
        detection["total_frequency_shift_hz"] = float(
            coarse_hz - residual if detection["conjugated"] else coarse_hz + residual
        )
        if best is None or candidate_rank(detection) < candidate_rank(best):
            best = detection
            best_window = window

    if best is None or best_window is None:
        raise RuntimeError("Unable to demodulate QPSK from the RTL-SDR capture")
    return best_window, best, coarse_candidates


def main() -> int:
    args = parse_args()
    if args.manifest is None and args.iq_path is None:
        raise SystemExit("Pass --manifest or --iq-path")
    manifest_path = args.manifest.resolve() if args.manifest is not None else None
    manifest = load_manifest(manifest_path) if manifest_path is not None else {}
    iq_path = resolve_iq_path(manifest, manifest_path, args.iq_path)
    signal = manifest.get("signal", {})
    symbol_count = int(args.symbol_count or signal.get("transmitted_symbol_count", 140))
    symbol_rate_hz = float(signal.get("symbol_rate_hz", 480_000.0))
    sps = int(signal.get("samples_per_symbol", 8))
    rolloff = float(signal.get("rolloff", 0.35))
    span_symbols = int(signal.get("rrc_span_symbols", 8))
    analysis_sample_rate_hz = symbol_rate_hz * sps
    expected_signal_offset_hz = float(signal.get("expected_signal_offset_hz", 0.0))
    tx_bits, tx_symbols = load_reference(symbol_count)

    x, wav_info = read_wav_iq(
        iq_path,
        manifest,
        skip_samples=args.skip_samples,
        max_samples=args.max_samples,
    )
    x = (x - np.mean(x)).astype(np.complex64)
    raw_peak_dbfs = float(20.0 * np.log10(max(float(np.max(np.abs(x))), 1e-15)))
    raw_rms_dbfs = float(20.0 * np.log10(max(float(np.sqrt(np.mean(np.abs(x) ** 2))), 1e-15)))
    clipping_fraction = float(
        np.mean((np.abs(np.real(x)) > 0.999) | (np.abs(np.imag(x)) > 0.999))
    )
    capture_sha256 = sha256_file(iq_path)

    analysis_window, detection, coarse_candidates = analyze(
        x,
        capture_sample_rate_hz=wav_info.sample_rate_hz,
        expected_signal_offset_hz=expected_signal_offset_hz,
        symbol_rate_hz=symbol_rate_hz,
        analysis_sample_rate_hz=analysis_sample_rate_hz,
        sps=sps,
        rolloff=rolloff,
        span_symbols=span_symbols,
        tx_bits=tx_bits,
        tx_symbols=tx_symbols,
        args=args,
    )

    dataset_id = str(manifest.get("dataset_id", iq_path.stem))
    prefix = f"lab1128_{sanitize_token(dataset_id)}"
    if args.run_tag:
        prefix += f"_{sanitize_token(args.run_tag)}"
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / f"{prefix}_metrics.json"
    raw_spectrum_path = out_dir / f"{prefix}_raw_capture_spectrum.png"
    spectrum_path = out_dir / f"{prefix}_baseband_spectrum.png"
    constellation_path = out_dir / f"{prefix}_constellation.png"

    metrics = {
        "dataset_id": dataset_id,
        "iq_path": str(iq_path),
        "capture_sha256": capture_sha256,
        "manifest_path": str(manifest_path) if manifest_path is not None else None,
        "capture_sample_rate_hz": wav_info.sample_rate_hz,
        "analysis_sample_rate_hz": analysis_sample_rate_hz,
        "center_frequency_hz": float(manifest.get("center_frequency_hz", 0.0)),
        "processed_input_samples": wav_info.frames_read,
        "duration_s_read": wav_info.duration_s,
        "symbol_rate_hz": symbol_rate_hz,
        "samples_per_symbol": sps,
        "symbol_count": symbol_count,
        "compared_bit_count": len(tx_bits),
        "bit_errors_total": detection["bit_errors_total"],
        "ber_total": detection["ber_total"],
        "evm_percent": detection["evm_percent"],
        "snr_from_evm_db": detection["snr_from_evm_db"],
        "expected_signal_offset_hz": expected_signal_offset_hz,
        "coarse_frequency_candidates_hz": [float(value) for value in coarse_candidates],
        "selected_coarse_frequency_hz": detection["coarse_frequency_hz"],
        "residual_cfo_hz": detection["residual_cfo_hz"],
        "total_frequency_shift_hz": detection["total_frequency_shift_hz"],
        "conjugated": detection["conjugated"],
        "sample_phase": detection["sample_phase"],
        "analysis_window_start_sample": detection["analysis_window_start_sample"],
        "matched_filter_start_sample": detection["matched_filter_start_sample"],
        "correlation_abs": detection["correlation_abs"],
        "raw_peak_level_dbfs": raw_peak_dbfs,
        "raw_rms_level_dbfs": raw_rms_dbfs,
        "raw_clipping_fraction": clipping_fraction,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    save_spectrum(raw_spectrum_path, x, wav_info.sample_rate_hz, "RTL-SDR OTA QPSK - raw spectrum")
    save_spectrum(
        spectrum_path,
        analysis_window,
        analysis_sample_rate_hz,
        "RTL-SDR OTA QPSK - selected baseband window",
    )
    save_constellation(
        constellation_path,
        detection["rx_symbols"],
        "RTL-SDR OTA QPSK - aligned matched-filter symbols",
    )
    if manifest_path is not None and manifest_path.suffix.lower() in {".yaml", ".yml"}:
        manifest["sha256"] = capture_sha256
        manifest.setdefault("quality_checks", {})["offline_analysis_completed"] = True
        analysis_meta = manifest.setdefault("analysis", {})
        analysis_meta["metrics_json"] = repo_relative_or_str(metrics_path)
        analysis_meta["raw_spectrum_plot"] = repo_relative_or_str(raw_spectrum_path)
        analysis_meta["baseband_spectrum_plot"] = repo_relative_or_str(spectrum_path)
        analysis_meta["constellation_plot"] = repo_relative_or_str(constellation_path)
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )

    print("Lab 11.28 - RTL-SDR OTA QPSK analysis")
    print(f"IQ file: {iq_path}")
    print(f"Compared bits: {len(tx_bits)}")
    print(f"Bit errors: {detection['bit_errors_total']}")
    print(f"BER: {detection['ber_total']:.6e}")
    print(f"EVM: {detection['evm_percent']:.3f} %")
    print(f"SNR from EVM: {detection['snr_from_evm_db']:.2f} dB")
    print(f"Frequency shift: {detection['total_frequency_shift_hz']:.1f} Hz")
    print(f"Clipping fraction: {clipping_fraction:.6e}")
    print(f"Metrics: {repo_relative_or_str(metrics_path)}")
    print(f"Raw spectrum: {repo_relative_or_str(raw_spectrum_path)}")
    print(f"Baseband spectrum: {repo_relative_or_str(spectrum_path)}")
    print(f"Constellation: {repo_relative_or_str(constellation_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
