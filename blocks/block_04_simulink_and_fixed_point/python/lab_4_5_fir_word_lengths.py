#!/usr/bin/env python3
"""Lab 4.5: controlled word-length sweep for a causal four-tap IQ FIR."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SEED = 945
FS_HZ = 2_400_000
SAMPLE_COUNT = 8192
LAB_TAPS = (0.125, 0.375, 0.375, 0.125)
NON_DYADIC_TAPS = (0.113, 0.387, 0.387, 0.113)


@dataclass(frozen=True)
class Widths:
    input_bits: int = 16
    coefficient_bits: int = 16
    accumulator_bits: int = 34
    output_bits: int = 16

    @property
    def accumulator_fractional_bits(self) -> int:
        return self.input_bits + self.coefficient_bits - 2


def quantize(values: np.ndarray, bits: int) -> tuple[np.ndarray, int]:
    scale = 1 << (bits - 1)
    rounded = np.floor(values * scale + 0.5).astype(np.int64)
    limited = np.clip(rounded, -scale, scale - 1)
    return limited, int(np.count_nonzero(rounded != limited))


def fir_integer(
    samples: np.ndarray, taps: np.ndarray, widths: Widths, overflow: str,
) -> tuple[np.ndarray, int, int]:
    """Input shape is (samples, 2). Count MAC overflow events and clipped outputs."""
    if overflow not in ("wrap", "saturate"):
        raise ValueError(f"Unknown accumulator policy: {overflow}")
    acc = np.zeros_like(samples, dtype=np.int64)
    limit = 1 << (widths.accumulator_bits - 1)
    overflow_events = 0
    for delay, coefficient in enumerate(taps[: len(samples)]):
        partial = acc[delay:] + samples[: len(samples) - delay] * coefficient
        overflow_events += int(np.count_nonzero((partial < -limit) | (partial >= limit)))
        if overflow == "wrap":
            acc[delay:] = (partial + limit) % (2 * limit) - limit
        else:
            acc[delay:] = np.clip(partial, -limit, limit - 1)

    shift = widths.accumulator_fractional_bits - (widths.output_bits - 1)
    if shift > 0:
        rounded = (acc + (1 << (shift - 1))) >> shift
    else:
        rounded = acc << (-shift)
    output_limit = 1 << (widths.output_bits - 1)
    result = np.clip(rounded, -output_limit, output_limit - 1)
    return result, overflow_events, int(np.count_nonzero(result != rounded))


def float_fir(samples: np.ndarray, taps: np.ndarray) -> np.ndarray:
    return np.column_stack([np.convolve(channel, taps)[: len(samples)] for channel in samples.T])


def make_signal() -> np.ndarray:
    rng = np.random.default_rng(SEED)
    time = np.arange(SAMPLE_COUNT) / FS_HZ
    signal = 0.64 * np.exp(2j * np.pi * 120_000 * time)
    signal += 0.18 * np.exp(2j * np.pi * 620_000 * time)
    signal += 0.015 * (rng.standard_normal(len(time)) + 1j * rng.standard_normal(len(time)))
    signal *= 0.80 / np.max(np.abs(signal))
    return np.column_stack((signal.real, signal.imag))


def response(taps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.fft.rfftfreq(4096), np.abs(np.fft.rfft(taps, n=4096))


def measure(
    samples: np.ndarray, taps: np.ndarray, reference: np.ndarray,
    widths: Widths, overflow: str = "wrap",
) -> dict:
    input_codes, input_clipped = quantize(samples, widths.input_bits)
    coefficient_codes, coefficients_clipped = quantize(taps, widths.coefficient_bits)
    output, events, output_clipped = fir_integer(input_codes, coefficient_codes, widths, overflow)
    actual = output / (1 << (widths.output_bits - 1))
    # Compare complex RMS after the three zero-history startup samples.
    error = actual[3:] - reference[3:]
    rms = float(np.sqrt(np.mean(np.sum(error**2, axis=1))))
    signal_rms = float(np.sqrt(np.mean(np.sum(reference[3:]**2, axis=1))))
    ratio = rms / signal_rms
    realized = coefficient_codes / (1 << (widths.coefficient_bits - 1))
    freq, gain = response(realized)
    _, ideal_gain = response(taps)
    return {
        **asdict(widths),
        "accumulator_fractional_bits": widths.accumulator_fractional_bits,
        "accumulator_overflow_policy": overflow,
        "coefficient_codes": coefficient_codes.tolist(),
        "input_clipped_components": input_clipped,
        "coefficient_clipped_values": coefficients_clipped,
        "accumulator_overflow_events": events,
        "output_clipped_components": output_clipped,
        "max_complex_error_fs": float(np.max(np.linalg.norm(error, axis=1))),
        "rms_complex_error_fs": rms,
        "normalized_rms_error_percent": 100 * ratio,
        "sqnr_db": float(-20 * np.log10(ratio)) if ratio else None,
        "dc_gain": float(gain[0]),
        "passband_max_abs_gain_error": float(np.max(np.abs(gain[freq <= 0.10] - ideal_gain[freq <= 0.10]))),
        "stopband_peak_gain_db": float(20 * np.log10(np.max(gain[freq >= 0.35]))),
    }


def experiment(combined_widths: Widths | None = None) -> dict:
    widths = Widths()
    samples = make_signal()
    taps = np.array(LAB_TAPS)
    reference = float_fir(samples, taps)
    sweeps = {}
    for field, values in (
        ("input_bits", (6, 8, 10, 12, 14, 16)),
        ("coefficient_bits", (2, 3, 4, 5, 6, 8, 10, 12, 14, 16)),
        ("accumulator_bits", (28, 29, 30, 31, 32, 33, 34)),
        ("output_bits", (6, 8, 10, 12, 14, 16)),
    ):
        sweeps[field] = [measure(samples, taps, reference, replace(widths, **{field: bits})) for bits in values]

    other_taps = np.array(NON_DYADIC_TAPS)
    other_reference = float_fir(samples, other_taps)
    non_dyadic = [
        measure(samples, other_taps, other_reference, replace(widths, coefficient_bits=row["coefficient_bits"]))
        for row in sweeps["coefficient_bits"]
    ]
    stress = np.tile([-1.0, 32767 / 32768], (64, 1))
    stress_taps = -np.ones(4)
    stress_reference = float_fir(stress, stress_taps)
    stress_rows = [
        measure(stress, stress_taps, stress_reference, replace(widths, accumulator_bits=bits), policy)
        for bits in (31, 32, 33, 34) for policy in ("wrap", "saturate")
    ]
    result = {
        "evidence": "synthetic fixed-point model",
        "seed": SEED,
        "sample_rate_hz": FS_HZ,
        "nominal_iq_samples": SAMPLE_COUNT,
        "nominal_tones_hz": [120_000, 620_000],
        "nominal_peak_complex_amplitude_fs": 0.80,
        "warmup_excluded_from_error_samples": 3,
        "rounding": "nearest, ties toward positive infinity",
        "baseline_widths": asdict(widths),
        "nominal_taps": list(LAB_TAPS),
        "nominal_baseline": measure(samples, taps, reference, widths),
        "nominal_sweeps": sweeps,
        "non_dyadic_taps": list(NON_DYADIC_TAPS),
        "non_dyadic_coefficient_sweep": non_dyadic,
        "stress_iq_samples": len(stress),
        "stress_input_pair": stress[0].tolist(),
        "stress_taps": stress_taps.tolist(),
        "stress_accumulator_sweep": stress_rows,
        "response_fft_points": 4096,
        "passband_upper_cycles_per_sample": 0.10,
        "stopband_lower_cycles_per_sample": 0.35,
    }
    if combined_widths is not None:
        result["combined_nominal"] = measure(samples, taps, reference, combined_widths)
    return result


def plot_sweeps(metrics: dict, path: Path, *, russian: bool = False) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(9, 6.5), layout="constrained")
    sweeps = metrics["nominal_sweeps"]
    input_label, output_label = ("Разрядность входа", "Разрядность выхода") if russian else ("Input width", "Output width")
    sqnr_label = "SQNR на выходе, дБ" if russian else "Output SQNR (dB)"
    for field, title, marker in (("input_bits", input_label, "o"), ("output_bits", output_label, "s")):
        rows = sweeps[field]
        axes[0, 0].plot([r[field] for r in rows], [r["sqnr_db"] for r in rows],
                        marker=marker, label=title)
    axes[0, 0].set(xlabel="Разрядность, бит" if russian else "Signed width (bits)", ylabel=sqnr_label)
    axes[0, 0].legend()

    lab_label, alternate_label = (("Коэффициенты из лаб. 5.13", "Неточные в двоичной системе")
                                  if russian else ("Lab 5.13 taps", "Non-dyadic taps"))
    for rows, label in ((sweeps["coefficient_bits"], lab_label),
                        (metrics["non_dyadic_coefficient_sweep"], alternate_label)):
        axes[0, 1].plot([r["coefficient_bits"] for r in rows], [r["sqnr_db"] for r in rows],
                        marker="o" if rows is sweeps["coefficient_bits"] else "s", label=label)
    axes[0, 1].set(xlabel="Разрядность коэффициентов, бит" if russian else "Coefficient width (bits)",
                   ylabel=sqnr_label)
    axes[0, 1].legend()

    rows = sweeps["accumulator_bits"]
    axes[1, 0].plot([r["accumulator_bits"] for r in rows],
                    [r["accumulator_overflow_events"] for r in rows], "o-")
    axes[1, 0].set(xlabel="Разрядность аккумулятора, бит" if russian else "Accumulator width (bits)",
                   ylabel="Переполнения при накоплении" if russian else "MAC overflow events",
                   title="Штатный IQ, с циклическим переносом" if russian else "Nominal IQ, wrap policy")

    for width, style in ((3, "--"), (6, ":"), (16, "-")):
        codes, _ = quantize(np.array(NON_DYADIC_TAPS), width)
        frequency, gain = response(codes / (1 << (width - 1)))
        axes[1, 1].plot(frequency, 20 * np.log10(np.maximum(gain, 1e-5)),
                        style, label=f"{width} бит" if russian else f"{width} bits")
    axes[1, 1].set(xlabel="Частота, цикл/отсчёт" if russian else "Frequency (cycles/sample)",
                   ylabel="Амплитудная характеристика, дБ" if russian else "Tap response (dB)",
                   title=alternate_label, ylim=(-70, 6))
    axes[1, 1].legend()
    for axis in axes.flat:
        axis.grid(alpha=0.25)
    figure.savefig(path, dpi=165)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/assets",
                        help="Directory for experiment metrics and plot")
    parser.add_argument("--widths", type=int, nargs=4, metavar=("INPUT", "COEFF", "ACC", "OUTPUT"),
                        help="Also measure a combined width choice on the nominal filter")
    args = parser.parse_args()
    combined_widths = None
    if args.widths:
        input_bits, coefficient_bits, accumulator_bits, output_bits = args.widths
        if not all(2 <= width <= 16 for width in (input_bits, coefficient_bits, output_bits)):
            parser.error("input, coefficient and output widths must be in 2..16 bits")
        if not 2 <= accumulator_bits <= 34:
            parser.error("accumulator width must be in 2..34 bits")
        combined_widths = Widths(*args.widths)
    metrics = experiment(combined_widths)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "lab45_fir_word_lengths.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n",
    )
    plot_sweeps(metrics, args.output / "lab45_fir_word_lengths.png")
    plot_sweeps(metrics, args.output / "lab45_fir_word_lengths_ru.png", russian=True)
    print(f"Q1.15 baseline SQNR: {metrics['nominal_baseline']['sqnr_db']:.2f} dB")
    if combined_widths is not None:
        row = metrics["combined_nominal"]
        print(f"Combined SQNR: {row['sqnr_db']:.2f} dB; "
              f"MAC overflow events: {row['accumulator_overflow_events']}")
    print(f"Metrics and plot: {args.output}")


if __name__ == "__main__":
    main()
