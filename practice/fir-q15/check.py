"""Offline cumulative grader for the FIR/Q15 student exercise."""

import argparse
import hashlib
import importlib.util
import math
import random
import shutil
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _load_candidate(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing student file: {path}")
    spec = importlib.util.spec_from_file_location("fir_q15_candidate", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load candidate: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def _float_equal(actual, expected, label):
    if len(actual) != len(expected) or any(
        not math.isfinite(a) or abs(a - b) > 1e-12 for a, b in zip(actual, expected)
    ):
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def _check_float(module):
    x = [1.0, 2.0, 3.0]
    h = [0.5, 0.25]
    _float_equal(module.fir_float(x, h), [0.5, 1.25, 2.0], "causal taps")
    _float_equal(
        module.fir_float([1.0, -1.0, 0.5], [0.25, -0.125]),
        [0.25, -0.375, 0.25],
        "signed input and taps",
    )
    _float_equal(module.fir_float([], [1.0]), [], "empty input")
    _float_equal(module.fir_float([1.0, 2.0], []), [0.0, 0.0], "empty taps")
    _float_equal(module.fir_float([0.0] * 6, [0.25, -0.5, 0.125]), [0.0] * 6, "zero input")
    _float_equal(module.fir_float([1.0, 0.0, 0.0, 0.0], [0.25, -0.5, 0.125]),
                 [0.25, -0.5, 0.125, 0.0], "asymmetric impulse response")
    _equal(x, [1.0, 2.0, 3.0], "input unchanged")
    _equal(h, [0.5, 0.25], "taps unchanged")
    rng = random.Random(15)
    samples = [rng.uniform(-0.75, 0.75) for _ in range(18)]
    taps = [rng.uniform(-0.3, 0.3) for _ in range(5)]
    expected = [
        sum(taps[k] * samples[n - k] for k in range(min(n + 1, len(taps))))
        for n in range(len(samples))
    ]
    _float_equal(module.fir_float(samples, taps), expected, "regression vector")


def _check_quantizer(module):
    _equal(module.quantize_q15([]), [], "empty quantizer input")
    data = [0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5]
    _equal(
        module.quantize_q15(data),
        [0, 16384, -16384, 32767, -32768, 32767, -32768],
        "Q15 endpoints and clipping",
    )
    _equal(data, [0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5], "input unchanged")
    _equal(
        module.quantize_q15([0.5 / 32768, 1.5 / 32768, -0.5 / 32768, -1.5 / 32768]),
        [0, 2, 0, -2],
        "nearest-even ties",
    )
    rng = random.Random(16)
    data = [rng.uniform(-1.2, 1.2) for _ in range(60)]
    expected = [min(32767, max(-32768, round(v * 32768))) for v in data]
    _equal(module.quantize_q15(data), expected, "regression vector")


def _round_div_even(value):
    quotient, remainder = divmod(abs(value), 32768)
    if remainder > 16384 or (remainder == 16384 and quotient % 2 == 1):
        quotient += 1
    return quotient if value >= 0 else -quotient


def _check_integer_fir(module):
    _equal(module.fir_q15([16384, 16384], [16384, 16384]), [8192, 16384], "Q15 FIR")
    _equal(module.fir_q15([1, 3, -1, -3], [16384]), [0, 2, 0, -2], "ties even")
    _equal(
        module.fir_q15([32767, 32767, 32767], [32767, 32767, 32767]),
        [32766, 32767, 32767],
        "positive saturation",
    )
    _equal(module.fir_q15([-32768, -32768], [32767, 32767]), [-32767, -32768], "negative saturation")
    _equal(module.fir_q15([], [16384]), [], "empty input")
    _equal(module.fir_q15([100, 200], []), [0, 0], "empty taps")
    _equal(module.fir_q15([0] * 6, [8192, -16384, 4096]), [0] * 6, "zero input")
    _equal(module.fir_q15([16384, 0, 0, 0], [8192, -16384, 4096]),
           [4096, -8192, 2048, 0], "asymmetric integer impulse")
    _equal(module.fir_q15([-32768] * 4, [-32768] * 4), [32767] * 4, "wide accumulator endpoint")
    rng = random.Random(17)
    x = [rng.randint(-32768, 32767) for _ in range(64)]
    h = [rng.randint(-32768, 32767) for _ in range(9)]
    expected = []
    for n in range(len(x)):
        acc = 0
        for k, coeff in enumerate(h):
            if k <= n:
                acc += coeff * x[n - k]
        expected.append(min(32767, max(-32768, _round_div_even(acc))))
    saved_x, saved_h = x.copy(), h.copy()
    _equal(module.fir_q15(x, h), expected, "integer regression vector")
    _equal(x, saved_x, "integer input unchanged")
    _equal(h, saved_h, "integer taps unchanged")
    small_x = [rng.randint(-4096, 4096) for _ in range(32)]
    small_h = [rng.randint(-4096, 4096) for _ in range(5)]
    actual = module.fir_q15(small_x, small_h)
    exact = [sum(small_h[k] * small_x[n - k] for k in range(min(n + 1, len(small_h)))) / 32768
             for n in range(len(small_x))]
    if len(actual) != len(exact) or any(not math.isfinite(a) or abs(a - b) > 0.5 for a, b in zip(actual, exact)):
        raise AssertionError("low-level fixed-point error exceeds half an output LSB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", type=Path, metavar="DIRECTORY")
    mode.add_argument("--stage", type=int, choices=(1, 2, 3))
    parser.add_argument("--path", type=Path, default=Path("work/fir-q15"))
    parser.add_argument("--solution", action="store_true")
    args = parser.parse_args()

    if args.init is not None:
        if args.solution:
            parser.error("--solution does not apply to --init")
        destination = args.init / "starter.py"
        if destination.exists():
            parser.error(f"{destination} exists; refusing to overwrite learner work")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / "starter.py", destination)
        print(f"Initialized learner workspace: {destination}")
        return 0

    candidate = HERE / "reference.py" if args.solution else args.path / "starter.py"
    try:
        print(f"Checking {'instructor reference' if args.solution else 'learner implementation'}: {candidate}")
        print(f"Source SHA-256: {hashlib.sha256(candidate.read_bytes()).hexdigest()}")
        module = _load_candidate(candidate)
        checks = (_check_float, _check_quantizer, _check_integer_fir)
        for index, check in enumerate(checks[: args.stage], start=1):
            check(module)
            print(f"PASS stage {index}: {check.__name__}")
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print(f"PASS: all stages 1-{args.stage} (software-only)")
    if args.solution:
        print("Instructor reference only; no learner completion recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
