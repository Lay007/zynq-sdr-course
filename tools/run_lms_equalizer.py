#!/usr/bin/env python3
"""Run a trained two-tap LMS model and optionally check its RTL against integer vectors."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from platform import python_version
import re
import shutil
import subprocess

import matplotlib
import numpy as np

from summarize_fir_architectures import read_routed


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "blocks/block_05_fpga_hdl_flow/rtl/lms_equalizer_2tap.sv"
BENCH = ROOT / "blocks/block_05_fpga_hdl_flow/tb/tb_lms_equalizer_2tap.sv"
SEED = 9415
COUNT = 4096
TRAIN = 1536
AMPLITUDE = 0.5
CHANNEL = (0.8, 0.62)
NOISE_STD = 0.045
MU = 1 / 16


def clip16(value: int) -> int:
    return max(-32768, min(32767, value))


def round_shift(value: int, shift: int) -> int:
    return (value + (1 << (shift - 1))) >> shift


@dataclass
class FixedLMS:
    previous: int = 0
    w0: int = 0
    w1: int = 0

    def step(self, sample: int, desired: int, *, train: bool) -> tuple[int, bool]:
        estimate = round_shift(self.w0 * sample + self.w1 * self.previous, 14)
        clipped = False
        if train:
            error = desired - estimate
            next0 = self.w0 + round_shift(error * sample, 20)
            next1 = self.w1 + round_shift(error * self.previous, 20)
            self.w0, self.w1 = clip16(next0), clip16(next1)
            clipped = (next0, next1) != (self.w0, self.w1)
        self.previous = sample
        return estimate, clipped


def q15(values: np.ndarray) -> np.ndarray:
    return np.clip(np.floor(values * 32768 + 0.5), -32768, 32767).astype(np.int64)


def score(estimate: np.ndarray, desired: np.ndarray) -> dict:
    error = estimate - desired
    mse = float(np.mean(error**2))
    bit_errors = int(np.count_nonzero((estimate >= 0) != (desired >= 0)))
    return {
        "samples": len(desired),
        "mse_fs_squared": mse,
        "normalized_rms_error_percent": 100 * float(np.sqrt(mse / np.mean(desired**2))),
        "bit_errors": bit_errors,
        "ber": bit_errors / len(desired),
    }


def experiment() -> tuple[dict, tuple[np.ndarray, ...], list[tuple[int, ...]]]:
    rng = np.random.default_rng(SEED)
    desired = AMPLITUDE * (2 * rng.integers(0, 2, COUNT) - 1)
    sample = np.convolve(desired, CHANNEL)[:COUNT] + rng.normal(0, NOISE_STD, COUNT)
    raw_codes = np.floor(sample * 32768 + 0.5)
    codes, targets = q15(sample), q15(desired)

    model = FixedLMS()
    float_weights = np.zeros(2)
    float_previous = 0.0
    float_estimates, fixed_estimates, weights = [], [], []
    vectors = [(1, 1, 1, 123, 456, 0, 0, 0, 0, 0)]
    clip_events = 0
    for n, (value, target, x_code, d_code) in enumerate(zip(sample, desired, codes, targets)):
        if n % 31 == 7:
            previous_y, previous_w0, previous_w1 = vectors[-1][6:9]
            vectors.append((0, 0, 1, -32768, 32767, 0, previous_y, previous_w0, previous_w1, 0))
        train = n < TRAIN
        # Drive an incompatible target after training to expose any accidental adaptation.
        target_code = int(d_code) if train else -int(d_code)
        estimate, clipped = model.step(int(x_code), target_code, train=train)
        clip_events += int(clipped)
        fixed_estimates.append(estimate / 32768)
        weights.append((model.w0 / 16384, model.w1 / 16384))
        vectors.append((0, 1, int(train), int(x_code), target_code,
                        1, estimate, model.w0, model.w1, int(clipped)))

        regressors = np.array([value, float_previous])
        float_previous = value
        predicted = float(np.dot(float_weights, regressors))
        float_estimates.append(predicted)
        if train:
            float_weights += MU * (target - predicted) * regressors

    stress_clips = {}
    for target in (32767, -32768):
        model = FixedLMS()
        vectors.append((1, 1, 1, -32768, target, 0, 0, 0, 0, 0))
        stress_clips[target] = 0
        for _ in range(512):
            estimate, clipped = model.step(4096, target, train=True)
            stress_clips[target] += int(clipped)
            vectors.append((0, 1, 1, 4096, target, 1, estimate, model.w0, model.w1, int(clipped)))
        rail = 32767 if target > 0 else -32768
        if stress_clips[target] == 0 or model.w0 != rail or model.w1 != rail:
            raise AssertionError("Weight-saturation stimulus did not reach both rails as expected")

    # At the negative weight rail, two negative full-scale inputs sum to +2**31.
    for _ in range(2):
        estimate, clipped = model.step(-32768, 0, train=False)
        vectors.append((0, 1, 0, -32768, 0, 1, estimate, model.w0, model.w1, int(clipped)))
    if estimate != 4 * 32768:
        raise AssertionError("Full-scale signed dot product must represent +4")

    evaluation = slice(TRAIN, None)
    f, q = np.asarray(float_estimates), np.asarray(fixed_estimates)
    fixed_weights = np.asarray(weights)
    result = {
        "evidence": "synthetic real BPSK model at one sample per symbol",
        "seed": SEED, "symbol_amplitude_fs": AMPLITUDE, "symbols": COUNT,
        "channel_taps": list(CHANNEL), "noise_std_fs": NOISE_STD,
        "training_symbols": TRAIN, "evaluation_symbols": COUNT - TRAIN, "mu": MU,
        "input_clip_samples": int(np.count_nonzero(raw_codes != codes)),
        "training_weight_clip_samples": clip_events,
        "stress_clip_flags": {"positive": stress_clips[32767], "negative": stress_clips[-32768]},
        "float_frozen_weights": float_weights.tolist(),
        "fixed_frozen_weights": fixed_weights[-1].tolist(),
        "evaluation": {
            "raw": score(sample[evaluation], desired[evaluation]),
            "float_lms": score(f[evaluation], desired[evaluation]),
            "fixed_lms": score(q[evaluation], desired[evaluation]),
        },
    }
    assert np.all(fixed_weights[TRAIN:] == fixed_weights[TRAIN - 1])
    return result, (desired, sample, f, q, fixed_weights), vectors


def run_rtl(output: Path, vectors: list[tuple[int, ...]]) -> dict:
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        raise RuntimeError("Icarus Verilog is required for --rtl")
    path = output / "lms_vectors.txt"
    path.write_text(f"{len(vectors)}\n" + "".join(" ".join(map(str, row)) + "\n" for row in vectors),
                    encoding="ascii", newline="\n")
    image = output / "lms.vvp"
    subprocess.run(["iverilog", "-g2012", "-Wall", "-s", BENCH.stem, "-o", str(image),
                    str(RTL), str(BENCH)], cwd=output, check=True, timeout=30)
    process = subprocess.run(["vvp", str(image)], cwd=output, text=True, capture_output=True, timeout=30)
    log = process.stdout + process.stderr
    (output / "lms_rtl.log").write_text(log, encoding="utf-8", newline="\n")
    expected = f"PASS LMS cycles={len(vectors)} samples={sum(r[5] for r in vectors)} saturation_flags={sum(r[9] for r in vectors)}"
    if process.returncode != 0 or not re.search(rf"^{expected}$", log, re.MULTILINE):
        raise RuntimeError(f"LMS cycle checks did not pass.\n{log}")
    version = subprocess.run(["iverilog", "-V"], text=True, capture_output=True, timeout=30)
    print(expected)
    return {"tool_version": version.stdout.partition("\n")[0].strip(),
            "cycles": len(vectors), "valid_samples": sum(r[5] for r in vectors),
            "weight_saturation_flags": sum(r[9] for r in vectors)}


def plot(data: tuple[np.ndarray, ...], path: Path, *, russian: bool) -> None:
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    desired, raw, f, q, weights = data
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 6.0), sharex=True, layout="constrained")
    frame = 64
    positions = np.arange(frame / 2, COUNT, frame)
    for signal, color, style, label in (
        (raw, "#666666", ":", "Принятый сигнал" if russian else "Received signal"),
        (f, "#226184", "-", "Плавающая точка" if russian else "Floating point"),
        (q, "#a04018", "--", "Фиксированная точка" if russian else "Fixed point"),
    ):
        mse = np.mean(((signal - desired)**2).reshape(-1, frame), axis=1)
        axes[0].plot(positions, 10 * np.log10(mse), style, linewidth=1.6, color=color, label=label)
    axes[1].plot(weights[:, 0], color="#226184", label="$w_0$")
    axes[1].plot(weights[:, 1], "--", color="#a04018", label="$w_1$")
    axes[0].set_ylabel("Средний квадрат ошибки, дБFS" if russian else "Mean squared error (dBFS)")
    axes[1].set_ylabel("Коэффициент, отн. ед." if russian else "Weight (unitless)")
    axes[1].set_xlabel("Номер символа" if russian else "Symbol index")
    axes[0].set_title("Обучение и проверка LMS на канале с эхом" if russian else "LMS training and evaluation on an echo channel")
    axes[1].set_title("Коэффициенты в фиксированной точке" if russian else "Fixed-point coefficients")
    for axis in axes:
        axis.axvline(TRAIN, color="#444444", linewidth=0.9)
        axis.axvspan(TRAIN, COUNT, color="#e8edf2", alpha=0.55, zorder=0)
        axis.grid(alpha=0.2)
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncols=3, frameon=False)
    axes[1].legend(loc="center right")
    fig.savefig(path, dpi=165)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/lms-sim")
    parser.add_argument("--rtl", action="store_true", help="Check the generated vectors with Icarus")
    parser.add_argument("--reports", type=Path, help="Read the optional routed Vivado reports")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(exist_ok=True, parents=True)
    metrics, data, vectors = experiment()
    metrics["model_tool_versions"] = {
        "python": python_version(), "numpy": np.__version__, "matplotlib": matplotlib.__version__,
    }
    if args.rtl:
        metrics["rtl_simulation"] = run_rtl(output, vectors)
    if args.reports:
        metadata, resources = read_routed(args.reports, "lms")
        metrics["post_route_ooc"] = {**metadata, **resources}
    paths = (Path(__file__), RTL, BENCH, ROOT / "tools/fir_architectures_ooc.xdc",
             ROOT / "tools/vivado_lms_equalizer.tcl")
    metrics["source_sha256_lf"] = {
        path.resolve().relative_to(ROOT).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n"),
        ).hexdigest() for path in paths
    }
    (output / "lab515_lms_equalizer.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n",
    )
    plot(data, output / "lab515_lms_equalizer.png", russian=False)
    plot(data, output / "lab515_lms_equalizer_ru.png", russian=True)
    for name, result in metrics["evaluation"].items():
        print(f"{name}: MSE={result['mse_fs_squared']:.6f}, errors={result['bit_errors']}/{result['samples']}")


if __name__ == "__main__":
    main()
