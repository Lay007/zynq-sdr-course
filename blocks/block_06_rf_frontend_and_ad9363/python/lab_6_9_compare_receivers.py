#!/usr/bin/env python3
"""Lab 6.9 - Compare RTL-SDR and AD936x receive-path quality."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_METRICS_OUT = DEFAULT_ASSET_DIR / "lab69_receiver_comparison_metrics.json"
DEFAULT_SINAD_PLOT_OUT = DEFAULT_ASSET_DIR / "lab69_receiver_comparison_sinad.png"
DEFAULT_NOISE_PLOT_OUT = DEFAULT_ASSET_DIR / "lab69_receiver_comparison_noise_density.png"


def parse_bits_list(value: str) -> list[int]:
    bits = sorted({int(item.strip()) for item in value.split(",") if item.strip()})
    if not bits or any(bit < 2 or bit > 16 for bit in bits):
        raise argparse.ArgumentTypeError("bit-depth list must contain integers from 2 to 16")
    return bits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare RTL-SDR and AD936x IQ captures using tone level, SNR, "
            "SINAD, SFDR, noise density, clipping and an AD936x quantization sweep."
        )
    )
    parser.add_argument("--rtl-iq", type=Path, help="RTL-SDR IQ capture. Omit both input files for synthetic mode.")
    parser.add_argument("--ad936x-iq", type=Path, help="AD936x IQ capture. Omit both input files for synthetic mode.")
    parser.add_argument("--rtl-format", choices=("cu8", "ci8", "ci16", "cf32"), default="cu8")
    parser.add_argument("--ad936x-format", choices=("cu8", "ci8", "ci16", "cf32"), default="ci16")
    parser.add_argument("--rtl-stored-bits", type=int, default=8)
    parser.add_argument("--ad936x-stored-bits", type=int, default=12)
    parser.add_argument("--rtl-sample-rate-hz", type=float, default=2_400_000.0)
    parser.add_argument("--ad936x-sample-rate-hz", type=float, default=2_400_000.0)
    parser.add_argument("--tone-offset-hz", type=float, default=120_000.0)
    parser.add_argument("--tone-search-span-hz", type=float, default=20_000.0)
    parser.add_argument("--analysis-bandwidth-hz", type=float, default=1_800_000.0)
    parser.add_argument("--quantize-bits", type=parse_bits_list, default=parse_bits_list("6,8,10,12"))
    parser.add_argument("--max-samples", type=int, default=262_144)
    parser.add_argument("--synthetic-samples", type=int, default=65_536)
    parser.add_argument("--synthetic-seed", type=int, default=6901)
    parser.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS_OUT)
    parser.add_argument("--sinad-plot-out", type=Path, default=DEFAULT_SINAD_PLOT_OUT)
    parser.add_argument("--noise-plot-out", type=Path, default=DEFAULT_NOISE_PLOT_OUT)
    return parser.parse_args()


def _paired(values: np.ndarray, *, path: Path) -> np.ndarray:
    if values.size % 2:
        raise ValueError(f"{path}: IQ file contains an odd number of scalar values")
    return values.reshape(-1, 2)


def read_iq(path: Path, iq_format: str, *, stored_bits: int) -> np.ndarray:
    """Read interleaved I/Q and normalize component full scale to approximately +/-1."""

    if stored_bits < 2 or stored_bits > 16:
        raise ValueError("stored_bits must be from 2 to 16")

    if iq_format == "cu8":
        pairs = _paired(np.fromfile(path, dtype=np.uint8), path=path).astype(np.float64)
        return ((pairs[:, 0] - 127.5) + 1j * (pairs[:, 1] - 127.5)) / 127.5
    if iq_format == "ci8":
        pairs = _paired(np.fromfile(path, dtype=np.int8), path=path).astype(np.float64)
        scale = float(2 ** (stored_bits - 1))
        return (pairs[:, 0] + 1j * pairs[:, 1]) / scale
    if iq_format == "ci16":
        pairs = _paired(np.fromfile(path, dtype="<i2"), path=path).astype(np.float64)
        scale = float(2 ** (stored_bits - 1))
        return (pairs[:, 0] + 1j * pairs[:, 1]) / scale
    if iq_format == "cf32":
        pairs = _paired(np.fromfile(path, dtype="<f4"), path=path).astype(np.float64)
        return pairs[:, 0] + 1j * pairs[:, 1]
    raise ValueError(f"Unsupported IQ format: {iq_format}")


def quantize_iq(iq: np.ndarray, bits: int) -> np.ndarray:
    """Round complex normalized IQ to a signed fixed-point grid."""

    if bits < 2 or bits > 16:
        raise ValueError("bits must be from 2 to 16")
    scale = float(2 ** (bits - 1))
    lower = -scale
    upper = scale - 1.0

    def quantize_component(values: np.ndarray) -> np.ndarray:
        codes = np.clip(np.rint(values * scale), lower, upper)
        return codes / scale

    return quantize_component(iq.real) + 1j * quantize_component(iq.imag)


def _db10(value: float) -> float:
    return 10.0 * math.log10(max(value, np.finfo(float).tiny))


def _db20(value: float) -> float:
    return 20.0 * math.log10(max(value, np.finfo(float).tiny))


def analyze_tone(
    iq: np.ndarray,
    sample_rate_hz: float,
    expected_tone_hz: float,
    *,
    analysis_bandwidth_hz: float,
    tone_search_span_hz: float,
    nominal_bits: int,
) -> dict[str, float | int]:
    """Estimate comparable tone and dynamic-range metrics from one complex capture."""

    if iq.size < 1024:
        raise ValueError("at least 1024 complex samples are required")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if not 0 < analysis_bandwidth_hz <= sample_rate_hz:
        raise ValueError("analysis_bandwidth_hz must be in (0, sample_rate_hz]")
    if not 0 < tone_search_span_hz < sample_rate_hz / 2:
        raise ValueError("tone_search_span_hz must be in (0, sample_rate_hz/2)")

    samples = np.asarray(iq, dtype=np.complex128)
    dc = np.mean(samples)
    centered = samples - dc
    sample_count = centered.size
    window = np.hanning(sample_count)
    window_power = float(np.sum(window**2))
    spectrum = np.fft.fftshift(np.fft.fft(centered * window))
    frequencies = np.fft.fftshift(np.fft.fftfreq(sample_count, d=1.0 / sample_rate_hz))
    psd = np.abs(spectrum) ** 2 / (sample_rate_hz * window_power)
    bin_width_hz = sample_rate_hz / sample_count

    search_mask = np.abs(frequencies - expected_tone_hz) <= tone_search_span_hz
    if not np.any(search_mask):
        raise ValueError("tone search window does not overlap the FFT frequency grid")
    search_indices = np.flatnonzero(search_mask)
    tone_index = int(search_indices[np.argmax(psd[search_mask])])
    detected_tone_hz = float(frequencies[tone_index])

    tone_half_width_bins = 2
    tone_mask = np.zeros(sample_count, dtype=bool)
    tone_mask[max(0, tone_index - tone_half_width_bins) : min(sample_count, tone_index + tone_half_width_bins + 1)] = True

    analysis_mask = np.abs(frequencies) <= analysis_bandwidth_hz / 2.0
    dc_index = int(np.argmin(np.abs(frequencies)))
    dc_mask = np.zeros(sample_count, dtype=bool)
    dc_mask[max(0, dc_index - 2) : min(sample_count, dc_index + 3)] = True

    signal_mask = tone_mask & analysis_mask
    residual_mask = analysis_mask & ~signal_mask & ~dc_mask
    if not np.any(signal_mask) or np.count_nonzero(residual_mask) < 32:
        raise ValueError("analysis bandwidth is too narrow for reliable metrics")

    signal_power = float(np.sum(psd[signal_mask]) * bin_width_hz)
    residual_power = float(np.sum(psd[residual_mask]) * bin_width_hz)
    median_psd = float(np.median(psd[residual_mask]))
    noise_density = median_psd / math.log(2.0)
    noise_power = min(residual_power, noise_density * np.count_nonzero(residual_mask) * bin_width_hz)
    distortion_power = max(residual_power - noise_power, 0.0)

    signal_peak_psd = float(np.max(psd[signal_mask]))
    largest_spur_psd = float(np.max(psd[residual_mask]))

    time_index = np.arange(sample_count, dtype=np.float64)
    reference = np.exp(-1j * 2.0 * np.pi * detected_tone_hz * time_index / sample_rate_hz)
    coherent_amplitude = abs(np.sum(centered * window * reference) / np.sum(window))
    component_limit = 1.0 - 1.0 / float(2 ** (nominal_bits - 1))
    clipping_fraction = float(
        np.mean((np.abs(samples.real) >= component_limit) | (np.abs(samples.imag) >= component_limit))
    )

    sinad_db = _db10(signal_power / max(residual_power, np.finfo(float).tiny))
    return {
        "sample_count": int(sample_count),
        "sample_rate_hz": float(sample_rate_hz),
        "analysis_bandwidth_hz": float(analysis_bandwidth_hz),
        "expected_tone_hz": float(expected_tone_hz),
        "detected_tone_hz": detected_tone_hz,
        "frequency_error_hz": detected_tone_hz - expected_tone_hz,
        "tone_level_dbfs": _db20(coherent_amplitude),
        "rms_level_dbfs": _db10(float(np.mean(np.abs(samples) ** 2))),
        "peak_level_dbfs": _db20(float(np.max(np.abs(samples)))),
        "dc_level_dbfs": _db20(abs(dc)),
        "snr_db": _db10(signal_power / max(noise_power, np.finfo(float).tiny)),
        "sinad_db": sinad_db,
        "sfdr_db": _db10(signal_peak_psd / max(largest_spur_psd, np.finfo(float).tiny)),
        "noise_density_dbfs_hz": _db10(noise_density),
        "distortion_power_dbfs": _db10(distortion_power),
        "enob_system_bits": (sinad_db - 1.76) / 6.02,
        "clipping_fraction": clipping_fraction,
    }


def synthetic_captures(sample_count: int, sample_rate_hz: float, tone_hz: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Create deterministic receiver-like captures for CI and teaching."""

    rng = np.random.default_rng(seed)
    time_index = np.arange(sample_count, dtype=np.float64)
    tone_amplitude = 10.0 ** (-18.0 / 20.0)
    tone = tone_amplitude * np.exp(1j * 2.0 * np.pi * tone_hz * time_index / sample_rate_hz)

    rtl_spur = tone_amplitude * 10.0 ** (-43.0 / 20.0) * np.exp(
        1j * 2.0 * np.pi * (-310_000.0) * time_index / sample_rate_hz
    )
    ad936x_spur = tone_amplitude * 10.0 ** (-68.0 / 20.0) * np.exp(
        1j * 2.0 * np.pi * (-310_000.0) * time_index / sample_rate_hz
    )

    rtl_noise = 7.5e-4 * (rng.standard_normal(sample_count) + 1j * rng.standard_normal(sample_count))
    ad936x_noise = 1.5e-4 * (rng.standard_normal(sample_count) + 1j * rng.standard_normal(sample_count))

    rtl_analog = tone + rtl_spur + rtl_noise + (2.5e-3 + 1j * -1.5e-3)
    ad936x_analog = tone + ad936x_spur + ad936x_noise + (3.5e-4 + 1j * 2.5e-4)
    return quantize_iq(rtl_analog, 8), quantize_iq(ad936x_analog, 12)


def build_payload(
    *,
    mode: str,
    rtl_metrics: dict[str, float | int],
    ad936x_native_metrics: dict[str, float | int],
    quantization_metrics: list[dict[str, Any]],
    source: dict[str, Any],
) -> dict[str, Any]:
    by_bits = {int(item["bits"]): item["metrics"] for item in quantization_metrics}
    comparison: dict[str, float | None] = {
        "ad936x_native_minus_rtl_sinad_db": float(ad936x_native_metrics["sinad_db"])
        - float(rtl_metrics["sinad_db"]),
        "ad936x_native_minus_rtl_sfdr_db": float(ad936x_native_metrics["sfdr_db"])
        - float(rtl_metrics["sfdr_db"]),
        "ad936x_native_minus_rtl_noise_density_db": float(ad936x_native_metrics["noise_density_dbfs_hz"])
        - float(rtl_metrics["noise_density_dbfs_hz"]),
        "ad936x_native_to_8bit_sinad_penalty_db": None,
        "ad936x_8bit_minus_rtl_8bit_sinad_db": None,
    }
    if 8 in by_bits:
        comparison["ad936x_native_to_8bit_sinad_penalty_db"] = float(ad936x_native_metrics["sinad_db"]) - float(
            by_bits[8]["sinad_db"]
        )
        comparison["ad936x_8bit_minus_rtl_8bit_sinad_db"] = float(by_bits[8]["sinad_db"]) - float(
            rtl_metrics["sinad_db"]
        )

    return {
        "lab": "6.9",
        "title": "RTL-SDR vs AD936x receiver quality and ADC resolution",
        "mode": mode,
        "source": source,
        "interpretation": {
            "native_vs_rtl": "Complete receiver-path difference under the recorded settings.",
            "ad936x_native_vs_quantized": "Quantization-only sensitivity using the same AD936x samples.",
            "ad936x_8bit_vs_rtl_8bit": (
                "Approximate same-resolution path comparison. It still includes gain, filters, clocks, "
                "sample-rate and calibration differences."
            ),
        },
        "receivers": {
            "rtl_sdr_8bit": rtl_metrics,
            "ad936x_native": ad936x_native_metrics,
        },
        "ad936x_quantization_sweep": quantization_metrics,
        "comparison": comparison,
    }


def save_metric_plot(
    payload: dict[str, Any],
    *,
    metric: str,
    ylabel: str,
    path: Path,
) -> None:
    labels = ["RTL-SDR\n8 bit", "AD936x\nnative"]
    values = [
        float(payload["receivers"]["rtl_sdr_8bit"][metric]),
        float(payload["receivers"]["ad936x_native"][metric]),
    ]
    for item in payload["ad936x_quantization_sweep"]:
        labels.append(f"AD936x\n{item['bits']} bit")
        values.append(float(item["metrics"][metric]))

    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(9.0, 4.8))
    axis.bar(labels, values)
    axis.set_ylabel(ylabel)
    axis.set_title("Lab 6.9 receiver comparison")
    axis.grid(axis="y", alpha=0.3)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def run(args: argparse.Namespace) -> dict[str, Any]:
    file_mode = args.rtl_iq is not None or args.ad936x_iq is not None
    if file_mode and (args.rtl_iq is None or args.ad936x_iq is None):
        raise ValueError("--rtl-iq and --ad936x-iq must be supplied together")
    if args.max_samples < 1024:
        raise ValueError("--max-samples must be at least 1024")

    if file_mode:
        rtl = read_iq(args.rtl_iq, args.rtl_format, stored_bits=args.rtl_stored_bits)[: args.max_samples]
        ad936x = read_iq(args.ad936x_iq, args.ad936x_format, stored_bits=args.ad936x_stored_bits)[: args.max_samples]
        mode = "files"
        source = {
            "rtl_iq": str(args.rtl_iq),
            "ad936x_iq": str(args.ad936x_iq),
            "rtl_format": args.rtl_format,
            "ad936x_format": args.ad936x_format,
            "manual_gain_required": True,
            "common_input_and_measurement_plane_required": True,
        }
    else:
        rtl, ad936x = synthetic_captures(
            args.synthetic_samples,
            args.rtl_sample_rate_hz,
            args.tone_offset_hz,
            args.synthetic_seed,
        )
        if args.ad936x_sample_rate_hz != args.rtl_sample_rate_hz:
            raise ValueError("synthetic mode requires equal RTL-SDR and AD936x sample rates")
        mode = "synthetic"
        source = {
            "seed": args.synthetic_seed,
            "purpose": "Deterministic CI baseline; not a substitute for bench measurements.",
        }

    rtl_metrics = analyze_tone(
        rtl,
        args.rtl_sample_rate_hz,
        args.tone_offset_hz,
        analysis_bandwidth_hz=args.analysis_bandwidth_hz,
        tone_search_span_hz=args.tone_search_span_hz,
        nominal_bits=args.rtl_stored_bits,
    )
    ad936x_native_metrics = analyze_tone(
        ad936x,
        args.ad936x_sample_rate_hz,
        args.tone_offset_hz,
        analysis_bandwidth_hz=args.analysis_bandwidth_hz,
        tone_search_span_hz=args.tone_search_span_hz,
        nominal_bits=args.ad936x_stored_bits,
    )

    quantization_metrics: list[dict[str, Any]] = []
    for bits in args.quantize_bits:
        quantized = quantize_iq(ad936x, bits)
        quantization_metrics.append(
            {
                "bits": bits,
                "metrics": analyze_tone(
                    quantized,
                    args.ad936x_sample_rate_hz,
                    args.tone_offset_hz,
                    analysis_bandwidth_hz=args.analysis_bandwidth_hz,
                    tone_search_span_hz=args.tone_search_span_hz,
                    nominal_bits=bits,
                ),
            }
        )

    payload = build_payload(
        mode=mode,
        rtl_metrics=rtl_metrics,
        ad936x_native_metrics=ad936x_native_metrics,
        quantization_metrics=quantization_metrics,
        source=source,
    )

    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    save_metric_plot(payload, metric="sinad_db", ylabel="SINAD, dB", path=args.sinad_plot_out)
    save_metric_plot(
        payload,
        metric="noise_density_dbfs_hz",
        ylabel="Noise density, dBFS/Hz",
        path=args.noise_plot_out,
    )
    return payload


def main() -> int:
    args = parse_args()
    payload = run(args)
    comparison = payload["comparison"]
    print(f"Mode: {payload['mode']}")
    print(f"RTL-SDR SINAD: {payload['receivers']['rtl_sdr_8bit']['sinad_db']:.2f} dB")
    print(f"AD936x native SINAD: {payload['receivers']['ad936x_native']['sinad_db']:.2f} dB")
    print(f"Native AD936x advantage: {comparison['ad936x_native_minus_rtl_sinad_db']:.2f} dB")
    if comparison["ad936x_native_to_8bit_sinad_penalty_db"] is not None:
        print(f"AD936x 12/native -> 8-bit penalty: {comparison['ad936x_native_to_8bit_sinad_penalty_db']:.2f} dB")
    print(f"Wrote {args.metrics_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
