#!/usr/bin/env python3
"""Run the executable course labs and create a reproducibility summary.

This script is intentionally lightweight: it runs representative Python labs
from the executable blocks and records pass/fail status plus generated artifacts.
It is used by the full-course smoke workflow and can also be executed locally.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_JSON = ROOT / "docs" / "assets" / "course_reproducibility_summary.json"
SUMMARY_MD = ROOT / "docs" / "assets" / "course_reproducibility_summary.md"
QUICK_LAB_COUNT = 2
Validator = Callable[[Path], list[str]]


@dataclass(frozen=True)
class LabCommand:
    name: str
    command: list[str]
    expected_artifacts: list[str]
    validator: Validator | None = None


@dataclass(frozen=True)
class LabResult:
    name: str
    return_code: int
    passed: bool
    missing_artifacts: list[str]
    validation_errors: list[str]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_lab64(root: Path) -> list[str]:
    payload = load_json(root / "docs/assets/lab64_synthetic_rf_capture_metrics.json")
    errors: list[str] = []
    if abs(payload["frequency_error_hz"]) > 50.0:
        errors.append(f"frequency_error_hz={payload['frequency_error_hz']:.3f} exceeds 50 Hz")
    if payload["snr_db"] < 40.0:
        errors.append(f"snr_db={payload['snr_db']:.2f} below 40 dB")
    if payload["clipping_count"] != 0:
        errors.append(f"clipping_count={payload['clipping_count']} is non-zero")
    if payload["overload_flag"]:
        errors.append("overload_flag is true")
    return errors


def validate_lab21(root: Path) -> list[str]:
    metrics = load_json(root / "docs/assets/lab21_sampling_metrics.json")["metrics"]
    errors: list[str] = []
    if abs(metrics["correct_frequency_error_hz"]) > 50.0:
        errors.append(
            f"correct_frequency_error_hz={metrics['correct_frequency_error_hz']:.3f} exceeds 50 Hz"
        )
    if abs(metrics["wrong_interpretation_error_hz"]) < 20_000.0:
        errors.append("wrong sampling-rate interpretation did not create a large enough error")
    if metrics["clipping_fraction"] > 0.001:
        errors.append(f"clipping_fraction={metrics['clipping_fraction']:.6f} exceeds 0.1%")
    return errors


def validate_lab22(root: Path) -> list[str]:
    metrics = load_json(root / "docs/assets/lab22_aliasing_metrics.json")["metrics"]
    errors: list[str] = []
    if metrics["max_alias_error_hz"] > 50.0:
        errors.append(f"max_alias_error_hz={metrics['max_alias_error_hz']:.3f} exceeds 50 Hz")
    if len(metrics["cases"]) < 3:
        errors.append("fewer than three aliasing example cases were generated")
    return errors


def validate_lab23(root: Path) -> list[str]:
    metrics = load_json(root / "docs/assets/lab23_iq_metrics.json")["metrics"]
    errors: list[str] = []
    if abs(metrics["correct_error_hz"]) > 50.0:
        errors.append(f"correct_error_hz={metrics['correct_error_hz']:.3f} exceeds 50 Hz")
    if abs(metrics["swapped_error_hz"]) > 50.0:
        errors.append(f"swapped_error_hz={metrics['swapped_error_hz']:.3f} exceeds 50 Hz")
    if abs(metrics["real_mirror_balance_hz"]) > 50.0:
        errors.append(f"real_mirror_balance_hz={metrics['real_mirror_balance_hz']:.3f} exceeds 50 Hz")
    return errors


def validate_lab73(root: Path) -> list[str]:
    metrics = load_json(root / "docs/assets/lab73_tx_rx_loopback_metrics.json")["metrics"]
    errors: list[str] = []
    if abs(metrics["residual_frequency_error_hz"]) > 250.0:
        errors.append(
            f"residual_frequency_error_hz={metrics['residual_frequency_error_hz']:.3f} exceeds 250 Hz"
        )
    if metrics["evm_percent"] > 15.0:
        errors.append(f"evm_percent={metrics['evm_percent']:.3f} exceeds 15%")
    if metrics["ber"] > 1e-9:
        errors.append(f"ber={metrics['ber']:.6e} is non-zero")
    return errors


def validate_lab84(root: Path) -> list[str]:
    metrics = load_json(root / "docs/assets/lab84_sync_chain_metrics.json")["metrics"]
    errors: list[str] = []
    if abs(metrics["cfo_error_hz"]) > 20.0:
        errors.append(f"cfo_error_hz={metrics['cfo_error_hz']:.3f} exceeds 20 Hz")
    if abs(metrics["phase_error_rad"]) > 0.2:
        errors.append(f"phase_error_rad={metrics['phase_error_rad']:.6f} exceeds 0.2 rad")
    if metrics["evm_final_percent"] > 10.0:
        errors.append(f"evm_final_percent={metrics['evm_final_percent']:.3f} exceeds 10%")
    if metrics["ber_final"] > 1e-9:
        errors.append(f"ber_final={metrics['ber_final']:.6e} is non-zero")
    if metrics["evm_final_percent"] >= metrics["evm_raw_percent"]:
        errors.append("final EVM did not improve over raw EVM")
    return errors


def validate_lab93(root: Path) -> list[str]:
    captures = load_json(root / "docs/assets/lab93_multiformat_iq_metrics.json")["captures"]
    errors: list[str] = []
    for capture in captures:
        fmt = capture["iq_format"]
        if abs(capture["frequency_error_hz"]) > 100.0:
            errors.append(f"{fmt}: frequency_error_hz={capture['frequency_error_hz']:.3f} exceeds 100 Hz")
        if capture["snr_db"] < 50.0:
            errors.append(f"{fmt}: snr_db={capture['snr_db']:.2f} below 50 dB")
        if capture["clipping_fraction"] > 0.01:
            errors.append(f"{fmt}: clipping_fraction={capture['clipping_fraction']:.6f} exceeds 1%")
    return errors


def validate_end_to_end_tone(root: Path) -> list[str]:
    metrics = load_json(root / "docs/assets/end_to_end_tone_metrics.json")
    errors: list[str] = []
    if abs(metrics["frequency_error_hz"]) > 1000.0:
        errors.append(f"frequency_error_hz={metrics['frequency_error_hz']:.3f} exceeds 1000 Hz")
    if metrics["estimated_snr_db"] < 50.0:
        errors.append(f"estimated_snr_db={metrics['estimated_snr_db']:.2f} below 50 dB")
    if metrics["clipping_fraction"] > 0.001:
        errors.append(f"clipping_fraction={metrics['clipping_fraction']:.6f} exceeds 0.1%")
    return errors


LABS: list[LabCommand] = [
    LabCommand(
        "Block 3 / Lab 3.5 FFT complexity and selected-bin trade-off",
        [sys.executable, "blocks/block_03_dsp_basics/python/lab_3_5_fft_complexity.py"],
        [
            "docs/assets/lab35_dft_fft_complexity.png",
            "docs/assets/lab35_selected_bin_tradeoff.png",
            "docs/assets/lab35_fft_complexity_metrics.json",
        ],
    ),
    LabCommand(
        "Block 3 / Lab 3.6 convolution and correlation",
        [sys.executable, "blocks/block_03_dsp_basics/python/lab_3_6_convolution_correlation.py"],
        [
            "docs/assets/lab36_convolution_filtering.png",
            "docs/assets/lab36_correlation_detection.png",
            "docs/assets/lab36_correlation_metrics.json",
        ],
    ),
    LabCommand(
        "Block 3 / Lab 3.7 window trade-offs and weak-signal detection",
        [sys.executable, "blocks/block_03_dsp_basics/python/lab_3_7_window_tradeoffs.py"],
        [
            "docs/assets/lab37_window_tradeoffs.png",
            "docs/assets/lab37_weak_signal_detection.png",
            "docs/assets/lab37_window_metrics.json",
        ],
    ),
    LabCommand(
        "Block 2 / Lab 2.1 sampling axis and interpretation checks",
        [sys.executable, "blocks/block_02_signals_and_sampling/python/sampling_analysis.py"],
        [
            "docs/assets/lab21_sampling_time_domain.png",
            "docs/assets/lab21_sampling_frequency_axis.png",
            "docs/assets/lab21_sampling_metrics.json",
        ],
        validate_lab21,
    ),
    LabCommand(
        "Block 2 / Lab 2.2 aliasing sweep and example spectra",
        [sys.executable, "blocks/block_02_signals_and_sampling/python/aliasing_sweep.py"],
        [
            "docs/assets/lab22_aliasing_map.png",
            "docs/assets/lab22_aliasing_examples.png",
            "docs/assets/lab22_aliasing_metrics.json",
        ],
        validate_lab22,
    ),
    LabCommand(
        "Block 2 / Lab 2.3 I/Q interpretation and mirrored spectrum checks",
        [sys.executable, "blocks/block_02_signals_and_sampling/python/iq_visualization.py"],
        [
            "docs/assets/lab23_iq_components_time.png",
            "docs/assets/lab23_iq_interpretation_spectra.png",
            "docs/assets/lab23_iq_metrics.json",
        ],
        validate_lab23,
    ),
    LabCommand(
        "Block 6 / Lab 6.4 synthetic RF capture analysis",
        [sys.executable, "blocks/block_06_rf_frontend_and_ad9363/python/lab_6_4_synthetic_rf_capture_analysis.py"],
        [
            "docs/assets/lab64_synthetic_rf_capture_fft.png",
            "docs/assets/lab64_synthetic_rf_capture_time.png",
            "docs/assets/lab64_synthetic_rf_capture_metrics.json",
        ],
        validate_lab64,
    ),
    LabCommand(
        "Block 7 / Lab 7.3 TX/RX loopback metrics",
        [sys.executable, "blocks/block_07_tx_rx_chains/python/lab_7_3_tx_rx_loopback_metrics.py"],
        [
            "docs/assets/lab73_tx_rx_loopback_spectrum.png",
            "docs/assets/lab73_tx_constellation.png",
            "docs/assets/lab73_rx_constellation_after_ddc.png",
            "docs/assets/lab73_tx_rx_loopback_metrics.json",
        ],
        validate_lab73,
    ),
    LabCommand(
        "Block 7 / Lab 7.5 CIC decimator",
        [sys.executable, "blocks/block_07_tx_rx_chains/python/lab_7_5_cic_decimator.py"],
        [
            "docs/assets/lab75_cic_response.png",
            "docs/assets/lab75_cic_decimation_spectrum.png",
            "docs/assets/lab75_cic_bit_growth.png",
            "docs/assets/lab75_cic_metrics.json",
        ],
    ),
    LabCommand(
        "Block 8 / Lab 8.4 end-to-end synchronization chain",
        [sys.executable, "blocks/block_08_modulation_and_synchronization/python/lab_8_4_end_to_end_sync_chain.py"],
        [
            "docs/assets/lab84_sync_constellation_raw.png",
            "docs/assets/lab84_sync_constellation_after_timing.png",
            "docs/assets/lab84_sync_constellation_final.png",
            "docs/assets/lab84_sync_chain_metrics.json",
        ],
        validate_lab84,
    ),
    LabCommand(
        "Block 9 / Lab 9.3 multi-format IQ reader",
        [sys.executable, "blocks/block_09_recording_and_analysis_tools/python/lab_9_3_multi_format_iq_reader.py"],
        [
            "docs/assets/lab93_multiformat_iq_metrics.json",
            "docs/assets/lab93_multiformat_iq_spectrum_ci16.png",
            "docs/assets/lab93_multiformat_iq_spectrum_cu8.png",
            "docs/assets/lab93_multiformat_iq_spectrum_cf32.png",
        ],
        validate_lab93,
    ),
    LabCommand(
        "Block 11 / End-to-end tone demo",
        [sys.executable, "blocks/block_11_integrated_sdr_project/python/end_to_end_tone_demo.py"],
        [
            "docs/assets/end_to_end_tone_reference_spectrum.png",
            "docs/assets/end_to_end_tone_capture_spectrum.png",
            "docs/assets/end_to_end_tone_capture_time.png",
            "docs/assets/end_to_end_tone_metrics.json",
            "datasets/manifests/end_to_end_tone_demo_v1.yml",
        ],
        validate_end_to_end_tone,
    ),
]


def run_lab(lab: LabCommand) -> LabResult:
    print(f"\n=== {lab.name} ===")
    completed = subprocess.run(lab.command, cwd=ROOT, text=True)
    missing = [p for p in lab.expected_artifacts if not (ROOT / p).is_file() or (ROOT / p).stat().st_size == 0]
    validation_errors = lab.validator(ROOT) if completed.returncode == 0 and not missing and lab.validator else []
    passed = completed.returncode == 0 and not missing and not validation_errors
    return LabResult(lab.name, completed.returncode, passed, missing, validation_errors)


def write_summary(results: list[LabResult]) -> None:
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "passed": all(r.passed for r in results),
        "lab_count": len(results),
        "results": [asdict(r) for r in results],
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Course reproducibility summary", "", f"Overall result: **{'PASS' if payload['passed'] else 'FAIL'}**", ""]
    lines.append("| Lab | Result | Missing artifacts | Validation errors |")
    lines.append("|---|---:|---|---|")
    for r in results:
        missing = ", ".join(r.missing_artifacts) if r.missing_artifacts else "-"
        validation = "; ".join(r.validation_errors) if r.validation_errors else "-"
        lines.append(f"| {r.name} | {'PASS' if r.passed else 'FAIL'} | {missing} | {validation} |")
    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run representative executable course labs.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help=f"Run a smaller subset ({QUICK_LAB_COUNT} labs) for faster local checks.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip writing summary files in docs/assets.",
    )
    args = parser.parse_args()

    selected_labs = LABS[:QUICK_LAB_COUNT] if args.quick else LABS
    print(f"Running {len(selected_labs)} of {len(LABS)} configured labs.")

    results = [run_lab(lab) for lab in selected_labs]
    if not args.no_summary:
        write_summary(results)

    for r in results:
        print(f"{r.name}: {'PASS' if r.passed else 'FAIL'}")
        if r.missing_artifacts:
            print("  Missing:", ", ".join(r.missing_artifacts))
        if r.validation_errors:
            print("  Validation:", "; ".join(r.validation_errors))
    if args.no_summary:
        print("\nSummary writing skipped (--no-summary).")
    else:
        print(f"\nSummary JSON: {SUMMARY_JSON}")
        print(f"Summary Markdown: {SUMMARY_MD}")
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
