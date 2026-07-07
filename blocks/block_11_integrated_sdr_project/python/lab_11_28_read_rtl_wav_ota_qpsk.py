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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


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
    resolve_path_hint,
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
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--analysis-window-samples", type=int, default=16_384)
    parser.add_argument("--coarse-candidate-count", type=int, default=7)
    parser.add_argument("--coarse-search-span-hz", type=float, default=1_500_000.0)
    parser.add_argument("--sync-symbol-count", type=int, default=16)
    parser.add_argument("--candidate-count", type=int, default=24)
    parser.add_argument("--multi-burst", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--burst-energy-block-samples", type=int, default=256)
    parser.add_argument("--burst-threshold-mad", type=float, default=10.0)
    parser.add_argument("--burst-peak-mad", type=float, default=15.0)
    parser.add_argument("--burst-merge-gap-blocks", type=int, default=12)
    parser.add_argument("--burst-window-samples", type=int, default=4096)
    parser.add_argument("--normalized-correlation-threshold", type=float, default=0.8)
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
        -float(candidate["normalized_correlation"]),
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
                sync_rx = sampled[symbol_index : symbol_index + sync_count]
                sync_energy = float(np.vdot(sync, sync).real)
                rx_energy = float(np.vdot(sync_rx, sync_rx).real)
                normalized_correlation = float(
                    abs(np.vdot(sync, sync_rx))
                    / math.sqrt(max(sync_energy * rx_energy, 1e-30))
                )
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
                    "normalized_correlation": normalized_correlation,
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


def detect_burst_centers(x: np.ndarray, args: argparse.Namespace) -> tuple[list[int], dict[str, Any]]:
    block_samples = max(int(args.burst_energy_block_samples), 16)
    block_count = len(x) // block_samples
    if block_count < 3:
        raise RuntimeError("Capture is too short for block-energy burst detection")
    used = x[: block_count * block_samples]
    block_power = np.mean(
        np.abs(used.reshape(block_count, block_samples)) ** 2,
        axis=1,
    )
    median_power = float(np.median(block_power))
    mad_power = float(np.median(np.abs(block_power - median_power)))
    robust_scale = max(mad_power, median_power * 1e-6, 1e-15)
    threshold = median_power + float(args.burst_threshold_mad) * robust_scale
    peak_threshold = median_power + float(args.burst_peak_mad) * robust_scale
    active = np.flatnonzero(block_power > threshold)

    groups: list[list[int]] = []
    merge_gap = max(int(args.burst_merge_gap_blocks), 0)
    for block_index in active.tolist():
        if not groups or block_index - groups[-1][-1] > merge_gap:
            groups.append([int(block_index)])
        else:
            groups[-1].append(int(block_index))
    groups = [group for group in groups if float(np.max(block_power[group])) > peak_threshold]
    centers = [
        int(round((group[0] + group[-1] + 1) * block_samples / 2.0))
        for group in groups
    ]
    detector = {
        "block_samples": block_samples,
        "median_block_power": median_power,
        "mad_block_power": mad_power,
        "threshold_mad_multiplier": float(args.burst_threshold_mad),
        "peak_mad_multiplier": float(args.burst_peak_mad),
        "power_threshold": threshold,
        "peak_power_threshold": peak_threshold,
        "merge_gap_blocks": merge_gap,
        "energy_candidate_count": len(centers),
    }
    return centers, detector


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
    return [float(max(center - half_width, 0.0)), float(min(center + half_width, 1.0))]


def distribution_summary(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    data = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(data)),
        "median": float(np.median(data)),
        "mean": float(np.mean(data)),
        "p95": float(np.quantile(data, 0.95)),
        "max": float(np.max(data)),
        "std": float(np.std(data)),
    }


def commanded_burst_count(manifest: dict[str, Any], manifest_path: Path | None) -> int | None:
    hardware = manifest.get("hardware", {})
    if hardware.get("runtime_repeat_count") is not None:
        return int(hardware["runtime_repeat_count"])
    capture_report = resolve_path_hint(
        manifest.get("analysis", {}).get("capture_report_json"),
        manifest_path=manifest_path,
    )
    if capture_report is None:
        return None
    payload = json.loads(capture_report.read_text(encoding="utf-8"))
    value = payload.get("config", {}).get("runtime_repeat_count")
    return int(value) if value is not None else None


def analyze_bursts(
    x: np.ndarray,
    *,
    capture_sample_rate_hz: float,
    expected_signal_offset_hz: float,
    symbol_rate_hz: float,
    tx_sps: int,
    rolloff: float,
    span_symbols: int,
    tx_bits: np.ndarray,
    tx_symbols: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, dict[str, Any], list[dict[str, Any]], dict[str, Any], np.ndarray]:
    centers, detector = detect_burst_centers(x, args)
    native_sps = capture_sample_rate_hz / symbol_rate_hz
    if abs(native_sps - round(native_sps)) < 1e-9:
        analysis_sps = int(round(native_sps))
        burst_sample_rate_hz = float(capture_sample_rate_hz)
    else:
        analysis_sps = tx_sps
        burst_sample_rate_hz = float(symbol_rate_hz * tx_sps)
    taps = rrc_taps(rolloff, span_symbols, analysis_sps).astype(np.float32)
    capture_window_samples = max(int(args.burst_window_samples), len(tx_symbols) * 2)
    rows: list[dict[str, Any]] = []
    accepted_symbols: list[np.ndarray] = []
    best: dict[str, Any] | None = None
    best_window: np.ndarray | None = None

    for burst_index, center_sample in enumerate(centers):
        capture_start = min(
            max(center_sample - capture_window_samples // 2, 0),
            max(len(x) - capture_window_samples, 0),
        )
        window = x[capture_start : capture_start + capture_window_samples]
        # The full capture has already had its global DC estimate removed. Do not
        # subtract a per-burst mean here: a finite deterministic QPSK frame need
        # not have exactly zero mean, so doing so would modify the wanted signal.
        window = mix_frequency(window, capture_sample_rate_hz, expected_signal_offset_hz)
        if burst_sample_rate_hz != capture_sample_rate_hz:
            window = resample_complex_linear(
                window,
                capture_sample_rate_hz,
                burst_sample_rate_hz,
            )
        matched = np.convolve(window, taps, mode="full")
        detection = detect_frame(
            matched,
            tx_bits=tx_bits,
            tx_symbols=tx_symbols,
            sps=analysis_sps,
            sample_rate_hz=burst_sample_rate_hz,
            sync_symbol_count=args.sync_symbol_count,
            candidate_count=args.candidate_count,
        )
        accepted = bool(
            detection["normalized_correlation"] >= args.normalized_correlation_threshold
        )
        residual = float(detection["residual_cfo_hz"])
        total_frequency_shift_hz = float(
            expected_signal_offset_hz - residual
            if detection["conjugated"]
            else expected_signal_offset_hz + residual
        )
        row = {
            "burst_index": burst_index,
            "center_capture_sample": center_sample,
            "center_time_s": float(center_sample / capture_sample_rate_hz),
            "capture_window_start_sample": capture_start,
            "detected": accepted,
            "normalized_correlation": detection["normalized_correlation"],
            "correlation_abs": detection["correlation_abs"],
            "bit_errors": detection["bit_errors_total"],
            "ber": detection["ber_total"],
            "frame_error": bool(detection["bit_errors_total"] != 0),
            "evm_percent": detection["evm_percent"],
            "snr_from_evm_db": detection["snr_from_evm_db"],
            "residual_cfo_hz": residual,
            "total_frequency_shift_hz": total_frequency_shift_hz,
            "sample_phase": detection["sample_phase"],
            "conjugated": detection["conjugated"],
        }
        rows.append(row)
        if not accepted:
            continue
        accepted_symbols.append(detection["rx_symbols"])
        detection["coarse_frequency_hz"] = float(expected_signal_offset_hz)
        detection["total_frequency_shift_hz"] = total_frequency_shift_hz
        detection["analysis_window_start_sample"] = capture_start
        if best is None or candidate_rank(detection) < candidate_rank(best):
            best = detection
            best_window = window

    if best is None or best_window is None or not accepted_symbols:
        raise RuntimeError("No QPSK burst passed the normalized-correlation detection gate")
    detector.update(
        {
            "normalized_correlation_threshold": float(args.normalized_correlation_threshold),
            "detected_burst_count": int(sum(row["detected"] for row in rows)),
            "analysis_sample_rate_hz": burst_sample_rate_hz,
            "analysis_samples_per_symbol": analysis_sps,
            "capture_window_samples": capture_window_samples,
        }
    )
    return best_window, best, rows, detector, np.concatenate(accepted_symbols)


def summarize_bursts(
    rows: list[dict[str, Any]],
    *,
    bits_per_burst: int,
    commanded_count: int | None,
) -> dict[str, Any]:
    detected = [row for row in rows if row["detected"]]
    detected_count = len(detected)
    zero_error_count = sum(int(row["bit_errors"] == 0) for row in detected)
    frame_error_count = detected_count - zero_error_count
    total_bits = detected_count * bits_per_burst
    total_errors = sum(int(row["bit_errors"]) for row in detected)
    aggregate_ber = float(total_errors / total_bits) if total_bits else None
    return {
        "commanded_burst_count": commanded_count,
        "energy_candidate_count": len(rows),
        "detected_burst_count": detected_count,
        "detection_rate_vs_commanded": (
            float(detected_count / commanded_count) if commanded_count else None
        ),
        "zero_error_burst_count": zero_error_count,
        "zero_error_burst_rate": (
            float(zero_error_count / detected_count) if detected_count else None
        ),
        "zero_error_burst_rate_wilson_95": wilson_interval(zero_error_count, detected_count),
        "frame_error_count": frame_error_count,
        "frame_error_rate": float(frame_error_count / detected_count) if detected_count else None,
        "compared_bits_total": total_bits,
        "bit_errors_total": total_errors,
        "aggregate_ber": aggregate_ber,
        "aggregate_ber_wilson_95": wilson_interval(total_errors, total_bits),
        "zero_error_ber_upper_95_rule_of_three": (
            float(3.0 / total_bits) if total_bits and total_errors == 0 else None
        ),
        "bit_errors_per_burst": distribution_summary(
            [float(row["bit_errors"]) for row in detected]
        ),
        "evm_percent": distribution_summary([float(row["evm_percent"]) for row in detected]),
        "snr_from_evm_db": distribution_summary(
            [float(row["snr_from_evm_db"]) for row in detected]
        ),
        "frequency_shift_hz": distribution_summary(
            [float(row["total_frequency_shift_hz"]) for row in detected]
        ),
        "normalized_correlation": distribution_summary(
            [float(row["normalized_correlation"]) for row in detected]
        ),
    }


def save_multiburst_metrics(path: Path, rows: list[dict[str, Any]]) -> None:
    detected = [row for row in rows if row["detected"]]
    indices = [row["burst_index"] for row in detected]
    fig, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    bit_errors = [row["bit_errors"] for row in detected]
    axes[0].bar(indices, bit_errors)
    axes[0].set_ylabel("Bit errors / 280")
    axes[0].grid(True, axis="y")
    if bit_errors and max(bit_errors) == 0:
        axes[0].set_ylim(0.0, 1.0)
        axes[0].text(
            0.5,
            0.5,
            f"{len(bit_errors)}/{len(bit_errors)} bursts: zero bit errors",
            ha="center",
            va="center",
            transform=axes[0].transAxes,
        )
    axes[1].plot(indices, [row["evm_percent"] for row in detected], "o-")
    axes[1].set_ylabel("EVM RMS, %")
    axes[1].grid(True)
    axes[2].plot(indices, [row["total_frequency_shift_hz"] for row in detected], "o-")
    axes[2].set_ylabel("CFO, Hz")
    axes[2].set_xlabel("Burst index")
    axes[2].grid(True)
    fig.suptitle("RTL-SDR OTA QPSK per-burst metrics")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


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
    dc_offset = complex(np.mean(x))
    raw_peak_dbfs = float(20.0 * np.log10(max(float(np.max(np.abs(x))), 1e-15)))
    raw_rms_dbfs = float(
        20.0 * np.log10(max(float(np.sqrt(np.mean(np.abs(x) ** 2))), 1e-15))
    )
    clipping_fraction = float(
        np.mean((np.abs(np.real(x)) > 0.999) | (np.abs(np.imag(x)) > 0.999))
    )
    x = (x - dc_offset).astype(np.complex64)
    capture_sha256 = sha256_file(iq_path)

    burst_rows: list[dict[str, Any]] | None = None
    burst_detector: dict[str, Any] | None = None
    burst_summary: dict[str, Any] | None = None
    all_burst_symbols: np.ndarray | None = None
    coarse_candidates: list[float] = [expected_signal_offset_hz]
    if args.multi_burst:
        analysis_window, detection, burst_rows, burst_detector, all_burst_symbols = analyze_bursts(
            x,
            capture_sample_rate_hz=wav_info.sample_rate_hz,
            expected_signal_offset_hz=expected_signal_offset_hz,
            symbol_rate_hz=symbol_rate_hz,
            tx_sps=sps,
            rolloff=rolloff,
            span_symbols=span_symbols,
            tx_bits=tx_bits,
            tx_symbols=tx_symbols,
            args=args,
        )
        analysis_sample_rate_hz = float(burst_detector["analysis_sample_rate_hz"])
        burst_summary = summarize_bursts(
            burst_rows,
            bits_per_burst=len(tx_bits),
            commanded_count=commanded_burst_count(manifest, manifest_path),
        )
    else:
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
    multiburst_metrics_path = out_dir / f"{prefix}_multiburst_metrics.png"
    multiburst_constellation_path = out_dir / f"{prefix}_multiburst_constellation.png"

    metrics = {
        "analysis_schema_version": 2,
        "metric_definition": "docs/digital-link-metrics.md",
        "analysis_mode": "multi_burst" if args.multi_burst else "single_best_frame",
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
        "transmitter_samples_per_symbol": sps,
        "analysis_samples_per_symbol": (
            int(burst_detector["analysis_samples_per_symbol"])
            if burst_detector is not None
            else sps
        ),
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
        "raw_crest_factor_db": float(raw_peak_dbfs - raw_rms_dbfs),
        "raw_dc_offset_i": float(dc_offset.real),
        "raw_dc_offset_q": float(dc_offset.imag),
        "raw_clipping_fraction": clipping_fraction,
        "selected_frame": {
            "bit_errors": detection["bit_errors_total"],
            "ber": detection["ber_total"],
            "evm_percent": detection["evm_percent"],
            "snr_from_evm_db": detection["snr_from_evm_db"],
            "normalized_correlation": detection["normalized_correlation"],
            "frequency_shift_hz": detection["total_frequency_shift_hz"],
        },
        "burst_analysis": (
            {
                "detector": burst_detector,
                "summary": burst_summary,
                "frames": burst_rows,
            }
            if burst_rows is not None
            else None
        ),
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
    if burst_rows is not None and all_burst_symbols is not None:
        save_multiburst_metrics(multiburst_metrics_path, burst_rows)
        save_constellation(
            multiburst_constellation_path,
            all_burst_symbols,
            "RTL-SDR OTA QPSK - all detected bursts",
        )
    if manifest_path is not None and manifest_path.suffix.lower() in {".yaml", ".yml"}:
        manifest["sha256"] = capture_sha256
        manifest.setdefault("quality_checks", {})["offline_analysis_completed"] = True
        analysis_meta = manifest.setdefault("analysis", {})
        analysis_meta["metrics_json"] = repo_relative_or_str(metrics_path)
        analysis_meta["raw_spectrum_plot"] = repo_relative_or_str(raw_spectrum_path)
        analysis_meta["baseband_spectrum_plot"] = repo_relative_or_str(spectrum_path)
        analysis_meta["constellation_plot"] = repo_relative_or_str(constellation_path)
        if burst_rows is not None:
            manifest.setdefault("quality_checks", {})["multi_burst_analysis_completed"] = True
            analysis_meta["multiburst_metrics_plot"] = repo_relative_or_str(
                multiburst_metrics_path
            )
            analysis_meta["multiburst_constellation_plot"] = repo_relative_or_str(
                multiburst_constellation_path
            )
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
    if burst_summary is not None:
        print(
            "Bursts: "
            f"detected {burst_summary['detected_burst_count']}/"
            f"{burst_summary['commanded_burst_count'] or burst_summary['energy_candidate_count']}, "
            f"BER=0 {burst_summary['zero_error_burst_count']}/"
            f"{burst_summary['detected_burst_count']}, "
            f"aggregate BER {burst_summary['aggregate_ber']:.6e}"
        )
    print(f"Metrics: {repo_relative_or_str(metrics_path)}")
    print(f"Raw spectrum: {repo_relative_or_str(raw_spectrum_path)}")
    print(f"Baseband spectrum: {repo_relative_or_str(spectrum_path)}")
    print(f"Constellation: {repo_relative_or_str(constellation_path)}")
    if burst_rows is not None:
        print(f"Multi-burst metrics: {repo_relative_or_str(multiburst_metrics_path)}")
        print(
            "Multi-burst constellation: "
            f"{repo_relative_or_str(multiburst_constellation_path)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
