#!/usr/bin/env python3
"""Lab 10.5 -- Touchstone (.s1p/.s2p) marker extractor (issue #37 software infrastructure).

Reads a real NanoVNA Touchstone export and fills the "Marker values" table of
``blocks/block_10_kicad_and_basic_electronics/reports/nanovna_measurement_report_*.template.md``
(frequency, S11 dB, VSWR, S21 dB, phase) at a chosen list of marker
frequencies, by linear interpolation between the two nearest recorded points.

Evidence boundary: this script only reads/interpolates whatever Touchstone
file it is given. ``--self-test`` builds and parses a synthetic, ideal
fixed-attenuator ``.s2p`` fixture entirely in software to prove the parser and
the marker interpolation are correct; it produces no NanoVNA measurement and
must never be presented as one. Real marker rows belong in the measurement
report only once real ``.s1p``/``.s2p`` files exist (issue #37's remaining
unchecked items: real screenshots, real Touchstone/CSV, a filled report).
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


FREQ_UNIT_TO_HZ = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}
PARAMS_BY_PORTS = {1: ("S11",), 2: ("S11", "S21", "S12", "S22")}


@dataclass(frozen=True)
class TouchstoneSweep:
    frequency_hz: tuple[float, ...]
    # complex value per parameter name, one tuple per frequency point
    params: dict[str, tuple[complex, ...]]
    n_ports: int
    reference_ohm: float


def _to_complex(format_code: str, a: float, b: float) -> complex:
    if format_code == "DB":
        magnitude = 10.0 ** (a / 20.0)
        angle = math.radians(b)
        return complex(magnitude * math.cos(angle), magnitude * math.sin(angle))
    if format_code == "MA":
        angle = math.radians(b)
        return complex(a * math.cos(angle), a * math.sin(angle))
    if format_code == "RI":
        return complex(a, b)
    raise ValueError(f"unsupported Touchstone data format {format_code!r}")


def parse_touchstone(path: Path) -> TouchstoneSweep:
    """Parse a .s1p/.s2p file: comments, one ``#`` option line, data rows."""
    suffix = path.suffix.lower()
    if suffix == ".s1p":
        n_ports = 1
    elif suffix == ".s2p":
        n_ports = 2
    else:
        raise ValueError(f"expected a .s1p or .s2p file, got {path.name!r}")

    freq_scale = None
    data_format = None
    reference_ohm = 50.0
    frequencies: list[float] = []
    values: dict[str, list[complex]] = {name: [] for name in PARAMS_BY_PORTS[n_ports]}
    param_names = PARAMS_BY_PORTS[n_ports]

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("#"):
            tokens = line[1:].split()
            upper_tokens = [t.upper() for t in tokens]
            freq_scale = FREQ_UNIT_TO_HZ[upper_tokens[0]]
            data_format = upper_tokens[2]
            if "R" in upper_tokens:
                reference_ohm = float(tokens[upper_tokens.index("R") + 1])
            continue
        if freq_scale is None or data_format is None:
            raise ValueError(f"{path}: data row before the '#' option line")

        numbers = [float(tok) for tok in line.split()]
        expected = 1 + 2 * len(param_names)
        if len(numbers) != expected:
            raise ValueError(f"{path}: expected {expected} numbers per row for {n_ports} port(s), got {len(numbers)}")

        frequencies.append(numbers[0] * freq_scale)
        for index, name in enumerate(param_names):
            a, b = numbers[1 + 2 * index], numbers[2 + 2 * index]
            values[name].append(_to_complex(data_format, a, b))

    if not frequencies:
        raise ValueError(f"{path}: no data rows found")
    if any(frequencies[i] >= frequencies[i + 1] for i in range(len(frequencies) - 1)):
        raise ValueError(f"{path}: frequency column must be strictly increasing")

    return TouchstoneSweep(
        frequency_hz=tuple(frequencies),
        params={name: tuple(seq) for name, seq in values.items()},
        n_ports=n_ports,
        reference_ohm=reference_ohm,
    )


def _wrap180(degrees_value: float) -> float:
    return ((degrees_value + 180.0) % 360.0) - 180.0


def _interpolate_param(freq_hz: tuple[float, ...], values: tuple[complex, ...], target_hz: float) -> complex:
    """Interpolate magnitude and phase separately (shortest angular path).

    Linearly interpolating the raw real/imaginary parts fails whenever the
    phase turns by more than ~90 degrees between two adjacent swept points
    (any nonzero electrical delay produces this at high enough frequency
    spacing): the two vectors partially cancel, silently reporting a lower
    magnitude than either endpoint. Interpolating magnitude and (wrapped)
    phase independently avoids that cancellation and matches how S-parameter
    markers are conventionally read off a VNA trace.
    """
    if target_hz <= freq_hz[0]:
        return values[0]
    if target_hz >= freq_hz[-1]:
        return values[-1]
    for i in range(len(freq_hz) - 1):
        if freq_hz[i] <= target_hz <= freq_hz[i + 1]:
            span = freq_hz[i + 1] - freq_hz[i]
            weight = 0.0 if span == 0 else (target_hz - freq_hz[i]) / span
            mag0, mag1 = abs(values[i]), abs(values[i + 1])
            magnitude = mag0 + weight * (mag1 - mag0)
            ang0 = math.degrees(math.atan2(values[i].imag, values[i].real))
            ang1 = math.degrees(math.atan2(values[i + 1].imag, values[i + 1].real))
            angle = math.radians(ang0 + weight * _wrap180(ang1 - ang0))
            return complex(magnitude * math.cos(angle), magnitude * math.sin(angle))
    raise AssertionError("unreachable: target_hz within the swept range")


@dataclass(frozen=True)
class MarkerRow:
    frequency_hz: float
    s11_db: float
    vswr: float
    s21_db: float | None
    s21_phase_deg: float | None
    comment: str


def db_of(value: complex) -> float:
    magnitude = abs(value)
    return 20.0 * math.log10(max(magnitude, 1e-15))


def vswr_of(s11: complex) -> float:
    gamma = min(abs(s11), 0.999999)
    return (1.0 + gamma) / (1.0 - gamma)


def extract_markers(sweep: TouchstoneSweep, marker_freqs_hz: list[float], *, comment: str = "") -> list[MarkerRow]:
    """Linear interpolation in frequency; intentionally simple for a teaching tool.

    This is not a calibration-grade fit (no cubic/rational interpolation, no
    group-delay unwrap across measurement noise) -- for the smooth, densely
    swept fixtures (real NanoVNA sweeps or the synthetic self-test) that this
    lab targets, linear interpolation between adjacent points is sufficient
    and keeps the marker math auditable by hand.
    """
    rows: list[MarkerRow] = []
    for target in marker_freqs_hz:
        s11 = _interpolate_param(sweep.frequency_hz, sweep.params["S11"], target)
        s21 = None
        s21_phase = None
        if sweep.n_ports == 2:
            s21_value = _interpolate_param(sweep.frequency_hz, sweep.params["S21"], target)
            s21 = db_of(s21_value)
            s21_phase = math.degrees(math.atan2(s21_value.imag, s21_value.real))
        rows.append(
            MarkerRow(
                frequency_hz=target,
                s11_db=db_of(s11),
                vswr=vswr_of(s11),
                s21_db=s21,
                s21_phase_deg=s21_phase,
                comment=comment,
            )
        )
    return rows


def render_markdown_table(rows: list[MarkerRow]) -> str:
    """Matches the "## 4. Marker values" table in the NanoVNA report template."""
    header = "| Frequency | S11, dB | VSWR | S21, dB | Phase / delay | Comment |\n|---:|---:|---:|---:|---:|---|"
    lines = [header]
    for row in rows:
        freq_label = f"{row.frequency_hz / 1e6:.3f} MHz"
        s21_label = f"{row.s21_db:.2f}" if row.s21_db is not None else "n/a (1-port)"
        phase_label = f"{row.s21_phase_deg:.1f} deg" if row.s21_phase_deg is not None else "n/a"
        lines.append(f"| {freq_label} | {row.s11_db:.2f} | {row.vswr:.3f} | {s21_label} | {phase_label} | {row.comment} |")
    return "\n".join(lines)


def _write_synthetic_touchstone(path: Path, *, s11_db: float, s21_db: float, delay_ns: float) -> None:
    """Ideal fixed-attenuator fixture: flat S11/S21 magnitude, linear S21 phase."""
    freqs_mhz = [10.0, 100.0, 433.0, 915.0, 1000.0, 1500.0]
    lines = [
        "! synthetic self-test fixture, not a real NanoVNA export",
        "# MHZ S DB R 50",
    ]
    for f_mhz in freqs_mhz:
        phase_deg = -360.0 * (f_mhz * 1e6) * (delay_ns * 1e-9)
        phase_deg = ((phase_deg + 180.0) % 360.0) - 180.0
        lines.append(f"{f_mhz} {s11_db} 0.0 {s21_db} {phase_deg:.4f} {s21_db} {phase_deg:.4f} {s11_db} 0.0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_self_test(tmp_dir: Path) -> dict:
    fixture_path = tmp_dir / "self_test_attenuator.s2p"
    injected_s11_db = -28.0
    injected_s21_db = -9.8
    injected_delay_ns = 4.2
    _write_synthetic_touchstone(
        fixture_path, s11_db=injected_s11_db, s21_db=injected_s21_db, delay_ns=injected_delay_ns
    )

    sweep = parse_touchstone(fixture_path)
    marker_freqs_hz = [50e6, 433e6, 915e6]
    rows = extract_markers(sweep, marker_freqs_hz, comment="synthetic self-test point")

    s11_ok = all(abs(row.s11_db - injected_s11_db) < 0.05 for row in rows)
    s21_ok = all(abs(row.s21_db - injected_s21_db) < 0.05 for row in rows)
    expected_vswr = (1 + 10 ** (injected_s11_db / 20)) / (1 - 10 ** (injected_s11_db / 20))
    vswr_ok = all(abs(row.vswr - expected_vswr) < 0.01 for row in rows)

    passed = bool(s11_ok and s21_ok and vswr_ok and sweep.n_ports == 2 and len(sweep.frequency_hz) == 6)
    return {
        "evidence_scope": "synthetic-self-test-only",
        "hardware_measurement_claimed": False,
        "fixture": str(fixture_path),
        "injected_s11_db": injected_s11_db,
        "injected_s21_db": injected_s21_db,
        "markdown_table": render_markdown_table(rows),
        "self_test_pass": passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("touchstone", nargs="?", type=Path, help=".s1p/.s2p file to read")
    parser.add_argument(
        "--marker-mhz", type=float, nargs="+", help="marker frequencies in MHz, e.g. --marker-mhz 10 433 915"
    )
    parser.add_argument("--comment", default="", help="comment text applied to every marker row")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    parser.add_argument("--self-test", action="store_true", help="run the no-hardware synthetic parser proof")
    return parser.parse_args()


def main() -> int:
    import tempfile

    args = parse_args()
    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_self_test(Path(tmp))
        print(result["markdown_table"])
        rc = 0 if result["self_test_pass"] else 1
    else:
        if args.touchstone is None or not args.marker_mhz:
            raise SystemExit("both a .s1p/.s2p path and --marker-mhz are required unless --self-test is used")
        sweep = parse_touchstone(args.touchstone)
        rows = extract_markers(sweep, [f * 1e6 for f in args.marker_mhz], comment=args.comment)
        table = render_markdown_table(rows)
        print(table)
        result = {
            "evidence_scope": "draft-from-real-touchstone-file",
            "hardware_measurement_claimed": True,
            "source": str(args.touchstone),
            "markdown_table": table,
            "rows": [asdict(row) for row in rows],
        }
        rc = 0

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
