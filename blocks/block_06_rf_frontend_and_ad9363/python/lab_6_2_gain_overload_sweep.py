#!/usr/bin/env python3
"""Lab 6.2 -- AD9363 gain/overload sweep analyzer (issue #29 software infrastructure).

Turns a set of captured -- or, for ``--self-test``, synthetic -- IQ points into
the measurement table used by ``templates/ad9363-gain-overload-log.md``: peak
and RMS level in dBFS, clipping fraction, a simple spectral SNR estimate and
an overload flag, one row per gain/attenuation setting.

Evidence boundary, stated exactly like ``templates/ad9363-gain-overload-log.md``
already requires: this script produces DRAFT rows only. "Do not fill it with
guessed values. Every promoted row must come from a real board session." A
real capture comes from AD9363/RTL-SDR hardware, which this environment does
not have. ``--self-test`` proves the analysis math (dBFS, clipping detection,
overload flag) on synthetic data and is labeled ``synthetic`` throughout; it
is not a hardware measurement and must never be pasted into a promoted log as
one.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_FORMATS = {"ci16", "cu8", "cf32"}

# A row is flagged overloaded when any sample clips, the peak sits within 1 dB
# of full scale, or the spectral SNR estimate looks implausibly low for a
# tone-in-noise capture -- the same three symptoms Lab 6.2 teaches to look for.
OVERLOAD_PEAK_DBFS = -1.0
OVERLOAD_MIN_SNR_DB = 10.0


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
class GainPointResult:
    test_id: str
    rx_tx_path: str
    tx_setting: str
    rx_gain_db: str
    external_attenuation_db: str
    peak_dbfs: float
    rms_dbfs: float
    snr_db: float
    sfdr_db: float
    clipping_fraction: float
    clipping_count: int
    overload: bool
    notes: str
    synthetic: bool


def analyze_iq(x: np.ndarray, *, full_scale: float = 1.0) -> dict:
    """Peak/RMS dBFS, a clipping fraction, a simple tone-vs-noise-floor SNR and SFDR.

    The SNR compares the tone bin with the *median* bin, so it is blind to a few
    strong spurs: clipping harmonics barely move the median. SFDR compares the tone
    with the *largest* bin outside it, which is where clipping shows up.
    """
    x = np.asarray(x, dtype=np.complex128)
    if x.size == 0:
        raise ValueError("capture has zero samples")

    magnitude = np.abs(x)
    peak = float(np.max(magnitude))
    rms = float(np.sqrt(np.mean(magnitude**2)))
    peak_dbfs = float(20.0 * np.log10(max(peak, 1e-15) / full_scale))
    rms_dbfs = float(20.0 * np.log10(max(rms, 1e-15) / full_scale))

    clip_threshold = 0.999 * full_scale
    clipping_count = int(np.sum(np.abs(np.real(x)) >= clip_threshold) + np.sum(np.abs(np.imag(x)) >= clip_threshold))
    clipping_fraction = clipping_count / (2 * x.size)

    n = min(x.size, 65536)
    window = np.hanning(n)
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    peak_bin = int(np.argmax(mag_db))
    exclusion = max(5, n // 200)
    lo, hi = max(0, peak_bin - exclusion), min(n, peak_bin + exclusion + 1)
    noise_mask = np.ones(n, dtype=bool)
    noise_mask[lo:hi] = False
    noise_floor_db = float(np.median(mag_db[noise_mask])) if np.any(noise_mask) else float(np.min(mag_db))
    snr_db = float(mag_db[peak_bin] - noise_floor_db)
    sfdr_db = float(mag_db[peak_bin] - np.max(mag_db[noise_mask])) if np.any(noise_mask) else 0.0

    overload = bool(clipping_count > 0 or peak_dbfs > OVERLOAD_PEAK_DBFS or snr_db < OVERLOAD_MIN_SNR_DB)

    return {
        "peak_dbfs": peak_dbfs,
        "rms_dbfs": rms_dbfs,
        "snr_db": snr_db,
        "sfdr_db": sfdr_db,
        "clipping_fraction": clipping_fraction,
        "clipping_count": clipping_count,
        "overload": overload,
    }


def synthetic_capture(sim_gain_db: float, *, n: int = 8192, seed: int = 29) -> np.ndarray:
    """Deterministic tone+noise capture whose amplitude tracks a nominal RX gain.

    Purely a self-test fixture: the mapping from ``sim_gain_db`` to amplitude is
    an arbitrary but monotonic and reproducible curve, chosen so the sweep
    crosses from a clean tone-in-noise capture into visible clipping -- proving
    the overload/clipping detection responds to increasing gain the way a real
    RX gain sweep should, without claiming any calibrated real-world value.
    """
    rng = np.random.default_rng(seed + 1000 + int(round(sim_gain_db * 10)))
    amplitude = min(1.35, 0.03 * (10.0 ** (sim_gain_db / 20.0)))
    t = np.arange(n)
    tone = amplitude * np.exp(1j * 2 * np.pi * 0.031 * t)
    noise = 0.01 * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    x = tone + noise
    i = np.clip(np.real(x), -1.0, 1.0)
    q = np.clip(np.imag(x), -1.0, 1.0)
    return i + 1j * q


def run_self_test() -> dict:
    """Sweep synthetic gain points and confirm clipping/overload tracks amplitude."""
    sim_gains_db = [-20.0, -10.0, 0.0, 20.0, 30.0, 34.0]
    rows: list[GainPointResult] = []
    for index, gain_db in enumerate(sim_gains_db, start=1):
        x = synthetic_capture(gain_db)
        metrics = analyze_iq(x)
        rows.append(
            GainPointResult(
                test_id=f"SELFTEST-{index:03d}",
                rx_tx_path="synthetic loopback (no hardware)",
                tx_setting="n/a",
                rx_gain_db=f"sim {gain_db:.0f} dB",
                external_attenuation_db="n/a",
                notes="synthetic self-test point, not a hardware measurement",
                synthetic=True,
                **metrics,
            )
        )

    overload_flags = [row.overload for row in rows]
    passed = bool(
        overload_flags[0] is False
        and overload_flags[1] is False
        and overload_flags[-1] is True
        and rows[-1].clipping_count > 0
        and rows[0].peak_dbfs < rows[-1].peak_dbfs
    )
    return {
        "evidence_scope": "synthetic-self-test-only",
        "hardware_measurement_claimed": False,
        "rows": [asdict(row) for row in rows],
        "self_test_pass": passed,
    }


def analyze_manifest(manifest_path: Path) -> dict:
    """Analyze one real gain-sweep manifest: a JSON list of capture points.

    Each point: ``{"test_id", "rx_tx_path", "tx_setting", "rx_gain_db",
    "external_attenuation_db", "capture_path", "iq_format", "notes"}``.
    ``capture_path`` is resolved relative to the manifest file.
    """
    points = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(points, list) or not points:
        raise ValueError("manifest must be a non-empty JSON list of gain-sweep points")

    rows: list[GainPointResult] = []
    for point in points:
        capture_path = (manifest_path.parent / point["capture_path"]).resolve()
        iq_format = str(point.get("iq_format", "ci16")).lower()
        x = read_iq(capture_path, iq_format)
        metrics = analyze_iq(x)
        rows.append(
            GainPointResult(
                test_id=str(point["test_id"]),
                rx_tx_path=str(point.get("rx_tx_path", "TBD")),
                tx_setting=str(point.get("tx_setting", "TBD")),
                rx_gain_db=str(point.get("rx_gain_db", "TBD")),
                external_attenuation_db=str(point.get("external_attenuation_db", "TBD")),
                notes=str(point.get("notes", "")),
                synthetic=False,
                **metrics,
            )
        )
    return {
        "evidence_scope": "draft-from-real-capture",
        "hardware_measurement_claimed": True,
        "manifest": str(manifest_path),
        "rows": [asdict(row) for row in rows],
    }


def render_markdown_table(rows: list[dict]) -> str:
    """Rows in the exact column order of templates/ad9363-gain-overload-log.md."""
    header = (
        "| Test ID | RX/TX path | TX gain / attenuation setting | RX gain setting "
        "| External attenuation | Observed peak | SNR / EVM / BER | Clipping / overload sign "
        "| Recommended? | Notes |\n"
        "|---|---|---:|---:|---:|---:|---|---|---|---|"
    )
    lines = [header]
    for row in rows:
        overload_sign = "clipping" if row["clipping_count"] > 0 else ("marginal" if row["overload"] else "none")
        recommended = "no" if row["overload"] else "candidate"
        note = row["notes"] + (" [SYNTHETIC]" if row["synthetic"] else "")
        lines.append(
            f"| {row['test_id']} | {row['rx_tx_path']} | {row['tx_setting']} | {row['rx_gain_db']} "
            f"| {row['external_attenuation_db']} | {row['peak_dbfs']:.2f} dBFS "
            f"| SNR {row['snr_db']:.1f} dB, SFDR {row['sfdr_db']:.1f} dB | {overload_sign} | {recommended} | {note} |"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="JSON gain-sweep manifest of real captures")
    parser.add_argument("--self-test", action="store_true", help="run the no-hardware synthetic sweep")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    parser.add_argument("--markdown-output", type=Path, help="optional rendered Markdown table path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        result = run_self_test()
        rc = 0 if result["self_test_pass"] else 1
    elif args.manifest:
        result = analyze_manifest(args.manifest)
        rc = 0
    else:
        raise SystemExit("either --self-test or --manifest is required")

    table = render_markdown_table(result["rows"])
    print(table)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(table + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
