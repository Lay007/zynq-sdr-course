#!/usr/bin/env python3
"""Lab 11.20 - Read RTL-SDR WAV IQ, demodulate OTA BPSK, and measure BER."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
BLOCK11_PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
BLOCK09_PYTHON_DIR = ROOT / "blocks" / "block_09_recording_and_analysis_tools" / "python"
if str(BLOCK11_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK11_PYTHON_DIR))
if str(BLOCK09_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK09_PYTHON_DIR))

from end_to_end_bpsk_reference import bits_to_bpsk, evm_percent, scalar_align  # noqa: E402
from lab_11_14_stock_shell_bpsk_ota import (  # noqa: E402
    DEFAULT_CANDIDATE_COUNT,
    DEFAULT_CENTER_FREQUENCY_HZ,
    DEFAULT_PAYLOAD_BIT_COUNT,
    DEFAULT_RF_BANDWIDTH_HZ,
    DEFAULT_ROLLOFF,
    DEFAULT_RRC_SPAN_SYMBOLS,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_SAMPLES_PER_SYMBOL,
    DEFAULT_SYMBOL_RATE_HZ,
    DEFAULT_TX_AMPLITUDE,
    DetectionResult,
    WaveformConfig,
    generate_bpsk_burst,
    repo_relative_or_str,
    save_constellation,
    save_matched_filter_trace,
    save_spectrum,
)


DOC_ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_MANIFEST = ROOT / "datasets" / "lab1_0_rtl_sdr_observation" / "manifest_narrowband_220860000.yaml"
DEFAULT_REFERENCE_METRICS_JSON = ROOT / "docs" / "assets" / "lab114_stock_shell_bpsk_ota_live_20260623d_metrics.json"


@dataclass(frozen=True)
class WavIqInfo:
    channels: int
    sample_width_bytes: int
    sample_rate_hz: float
    frame_count: int
    frames_read: int
    start_frame: int
    duration_s: float


@dataclass(frozen=True)
class RtlWavBerMetrics:
    dataset_id: str
    iq_path: str
    manifest_path: str | None
    reference_metrics_json: str | None
    reference_config_json: str | None
    capture_sample_rate_hz: float
    analysis_sample_rate_hz: float
    capture_center_frequency_hz: float
    expected_signal_offset_hz: float
    coarse_frequency_candidates_hz: list[float]
    selected_coarse_frequency_hz: float
    selected_fine_frequency_hz: float
    total_frequency_shift_hz: float
    processed_input_samples: int
    processed_analysis_samples: int
    analysis_window_start_sample: int
    analysis_window_samples: int
    duration_s_read: float
    peak_level_dbfs: float
    rms_level_dbfs: float
    clipping_fraction: float
    detection: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--iq-path", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=DOC_ASSET_DIR)
    parser.add_argument("--reference-metrics-json", type=Path, default=None)
    parser.add_argument("--reference-config-json", type=Path, default=None)
    parser.add_argument("--expected-signal-offset-hz", type=float, default=None)
    parser.add_argument("--skip-samples", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=4_000_000)
    parser.add_argument("--analysis-window-samples", type=int, default=262_144)
    parser.add_argument("--coarse-candidate-count", type=int, default=5)
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--coarse-search-span-hz", type=float, default=None)
    parser.add_argument("--fine-search-hz", type=float, default=12_000.0)
    parser.add_argument("--fine-step-hz", type=float, default=1_000.0)
    parser.add_argument("--run-tag", default=None)
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported manifest format: {path}")


def resolve_path_hint(
    raw_path: str | None,
    *,
    manifest_path: Path | None,
) -> Path | None:
    if not raw_path:
        return None
    expanded = os.path.expandvars(str(raw_path))
    candidate = Path(expanded).expanduser()
    if candidate.exists():
        return candidate.resolve()
    if manifest_path is not None:
        sibling = manifest_path.parent / str(raw_path)
        if sibling.exists():
            return sibling.resolve()
    repo_candidate = ROOT / str(raw_path)
    if repo_candidate.exists():
        return repo_candidate.resolve()
    return None


def resolve_iq_path(manifest: dict[str, Any], manifest_path: Path | None, explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path.expanduser().resolve()

    for key in ("local_path_hint_windows", "local_path", "file_name"):
        candidate = resolve_path_hint(manifest.get(key), manifest_path=manifest_path)
        if candidate is not None:
            return candidate

    raise FileNotFoundError(
        "Unable to locate the WAV IQ file. Pass --iq-path or add local_path_hint_windows/local_path/file_name."
    )


def load_reference_metrics(reference_path: Path) -> dict[str, Any]:
    return json.loads(reference_path.read_text(encoding="utf-8"))


def load_reference_config(reference_path: Path) -> dict[str, Any]:
    return json.loads(reference_path.read_text(encoding="utf-8"))


def reference_metrics_path_from_manifest(manifest: dict[str, Any], manifest_path: Path | None) -> Path | None:
    analysis = manifest.get("analysis", {})
    for key in ("reference_metrics_json", "reference_metrics_path"):
        candidate = resolve_path_hint(analysis.get(key), manifest_path=manifest_path)
        if candidate is not None:
            return candidate
    return None


def reference_config_path_from_manifest(manifest: dict[str, Any], manifest_path: Path | None) -> Path | None:
    analysis = manifest.get("analysis", {})
    for key in ("reference_config_json", "reference_config_path"):
        candidate = resolve_path_hint(analysis.get(key), manifest_path=manifest_path)
        if candidate is not None:
            return candidate
    return None


def build_waveform_config(
    manifest: dict[str, Any],
    args: argparse.Namespace,
    manifest_path: Path | None,
) -> tuple[WaveformConfig, Path | None, Path | None]:
    reference_metrics_json = args.reference_metrics_json
    if reference_metrics_json is None:
        reference_metrics_json = reference_metrics_path_from_manifest(manifest, manifest_path)

    reference_config_json = args.reference_config_json
    if reference_config_json is None:
        reference_config_json = reference_config_path_from_manifest(manifest, manifest_path)
    if reference_metrics_json is None and reference_config_json is None and DEFAULT_REFERENCE_METRICS_JSON.exists():
        reference_metrics_json = DEFAULT_REFERENCE_METRICS_JSON

    cfg_data: dict[str, Any] = {}
    if reference_metrics_json is not None and reference_metrics_json.exists():
        metrics = load_reference_metrics(reference_metrics_json)
        cfg_data = dict(metrics.get("waveform_config", {}))

    if reference_config_json is not None and reference_config_json.exists():
        raw_reference_cfg = load_reference_config(reference_config_json)
        allowed_keys = set(WaveformConfig.__dataclass_fields__.keys())
        aliases = {
            "attenuation_db": "tx_attenuation_db",
        }
        filtered_reference_cfg: dict[str, Any] = {}
        for key, value in raw_reference_cfg.items():
            normalized_key = aliases.get(key, key)
            if normalized_key in allowed_keys:
                filtered_reference_cfg[normalized_key] = value
        cfg_data.update(filtered_reference_cfg)

    analysis = manifest.get("analysis", {})
    signal = manifest.get("signal", {})
    hardware = manifest.get("hardware", {})
    reference_sample_rate_hz = analysis.get("reference_sample_rate_hz")
    if reference_sample_rate_hz is None:
        reference_sample_rate_hz = signal.get("reference_sample_rate_hz")
    if reference_sample_rate_hz is None:
        symbol_rate_hz_hint = signal.get("symbol_rate_hz")
        sps_hint = signal.get("samples_per_symbol")
        if symbol_rate_hz_hint is not None and sps_hint is not None:
            reference_sample_rate_hz = int(symbol_rate_hz_hint) * int(sps_hint)

    cfg_data.update(
        {
            "center_frequency_hz": int(
                signal.get(
                    "reference_center_frequency_hz",
                    manifest.get("center_frequency_hz", cfg_data.get("center_frequency_hz", DEFAULT_CENTER_FREQUENCY_HZ)),
                )
            ),
            "sample_rate_hz": int(reference_sample_rate_hz or cfg_data.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ)),
            "symbol_rate_hz": int(signal.get("symbol_rate_hz", cfg_data.get("symbol_rate_hz", DEFAULT_SYMBOL_RATE_HZ))),
            "samples_per_symbol": int(
                signal.get("samples_per_symbol", cfg_data.get("samples_per_symbol", DEFAULT_SAMPLES_PER_SYMBOL))
            ),
            "rf_bandwidth_hz": int(
                signal.get("bandwidth_hz", cfg_data.get("rf_bandwidth_hz", DEFAULT_RF_BANDWIDTH_HZ))
            ),
            "payload_bit_count": int(
                signal.get("payload_bit_count", cfg_data.get("payload_bit_count", DEFAULT_PAYLOAD_BIT_COUNT))
            ),
            "rolloff": float(signal.get("rolloff", cfg_data.get("rolloff", DEFAULT_ROLLOFF))),
            "rrc_span_symbols": int(
                signal.get("rrc_span_symbols", cfg_data.get("rrc_span_symbols", DEFAULT_RRC_SPAN_SYMBOLS))
            ),
            "tx_amplitude": float(cfg_data.get("tx_amplitude", DEFAULT_TX_AMPLITUDE)),
            "leading_silence_samples": int(cfg_data.get("leading_silence_samples", 4096)),
            "trailing_silence_samples": int(cfg_data.get("trailing_silence_samples", 4096)),
            "capture_sample_count": int(cfg_data.get("capture_sample_count", 131072)),
            "tx_attenuation_db": float(cfg_data.get("tx_attenuation_db", -50.0)),
            "rx_gain_db": float(cfg_data.get("rx_gain_db", 35.0)),
            "settle_ms": int(cfg_data.get("settle_ms", 150)),
            "rx_rf_port_select": str(cfg_data.get("rx_rf_port_select", hardware.get("rx_rf_port_select", "A_BALANCED"))),
            "tx_rf_port_select": str(cfg_data.get("tx_rf_port_select", hardware.get("tx_rf_port_select", "A"))),
            "synthetic_test": bool(cfg_data.get("synthetic_test", False)),
            "synthetic_cfo_hz": float(cfg_data.get("synthetic_cfo_hz", 120.0)),
            "synthetic_phase_offset_rad": float(cfg_data.get("synthetic_phase_offset_rad", 0.18)),
            "synthetic_timing_offset_samples": int(cfg_data.get("synthetic_timing_offset_samples", 5)),
            "synthetic_noise_rms": float(cfg_data.get("synthetic_noise_rms", 0.010)),
            "seed": int(cfg_data.get("seed", 20260623)),
        }
    )

    sample_rate_hz = cfg_data["sample_rate_hz"]
    expected_rate_hz = cfg_data["symbol_rate_hz"] * cfg_data["samples_per_symbol"]
    if sample_rate_hz != expected_rate_hz:
        raise ValueError(
            f"Reference waveform config is inconsistent: sample_rate_hz={sample_rate_hz}, "
            f"symbol_rate_hz*samples_per_symbol={expected_rate_hz}."
        )
    return (
        WaveformConfig(**cfg_data),
        (reference_metrics_json.resolve() if reference_metrics_json is not None else None),
        (reference_config_json.resolve() if reference_config_json is not None else None),
    )


def get_expected_signal_offset_hz(manifest: dict[str, Any], args: argparse.Namespace) -> float:
    if args.expected_signal_offset_hz is not None:
        return float(args.expected_signal_offset_hz)
    signal = manifest.get("signal", {})
    if "expected_signal_offset_hz" in signal:
        return float(signal["expected_signal_offset_hz"])
    if "expected_signal_offset_hz" in manifest:
        return float(manifest["expected_signal_offset_hz"])
    return 0.0


def read_wav_iq(
    path: Path,
    manifest: dict[str, Any],
    *,
    skip_samples: int,
    max_samples: int | None,
) -> tuple[np.ndarray, WavIqInfo]:
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        sample_width = w.getsampwidth()
        sample_rate_hz = float(w.getframerate())
        frame_count = w.getnframes()
        start_frame = min(max(skip_samples, 0), frame_count)
        frames_to_read = frame_count - start_frame
        if max_samples is not None and max_samples > 0:
            frames_to_read = min(frames_to_read, max_samples)
        w.setpos(start_frame)
        raw_frames = w.readframes(frames_to_read)

    if channels != 2:
        raise ValueError(f"WAV IQ reader expects stereo data, got {channels} channels in {path}")

    if sample_width == 1:
        raw = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float32)
        raw = (raw - 127.5) / 127.5
    elif sample_width == 2:
        raw = np.frombuffer(raw_frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        raw = np.frombuffer(raw_frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV IQ sample width: {sample_width} bytes")

    if len(raw) % channels != 0:
        raise ValueError(f"Unexpected interleaved sample count in {path}: {len(raw)}")

    matrix = raw.reshape(-1, channels)
    i_first = bool(manifest.get("i_first", True))
    i_data = matrix[:, 0]
    q_data = matrix[:, 1]
    x = (i_data + 1j * q_data) if i_first else (q_data + 1j * i_data)

    info = WavIqInfo(
        channels=channels,
        sample_width_bytes=sample_width,
        sample_rate_hz=sample_rate_hz,
        frame_count=frame_count,
        frames_read=int(matrix.shape[0]),
        start_frame=start_frame,
        duration_s=float(matrix.shape[0] / sample_rate_hz),
    )
    return x.astype(np.complex64), info


def sanitize_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value)


def output_prefix(dataset_id: str, run_tag: str | None) -> str:
    if run_tag:
        return f"lab1120_{sanitize_token(dataset_id)}_{sanitize_token(run_tag)}"
    return f"lab1120_{sanitize_token(dataset_id)}"


def resample_complex_linear(x: np.ndarray, src_rate_hz: float, dst_rate_hz: float) -> np.ndarray:
    if len(x) == 0:
        return x.astype(np.complex64)
    if abs(src_rate_hz - dst_rate_hz) <= 1e-9:
        return x.astype(np.complex64, copy=False)

    dst_count = max(int(round(len(x) * dst_rate_hz / src_rate_hz)), 1)
    src_time = np.arange(len(x), dtype=np.float64) / src_rate_hz
    dst_time = np.arange(dst_count, dtype=np.float64) / dst_rate_hz
    y_real = np.interp(dst_time, src_time, np.real(x))
    y_imag = np.interp(dst_time, src_time, np.imag(x))
    return (y_real + 1j * y_imag).astype(np.complex64)


def mix_frequency(x: np.ndarray, sample_rate_hz: float, frequency_hz: float) -> np.ndarray:
    if abs(frequency_hz) <= 1e-12:
        return x.astype(np.complex64, copy=False)
    n = np.arange(len(x), dtype=np.float64)
    rot = np.exp(-1j * 2.0 * np.pi * frequency_hz * n / sample_rate_hz)
    return (x * rot).astype(np.complex64)


def deduplicate_candidates(values: list[float], *, tol_hz: float) -> list[float]:
    unique: list[float] = []
    for value in values:
        if not any(abs(value - existing) <= tol_hz for existing in unique):
            unique.append(float(value))
    return unique


def estimate_coarse_frequency_candidates(
    x: np.ndarray,
    sample_rate_hz: float,
    *,
    expected_signal_offset_hz: float,
    occupied_bandwidth_hz: float,
    candidate_count: int,
    coarse_search_span_hz: float | None,
) -> list[float]:
    n = min(len(x), 262_144)
    if n < 4096:
        return [expected_signal_offset_hz, 0.0]

    preview = x[:n].astype(np.complex128)
    preview -= np.mean(preview)
    window = np.hanning(n)
    spectrum = np.fft.fftshift(np.fft.fft(preview * window, n=n))
    power = np.abs(spectrum) ** 2
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate_hz))
    bin_width_hz = sample_rate_hz / n
    smooth_bins = max(int(round(occupied_bandwidth_hz / max(bin_width_hz, 1e-9))), 8)
    kernel = np.ones(smooth_bins, dtype=np.float64) / smooth_bins
    smooth_power = np.convolve(power, kernel, mode="same")

    if coarse_search_span_hz is not None and coarse_search_span_hz > 0.0:
        half_span_hz = coarse_search_span_hz / 2.0
        mask = np.abs(freq - expected_signal_offset_hz) <= half_span_hz
    else:
        mask = np.ones_like(freq, dtype=bool)

    ranked = np.argsort(smooth_power[mask])[::-1]
    masked_freq = freq[mask]
    selected: list[float] = [expected_signal_offset_hz, 0.0]
    selected_idx: list[int] = []
    for rank in ranked.tolist():
        idx = int(rank)
        if any(abs(idx - previous) < smooth_bins for previous in selected_idx):
            continue
        selected_idx.append(idx)
        selected.append(float(masked_freq[idx]))
        if len(selected_idx) >= max(candidate_count, 1):
            break
    return deduplicate_candidates(selected, tol_hz=max(bin_width_hz * 2.0, 1.0))


def build_fine_frequency_grid(search_hz: float, step_hz: float) -> list[float]:
    if search_hz <= 0.0 or step_hz <= 0.0:
        return [0.0]
    edge = int(round(search_hz / step_hz))
    values = [float(index * step_hz) for index in range(-edge, edge + 1)]
    return deduplicate_candidates([0.0] + values, tol_hz=1e-9)


def crop_active_window(x: np.ndarray, window_samples: int) -> tuple[np.ndarray, int]:
    if window_samples <= 0 or len(x) <= window_samples:
        return x, 0
    kernel_len = max(window_samples // 32, 1)
    kernel = np.ones(kernel_len, dtype=np.float64) / kernel_len
    envelope = np.convolve(np.abs(x) ** 2, kernel, mode="same")
    peak_idx = int(np.argmax(envelope))
    start = min(max(peak_idx - window_samples // 2, 0), len(x) - window_samples)
    stop = start + window_samples
    return x[start:stop], start


def detect_frame_from_matched_filter(
    *,
    matched: np.ndarray,
    preamble_bits: np.ndarray,
    tx_bits: np.ndarray,
    tx_symbols: np.ndarray,
    sps: int,
    candidate_count: int,
    fine_frequency_offsets_hz: list[float],
    sample_rate_hz: float,
) -> dict[str, Any]:
    preamble_symbols = bits_to_bpsk(preamble_bits).astype(np.complex128)
    sampled_by_phase = [matched[phase::sps] for phase in range(sps)]
    best: dict[str, Any] | None = None

    for fine_frequency_hz in fine_frequency_offsets_hz:
        phase_step_rad = 2.0 * np.pi * fine_frequency_hz * sps / sample_rate_hz
        for phase, sampled in enumerate(sampled_by_phase):
            if len(sampled) < len(tx_symbols):
                continue
            if abs(fine_frequency_hz) > 1e-12:
                rot = np.exp(-1j * phase_step_rad * np.arange(len(sampled), dtype=np.float64))
                sampled_used = sampled * rot
            else:
                sampled_used = sampled

            corr = np.correlate(sampled_used, preamble_symbols, mode="valid")
            if corr.size == 0:
                continue
            ranked = np.argsort(np.abs(corr))[-max(candidate_count, 1) :]
            for symbol_index in ranked.tolist():
                frame = sampled_used[symbol_index : symbol_index + len(tx_symbols)]
                if len(frame) < len(tx_symbols):
                    continue
                aligned = scalar_align(tx_symbols, frame)
                rx_bits = np.where(np.real(aligned) >= 0.0, 0, 1).astype(np.uint8)
                total_errors = int(np.sum(rx_bits != tx_bits))
                payload_errors = int(np.sum(rx_bits[len(preamble_bits) :] != tx_bits[len(preamble_bits) :]))
                candidate = {
                    "fine_frequency_offset_hz": float(fine_frequency_hz),
                    "matched_filter_start_sample": int(phase + symbol_index * sps),
                    "sample_phase": int(phase),
                    "symbol_index": int(symbol_index),
                    "correlation_abs": float(abs(corr[symbol_index])),
                    "rx_bits": rx_bits,
                    "rx_symbols": aligned,
                    "matched": matched,
                    "bit_errors_total": total_errors,
                    "bit_errors_payload": payload_errors,
                    "ber_total": float(total_errors / max(len(tx_bits), 1)),
                    "ber_payload": float(payload_errors / max(len(tx_bits) - len(preamble_bits), 1)),
                    "evm_percent": float(evm_percent(tx_symbols, aligned)),
                }
                if best is None:
                    best = candidate
                    continue
                if candidate["bit_errors_total"] < best["bit_errors_total"]:
                    best = candidate
                    continue
                if (
                    candidate["bit_errors_total"] == best["bit_errors_total"]
                    and candidate["correlation_abs"] > best["correlation_abs"]
                ):
                    best = candidate

    if best is None:
        raise RuntimeError("Unable to find a full BPSK frame in the WAV capture.")
    return best


def analyze_capture(
    x: np.ndarray,
    capture_sample_rate_hz: float,
    cfg: WaveformConfig,
    *,
    expected_signal_offset_hz: float,
    coarse_candidate_count: int,
    candidate_count: int,
    coarse_search_span_hz: float | None,
    fine_search_hz: float,
    fine_step_hz: float,
    analysis_window_samples: int,
) -> tuple[np.ndarray, int, dict[str, Any], list[float]]:
    burst = generate_bpsk_burst(cfg)
    occupied_bandwidth_hz = cfg.symbol_rate_hz * (1.0 + cfg.rolloff)
    coarse_candidates = estimate_coarse_frequency_candidates(
        x,
        capture_sample_rate_hz,
        expected_signal_offset_hz=expected_signal_offset_hz,
        occupied_bandwidth_hz=occupied_bandwidth_hz,
        candidate_count=coarse_candidate_count,
        coarse_search_span_hz=coarse_search_span_hz,
    )
    fine_offsets_hz = build_fine_frequency_grid(fine_search_hz, fine_step_hz)

    best_result: dict[str, Any] | None = None
    best_analysis_window: np.ndarray | None = None
    best_window_start = 0

    for coarse_frequency_hz in coarse_candidates:
        shifted = mix_frequency(x, capture_sample_rate_hz, coarse_frequency_hz)
        analysis_capture = resample_complex_linear(shifted, capture_sample_rate_hz, cfg.sample_rate_hz)
        analysis_capture, analysis_start = crop_active_window(analysis_capture, analysis_window_samples)
        matched = np.convolve(analysis_capture, burst["rrc_taps"], mode="full")
        try:
            detection = detect_frame_from_matched_filter(
                matched=matched,
                preamble_bits=burst["preamble_bits"],
                tx_bits=burst["tx_bits"],
                tx_symbols=burst["tx_symbols"],
                sps=cfg.samples_per_symbol,
                candidate_count=candidate_count,
                fine_frequency_offsets_hz=fine_offsets_hz,
                sample_rate_hz=cfg.sample_rate_hz,
            )
        except RuntimeError:
            continue

        detection["coarse_frequency_hz"] = float(coarse_frequency_hz)
        detection["analysis_window_start_sample"] = int(analysis_start)
        if best_result is None:
            best_result = detection
            best_analysis_window = analysis_capture
            best_window_start = analysis_start
            continue
        if detection["bit_errors_total"] < best_result["bit_errors_total"]:
            best_result = detection
            best_analysis_window = analysis_capture
            best_window_start = analysis_start
            continue
        if (
            detection["bit_errors_total"] == best_result["bit_errors_total"]
            and detection["correlation_abs"] > best_result["correlation_abs"]
        ):
            best_result = detection
            best_analysis_window = analysis_capture
            best_window_start = analysis_start

    if best_result is None or best_analysis_window is None:
        raise RuntimeError("Unable to demodulate a BPSK frame from the WAV capture.")
    return best_analysis_window, best_window_start, best_result, coarse_candidates


def save_metrics_json(metrics: RtlWavBerMetrics, output_prefix_token: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{output_prefix_token}_metrics.json"
    path.write_text(json.dumps(asdict(metrics), indent=2), encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    if args.manifest is None and args.iq_path is None:
        args.manifest = DEFAULT_MANIFEST
    if args.manifest is None and args.iq_path is None:
        raise SystemExit("Pass --manifest or --iq-path.")

    manifest_path = args.manifest.resolve() if args.manifest is not None and args.manifest.exists() else None
    manifest = load_manifest(manifest_path) if manifest_path is not None else {}
    out_dir = args.out_dir.resolve()
    iq_path = resolve_iq_path(manifest, manifest_path, args.iq_path)
    dataset_id = str(manifest.get("dataset_id", iq_path.stem or "rtl_sdr_ota_bpsk_capture"))
    output_prefix_token = output_prefix(dataset_id, args.run_tag)
    cfg, reference_metrics_json, reference_config_json = build_waveform_config(manifest, args, manifest_path)
    expected_signal_offset_hz = get_expected_signal_offset_hz(manifest, args)
    x, wav_info = read_wav_iq(
        iq_path,
        manifest,
        skip_samples=args.skip_samples,
        max_samples=args.max_samples,
    )
    x = (x - np.mean(x)).astype(np.complex64)

    analysis_capture, analysis_window_start, detection_payload, coarse_candidates = analyze_capture(
        x,
        wav_info.sample_rate_hz,
        cfg,
        expected_signal_offset_hz=expected_signal_offset_hz,
        coarse_candidate_count=args.coarse_candidate_count,
        candidate_count=args.candidate_count,
        coarse_search_span_hz=args.coarse_search_span_hz,
        fine_search_hz=args.fine_search_hz,
        fine_step_hz=args.fine_step_hz,
        analysis_window_samples=args.analysis_window_samples,
    )

    detection = DetectionResult(
        matched_filter_start_sample=detection_payload["matched_filter_start_sample"],
        sample_phase=detection_payload["sample_phase"],
        symbol_index=detection_payload["symbol_index"],
        correlation_abs=detection_payload["correlation_abs"],
        bit_errors_total=detection_payload["bit_errors_total"],
        bit_errors_payload=detection_payload["bit_errors_payload"],
        ber_total=detection_payload["ber_total"],
        ber_payload=detection_payload["ber_payload"],
        evm_percent=detection_payload["evm_percent"],
    )

    total_frequency_shift_hz = float(
        detection_payload["coarse_frequency_hz"] + detection_payload["fine_frequency_offset_hz"]
    )
    peak_level_dbfs = float(20.0 * np.log10(max(np.max(np.abs(analysis_capture)), 1e-15)))
    rms_level_dbfs = float(20.0 * np.log10(max(np.sqrt(np.mean(np.abs(analysis_capture) ** 2)), 1e-15)))
    clipping_fraction = float(
        np.mean((np.abs(np.real(analysis_capture)) > 0.999) | (np.abs(np.imag(analysis_capture)) > 0.999))
    )

    metrics = RtlWavBerMetrics(
        dataset_id=dataset_id,
        iq_path=str(iq_path),
        manifest_path=str(manifest_path) if manifest_path is not None else None,
        reference_metrics_json=str(reference_metrics_json) if reference_metrics_json is not None else None,
        reference_config_json=str(reference_config_json) if reference_config_json is not None else None,
        capture_sample_rate_hz=wav_info.sample_rate_hz,
        analysis_sample_rate_hz=float(cfg.sample_rate_hz),
        capture_center_frequency_hz=float(manifest.get("center_frequency_hz", cfg.center_frequency_hz)),
        expected_signal_offset_hz=expected_signal_offset_hz,
        coarse_frequency_candidates_hz=[float(value) for value in coarse_candidates],
        selected_coarse_frequency_hz=float(detection_payload["coarse_frequency_hz"]),
        selected_fine_frequency_hz=float(detection_payload["fine_frequency_offset_hz"]),
        total_frequency_shift_hz=total_frequency_shift_hz,
        processed_input_samples=int(wav_info.frames_read),
        processed_analysis_samples=int(len(analysis_capture)),
        analysis_window_start_sample=int(analysis_window_start),
        analysis_window_samples=int(len(analysis_capture)),
        duration_s_read=float(wav_info.duration_s),
        peak_level_dbfs=peak_level_dbfs,
        rms_level_dbfs=rms_level_dbfs,
        clipping_fraction=clipping_fraction,
        detection=asdict(detection),
    )

    metrics_path = save_metrics_json(metrics, output_prefix_token, out_dir)
    spectrum_path = out_dir / f"{output_prefix_token}_baseband_spectrum.png"
    constellation_path = out_dir / f"{output_prefix_token}_constellation.png"
    matched_filter_path = out_dir / f"{output_prefix_token}_matched_filter.png"
    save_spectrum(
        spectrum_path,
        analysis_capture,
        cfg.sample_rate_hz,
        "RTL-SDR OTA BPSK capture - baseband spectrum",
    )
    save_constellation(
        constellation_path,
        detection_payload["rx_symbols"],
        "RTL-SDR OTA BPSK capture - matched-filter constellation",
    )
    save_matched_filter_trace(
        matched_filter_path,
        detection_payload["matched"],
        detection.matched_filter_start_sample,
        cfg.samples_per_symbol,
        len(detection_payload["rx_bits"]),
        "RTL-SDR OTA BPSK capture - matched filter and symbol sampling",
    )

    print("Lab 11.20 - Read RTL-SDR WAV IQ, demodulate OTA BPSK, and measure BER")
    if manifest_path is not None:
        print(f"Manifest: {manifest_path}")
    print(f"IQ file: {iq_path}")
    print(f"Dataset ID: {dataset_id}")
    print(f"Reference metrics JSON: {reference_metrics_json if reference_metrics_json is not None else 'none'}")
    print(f"Reference config JSON: {reference_config_json if reference_config_json is not None else 'none'}")
    print(f"Capture sample rate: {wav_info.sample_rate_hz:.0f} Hz")
    print(f"Analysis sample rate: {cfg.sample_rate_hz} Hz")
    print(f"Expected signal offset: {expected_signal_offset_hz:.3f} Hz")
    print(f"Coarse frequency candidates: {', '.join(f'{value:.1f}' for value in coarse_candidates)}")
    print(f"Selected coarse shift: {metrics.selected_coarse_frequency_hz:.3f} Hz")
    print(f"Selected fine shift: {metrics.selected_fine_frequency_hz:.3f} Hz")
    print(f"Total shift: {metrics.total_frequency_shift_hz:.3f} Hz")
    print(f"Samples read: {wav_info.frames_read}")
    print(f"Analysis window start: {analysis_window_start}")
    print(f"Analysis window samples: {len(analysis_capture)}")
    print(f"BER total: {detection.ber_total:.6e}")
    print(f"BER payload: {detection.ber_payload:.6e}")
    print(f"Bit errors total: {detection.bit_errors_total}")
    print(f"Bit errors payload: {detection.bit_errors_payload}")
    print(f"EVM: {detection.evm_percent:.3f} %")
    print(f"Peak level: {peak_level_dbfs:.2f} dBFS")
    print(f"RMS level: {rms_level_dbfs:.2f} dBFS")
    print(f"Clipping fraction: {clipping_fraction:.6e}")
    print(f"Metrics JSON: {repo_relative_or_str(metrics_path)}")
    print(f"Spectrum plot: {repo_relative_or_str(spectrum_path)}")
    print(f"Constellation plot: {repo_relative_or_str(constellation_path)}")
    print(f"Matched-filter plot: {repo_relative_or_str(matched_filter_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
