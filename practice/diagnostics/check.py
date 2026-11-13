#!/usr/bin/env python3
"""Local diagnostic grader and instructor negative controls (issue #85)."""

from __future__ import annotations

import argparse
from functools import partial
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AXIS_REFERENCE = ROOT / "blocks/block_05_fpga_hdl_flow/rtl/axis_iq_passthrough.v"
PYTHON_CASES = ("cfo", "iq", "fir")


def load_module(path: Path):
    name = "diagnostic_" + hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load Python file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_info(path: Path) -> dict:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def observation(name: str, passed: bool, **metrics) -> dict:
    return {"test": name, "passed": bool(passed), "metrics": metrics}


def checked_array(value, length: int) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (length,) or not np.all(np.isfinite(array)):
        raise ValueError(f"Expected {length} finite output samples, got shape {array.shape}")
    return array


def check_cfo(candidate) -> list[dict]:
    # Reuse the course mapper and estimator. The grader measures residual CFO
    # against the known transmitted symbols, independently of that estimator.
    lab = load_module(ROOT / "blocks/block_08_modulation_and_synchronization/python/lab_8_1_cfo_estimation_correction.py")
    rng = np.random.default_rng(85)
    results = []
    for frequency in (2750.0, -3170.0, 0.0):
        for noise_rms in (0.0, 0.002):
            fs = 1_000_000.0
            bits = rng.integers(0, 2, size=4096, dtype=np.uint8)
            tx = lab.bits_to_qpsk(bits)
            n = np.arange(len(tx))
            rx = tx * np.exp(2j * np.pi * frequency * n / fs)
            rx += noise_rms * (rng.standard_normal(len(tx)) + 1j * rng.standard_normal(len(tx)))
            estimate = lab.estimate_cfo_4th_power(rx, fs)
            corrected = checked_array(candidate.correct_cfo(rx.copy(), estimate, fs), len(tx))
            phase_error = np.unwrap(np.angle(corrected * np.conj(tx)))
            residual_hz = float(np.polyfit(n, phase_error, 1)[0] * fs / (2 * np.pi))
            evm_percent = float(100 * np.sqrt(np.mean(np.abs(corrected - tx)**2)))
            _, bit_errors, compared_bits = lab.ber(bits, corrected)
            results.append(observation(
                f"cfo_{frequency:g}Hz_noise_{noise_rms:g}",
                abs(residual_hz) < 1.0 and evm_percent < 2.0 and bit_errors == 0,
                sample_rate_hz=fs, true_cfo_hz=frequency, estimated_cfo_hz=estimate,
                residual_cfo_hz=residual_hz, evm_percent=evm_percent,
                bit_errors=bit_errors, compared_bits=compared_bits, noise_rms=noise_rms,
            ))
    return results


def check_iq(candidate) -> list[dict]:
    results = []
    fs, count = 8192.0, 1024
    for frequency in (1000.0, -1504.0):
        tx = 0.65 * np.exp(1j * (2 * np.pi * frequency * np.arange(count) / fs + 0.31))
        raw = np.rint(np.column_stack((tx.real, tx.imag)) * 32768).astype(np.int16).ravel()
        decoded = checked_array(candidate.decode_iq(raw.copy()), count)
        peak = float(np.fft.fftfreq(count, 1 / fs)[np.argmax(np.abs(np.fft.fft(decoded)))])
        evm = float(100 * np.linalg.norm(decoded - tx) / np.linalg.norm(tx))
        results.append(observation(
            f"iq_tone_{frequency:g}Hz", peak == frequency and evm < 0.01,
            sample_rate_hz=fs, samples=count, expected_peak_hz=frequency,
            observed_peak_hz=peak, evm_percent=evm,
        ))
    raw = np.array([-32768, 32767, 0, -1, 1234, -5678], dtype=np.int16)
    expected = np.array([-1 + 32767j / 32768, -1j / 32768, (1234 - 5678j) / 32768])
    decoded = checked_array(candidate.decode_iq(raw.copy()), 3)
    error = float(np.max(np.abs(decoded - expected)))
    results.append(observation("iq_signed_endpoints", error < 1e-12, max_complex_error=error))
    return results


# Hand-derived output vectors keep the grading oracle separate from reference.py.
# Four -32768 * -32768 products sum to +2**32, which needs 34 signed bits.
FIR_VECTORS = (
    ("zero", [0] * 8, [8192, -16384, 4096, 12288], [0] * 8),
    ("causal_asymmetric_impulse", [16384, 0, 0, 0, 0], [8192, -16384, 4096, 12288], [4096, -8192, 2048, 6144, 0]),
    ("half_lsb_ties", [-3, -1, 1, 3], [16384], [-1, 0, 1, 2]),
    ("small_signal_scale", [1000, -1000, 2000, -2000], [16384], [500, -500, 1000, -1000]),
    ("positive_overload", [32767] * 4, [32767] * 4, [32766, 32767, 32767, 32767]),
    ("negative_overload", [-32768] * 4, [32767] * 4, [-32767, -32768, -32768, -32768]),
    ("signed_product_endpoint", [-32768] * 4, [-32768] * 4, [32767] * 4),
)


def check_fir(candidate) -> list[dict]:
    results = []
    for name, samples, coefficients, expected in FIR_VECTORS:
        actual = checked_array(candidate.fir_q15(list(samples), list(coefficients)), len(expected))
        if np.iscomplexobj(actual):
            raise ValueError("FIR output must contain signed Q1.15 integers")
        error = np.abs(actual.astype(np.float64) - expected)
        results.append(observation(
            name, np.array_equal(actual, expected), max_error_lsb=float(max(error)),
            mismatched_samples=int(np.count_nonzero(error)), expected=expected, actual=actual.tolist(),
        ))
    return results


def check_python(candidate, case: str) -> dict:
    checks = {"cfo": check_cfo, "iq": check_iq, "fir": check_fir}[case](candidate)
    return {"case": case, "evidence": "synthetic-software", "passed": all(c["passed"] for c in checks), "checks": checks}


def check_axis(source: Path) -> dict:
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp:
        raise RuntimeError("AXI check requires iverilog and vvp on PATH; no RTL result was produced")
    bench = HERE / "rtl/tb_axis_diagnostic.sv"
    with tempfile.TemporaryDirectory(prefix="sdr-diagnostic-") as directory:
        output = Path(directory) / "axis.out"
        compile_result = subprocess.run(
            [iverilog, "-g2012", "-s", "tb_axis_diagnostic", "-o", str(output), str(bench), str(source.resolve())],
            capture_output=True, text=True, timeout=30,
        )
        if compile_result.returncode:
            raise RuntimeError(f"RTL compile failed (not a detected mutant): {compile_result.stderr}")
        simulation = subprocess.run([vvp, str(output)], cwd=directory, capture_output=True, text=True, timeout=30)
    # A compile failure, timeout or missing completion marker is not evidence that
    # the transaction checker detected a deliberate behavioral defect.
    if "DIAGNOSTIC_FAIL:" in simulation.stdout and simulation.returncode != 0:
        passed = False
    elif "DIAGNOSTIC_PASS:" in simulation.stdout and simulation.returncode == 0:
        passed = True
    else:
        raise RuntimeError(f"RTL simulation did not complete its checks: {simulation.stdout}\n{simulation.stderr}")
    version = subprocess.run([iverilog, "-V"], capture_output=True, text=True, timeout=10).stdout.splitlines()[0]
    return {"case": "axis", "evidence": "rtl-simulation", "passed": passed,
            "source": source_info(source), "testbench": source_info(bench), "simulator": version,
            "exit_code": simulation.returncode, "log": simulation.stdout}


def self_test(*, with_rtl=False, rtl_only=False) -> dict:
    controls = []
    if not rtl_only:
        reference = load_module(HERE / "reference.py")
        starter = load_module(HERE / "starter.py")
        mutants = load_module(HERE / "mutants.py")
        for case in PYTHON_CASES:
            controls.append({"control": f"{case}_reference", "expected_pass": True, "result": check_python(reference, case)})
            controls.append({"control": f"{case}_starter", "expected_pass": False, "result": check_python(starter, case)})
        variants = (
            ("cfo_uncorrected", "cfo", SimpleNamespace(correct_cfo=mutants.uncorrected_cfo)),
            ("iq_conjugated", "iq", SimpleNamespace(decode_iq=mutants.conjugated_iq)),
            ("fir_wrong_q_format", "fir", SimpleNamespace(fir_q15=partial(mutants.fir_variant, shift=14))),
            ("fir_output_wrap", "fir", SimpleNamespace(fir_q15=partial(mutants.fir_variant, saturate=False))),
            ("fir_reversed_taps", "fir", SimpleNamespace(fir_q15=partial(mutants.fir_variant, reverse=True))),
        )
        for name, case, candidate in variants:
            controls.append({"control": name, "expected_pass": False, "result": check_python(candidate, case)})
    if with_rtl or rtl_only:
        for name, path, expected in (
            ("axis_reference", AXIS_REFERENCE, True),
            ("axis_drop", HERE / "rtl/axis_drop.v", False),
            ("axis_duplicate", HERE / "rtl/axis_duplicate.v", False),
        ):
            controls.append({"control": name, "expected_pass": expected, "result": check_axis(path)})
    passed = all(c["result"]["passed"] == c["expected_pass"] for c in controls)
    return {"mode": "instructor-self-test", "learner_completion": False, "passed": passed, "controls": controls,
            "python_sources": [source_info(HERE / name) for name in ("reference.py", "starter.py", "mutants.py")]}


def initialize(workspace: Path) -> None:
    # Never overwrite a learner's diagnosis or implementation, even on rerun.
    workspace.mkdir(parents=True, exist_ok=False)
    for source, name in ((HERE / "starter.py", "learner.py"),
                         (HERE / "rtl/axis_drop.v", "axis_iq_passthrough.v"),
                         (HERE / "report.template.md", "report.md")):
        shutil.copyfile(source, workspace / name)


def print_summary(result: dict) -> None:
    if "controls" in result:
        for control in result["controls"]:
            actual = control["result"]["passed"]
            verdict = "PASS" if actual == control["expected_pass"] else "FAIL"
            print(f"{verdict} {control['control']}: {'accepted' if actual else 'rejected'}")
        print("Instructor controls only; no learner completion recorded.")
    elif "checks" in result:
        for check in result["checks"]:
            print(f"{'PASS' if check['passed'] else 'FAIL'} {check['test']}: "
                  + json.dumps(check["metrics"], allow_nan=False))
    else:
        print(result["log"], end="")
    print(f"Overall: {'PASS' if result['passed'] else 'FAIL'}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a new learner workspace; refuse existing directories")
    init.add_argument("workspace", type=Path)
    check = commands.add_parser("check", help="Check a learner implementation without modifying it")
    check.add_argument("--case", choices=(*PYTHON_CASES, "axis"), required=True)
    check.add_argument("--implementation", type=Path, help="Learner Python file for cfo/iq/fir")
    check.add_argument("--rtl", type=Path, help="Learner Verilog module for axis")
    check.add_argument("--output", type=Path, help="Write a JSON result")
    controls = commands.add_parser("self-test", help="Check references and deliberate mutants, not student progress")
    mode = controls.add_mutually_exclusive_group()
    mode.add_argument("--with-rtl", action="store_true")
    mode.add_argument("--rtl-only", action="store_true")
    controls.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report_path = None
    try:
        if args.command == "init":
            initialize(args.workspace)
            print(f"Created {args.workspace}; record a hypothesis in report.md before checking.")
            return 0
        if args.output and (args.output.suffix != ".json" or args.output.resolve().is_relative_to(HERE)):
            raise ValueError("Write JSON results outside the exercise sources, for example under build/")
        report_path = args.output
        if args.command == "self-test":
            result = self_test(with_rtl=args.with_rtl, rtl_only=args.rtl_only)
        else:
            if args.case == "axis":
                if args.rtl is None or args.implementation is not None:
                    parser.error("--case axis requires --rtl only")
                result = check_axis(args.rtl)
            else:
                if args.implementation is None or args.rtl is not None:
                    parser.error("Python cases require --implementation only")
                result = check_python(load_module(args.implementation), args.case)
                result["source"] = source_info(args.implementation)
            result["mode"] = "implementation-check"
        result["python_version"] = platform.python_version()
        result["seed"] = 85
        result["grader"] = source_info(Path(__file__))
        rendered = json.dumps(result, indent=2, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print_summary(result)
        if args.output:
            print(f"JSON: {args.output}")
        return 0 if result["passed"] else 1
    except Exception as exc:
        # An implementation or tool error must replace a previous successful
        # report at the same destination, rather than leaving stale pass evidence.
        if report_path:
            error = {"mode": args.command, "passed": False, "completed": False,
                     "error": str(exc), "error_type": type(exc).__name__}
            try:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(error, indent=2) + "\n", encoding="utf-8")
            except OSError as write_error:
                print(f"ERROR: cannot write failure report: {write_error}", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
