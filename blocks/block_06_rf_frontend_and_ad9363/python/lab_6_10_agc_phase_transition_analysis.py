#!/usr/bin/env python3
"""Lab 6.10 -- AGC/LNA gain-transition phase-discontinuity analysis (issue #58).

Turns one raw IQ capture plus a metadata sidecar describing where gain-state
transitions occur (see ``templates/gain_transition_capture_metadata.template.json``)
into, per transition: an amplitude step, a phase discontinuity that is
separated from ordinary CFO-driven phase rotation, and a settling/recovery
time back onto the pre-transition CFO trend.

The key measurement problem this tool solves (from the issue): a receiver's
phase keeps rotating continuously because of CFO even with no gain event at
all, so a raw "phase before vs phase after" comparison at a gain transition
cannot tell a gain-correlated phase glitch apart from ordinary CFO rotation.
This script fits the CFO-driven linear phase trend from a window *before* the
transition, extrapolates it across the transition, and reports the residual
between the extrapolated and the actually observed phase as the
transition-correlated discontinuity -- exactly the two effects the issue asks
to keep separate.

Evidence boundary: this is a general-purpose IQ analysis tool, not a claim
about any real AD9361/AD9363 AGC behavior. ``--self-test`` proves the
separation logic on synthetic IQ with a *known* injected CFO, a *known*
amplitude step and a *known* injected phase discontinuity (plus a zero-
discontinuity control case). It produces no RF/hardware measurement.
Real AGC evidence requires a real gain-state transition captured on
hardware -- the issue's own acceptance criteria (#58) -- which this
environment does not have.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


SUPPORTED_FORMATS = {"ci16", "cu8", "cf32"}


def read_iq(path: Path, iq_format: str) -> np.ndarray:
    """Minimal ci16/cu8/cf32 adapter; see docs/iq-recording-metadata.md."""
    if iq_format == "ci16":
        raw = np.fromfile(path, dtype="<i2")
        scale, zero = 32768.0, 0.0
    elif iq_format == "cu8":
        raw = np.fromfile(path, dtype=np.uint8)
        scale, zero = 127.5, 127.5
    elif iq_format == "cf32":
        raw = np.fromfile(path, dtype="<f4")
        scale, zero = 1.0, 0.0
    else:
        raise ValueError(f"unsupported iq_format {iq_format!r}; expected one of {sorted(SUPPORTED_FORMATS)}")
    if raw.size == 0:
        raise ValueError(f"capture is empty: {path}")
    if raw.size % 2:
        raise ValueError(f"capture has an odd number of scalar values: {raw.size}")
    values = raw.astype(np.float64)
    return (values[0::2] - zero) / scale + 1j * (values[1::2] - zero) / scale


@dataclass(frozen=True)
class TransitionResult:
    sample_index: int
    fit_window: int
    amplitude_before_dbfs: float
    amplitude_after_dbfs: float
    amplitude_step_db: float
    fitted_cfo_rad_per_sample: float
    expected_phase_rad: float
    observed_phase_rad: float
    phase_discontinuity_rad: float
    phase_discontinuity_deg: float
    recovery_samples: int | None


def _unwrap(phase: np.ndarray) -> np.ndarray:
    return np.unwrap(phase)


def _wrap_pi(angle: np.ndarray | float) -> np.ndarray | float:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def analyze_transition(
    x: np.ndarray,
    sample_index: int,
    *,
    fit_window: int = 256,
    recovery_search: int = 512,
    recovery_threshold_rad: float = 0.15,
    full_scale: float = 1.0,
) -> TransitionResult:
    """Characterize one gain transition at ``sample_index`` inside ``x``.

    ``fit_window`` samples immediately before the transition establish the
    CFO-driven phase trend (a straight-line fit of unwrapped phase versus
    sample index); the same trend, extrapolated one sample past the fit
    window, is compared against the phase actually observed there. Amplitude
    is summarized before/after as a plain RMS level in dBFS rather than
    folded into the phase fit, so a gain step (which is expected to change
    amplitude) cannot bias the phase-discontinuity estimate.
    """
    x = np.asarray(x, dtype=np.complex128)
    if sample_index - fit_window < 0 or sample_index + 1 >= x.size:
        raise ValueError(
            f"sample_index={sample_index} needs at least {fit_window} samples before it "
            f"and at least 1 sample after it inside a capture of {x.size} samples"
        )

    before = x[sample_index - fit_window : sample_index]
    after_window = x[sample_index : min(x.size, sample_index + fit_window)]

    amplitude_before_dbfs = float(20.0 * np.log10(max(np.sqrt(np.mean(np.abs(before) ** 2)), 1e-15) / full_scale))
    amplitude_after_dbfs = float(20.0 * np.log10(max(np.sqrt(np.mean(np.abs(after_window) ** 2)), 1e-15) / full_scale))

    phase_before = _unwrap(np.angle(before))
    index_before = np.arange(-fit_window, 0, dtype=np.float64)
    slope, intercept = np.polyfit(index_before, phase_before, 1)

    expected_phase = float(_wrap_pi(intercept + slope * 0.0))
    observed_phase = float(np.angle(x[sample_index]))
    discontinuity = float(_wrap_pi(observed_phase - expected_phase))

    recovery_samples: int | None = None
    tail_end = min(x.size, sample_index + recovery_search)
    tail = x[sample_index:tail_end]
    tail_phase = _unwrap(np.angle(tail))
    tail_index = np.arange(tail.size, dtype=np.float64)
    predicted_tail = intercept + slope * tail_index + discontinuity
    residual = np.abs(_wrap_pi(tail_phase - predicted_tail))
    settled = np.where(residual < recovery_threshold_rad)[0]
    if settled.size > 0:
        recovery_samples = int(settled[0])

    return TransitionResult(
        sample_index=int(sample_index),
        fit_window=int(fit_window),
        amplitude_before_dbfs=amplitude_before_dbfs,
        amplitude_after_dbfs=amplitude_after_dbfs,
        amplitude_step_db=amplitude_after_dbfs - amplitude_before_dbfs,
        fitted_cfo_rad_per_sample=float(slope),
        expected_phase_rad=expected_phase,
        observed_phase_rad=observed_phase,
        phase_discontinuity_rad=discontinuity,
        phase_discontinuity_deg=float(np.degrees(discontinuity)),
        recovery_samples=recovery_samples,
    )


def _synthetic_capture(
    *,
    n: int,
    transition_index: int,
    cfo_rad_per_sample: float,
    amplitude_before: float,
    amplitude_after: float,
    injected_discontinuity_rad: float,
    noise_std: float,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_index = np.arange(n, dtype=np.float64)
    phase = cfo_rad_per_sample * n_index
    phase[transition_index:] += injected_discontinuity_rad
    amplitude = np.where(n_index < transition_index, amplitude_before, amplitude_after)
    signal = amplitude * np.exp(1j * phase)
    noise = noise_std * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    return signal + noise


def run_self_test() -> dict:
    """Prove the CFO/gain-transition separation on synthetic IQ, both ways."""
    n = 4096
    transition_index = 2048
    cfo_rad_per_sample = 0.013  # a few kHz-scale rotation per sample, deliberately not tiny
    injected_discontinuity_rad = 1.1  # ~63 degrees, clearly resolvable
    common_kwargs = dict(
        n=n,
        transition_index=transition_index,
        cfo_rad_per_sample=cfo_rad_per_sample,
        amplitude_before=0.20,
        amplitude_after=0.55,
        noise_std=0.002,
    )

    with_glitch = _synthetic_capture(
        injected_discontinuity_rad=injected_discontinuity_rad, seed=610, **common_kwargs
    )
    without_glitch = _synthetic_capture(injected_discontinuity_rad=0.0, seed=611, **common_kwargs)

    result_with = analyze_transition(with_glitch, transition_index)
    result_without = analyze_transition(without_glitch, transition_index)

    detected_error_rad = abs(result_with.phase_discontinuity_rad - injected_discontinuity_rad)
    control_error_rad = abs(result_without.phase_discontinuity_rad - 0.0)
    amplitude_step_error_db = abs(
        result_with.amplitude_step_db - 20.0 * np.log10(common_kwargs["amplitude_after"] / common_kwargs["amplitude_before"])
    )
    cfo_error = abs(result_with.fitted_cfo_rad_per_sample - cfo_rad_per_sample)

    passed = bool(
        detected_error_rad < 0.05
        and control_error_rad < 0.05
        and amplitude_step_error_db < 0.2
        and cfo_error < 1e-3
        and result_with.recovery_samples is not None
        and result_with.recovery_samples < 10
    )

    return {
        "evidence_scope": "synthetic-self-test-only",
        "hardware_measurement_claimed": False,
        "injected_cfo_rad_per_sample": cfo_rad_per_sample,
        "injected_discontinuity_rad": injected_discontinuity_rad,
        "with_glitch": asdict(result_with),
        "without_glitch_control": asdict(result_without),
        "detected_discontinuity_error_rad": detected_error_rad,
        "control_false_positive_error_rad": control_error_rad,
        "self_test_pass": passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", nargs="?", type=Path, help="raw ci16/cu8/cf32 capture")
    parser.add_argument("--metadata", type=Path, help="JSON sidecar with sampling.iq_format and gain_transitions")
    parser.add_argument("--fit-window", type=int, default=256, help="samples before the transition used for the CFO fit")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    parser.add_argument("--self-test", action="store_true", help="run the no-hardware synthetic separation proof")
    return parser.parse_args()


def analyze_capture_file(capture_path: Path, metadata_path: Path, *, fit_window: int) -> dict:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    sampling = metadata["sampling"]
    iq_format = str(sampling["iq_format"]).lower()
    x = read_iq(capture_path, iq_format)

    transitions = metadata.get("gain_transitions", [])
    if not transitions:
        raise ValueError(f"{metadata_path}: 'gain_transitions' must list at least one transition sample_index")

    results = [
        asdict(analyze_transition(x, int(t["sample_index"]), fit_window=fit_window)) for t in transitions
    ]
    return {
        "evidence_scope": "draft-from-real-capture",
        "hardware_measurement_claimed": True,
        "capture": str(capture_path),
        "metadata": str(metadata_path),
        "transitions": results,
    }


def main() -> int:
    args = parse_args()
    if args.self_test:
        result = run_self_test()
        rc = 0 if result["self_test_pass"] else 1
    else:
        if args.capture is None or args.metadata is None:
            raise SystemExit("both a capture path and --metadata are required unless --self-test is used")
        result = analyze_capture_file(args.capture, args.metadata, fit_window=args.fit_window)
        rc = 0

    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
