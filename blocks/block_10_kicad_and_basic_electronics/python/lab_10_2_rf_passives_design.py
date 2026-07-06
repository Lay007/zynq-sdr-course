#!/usr/bin/env python3
"""Calculate an RC low-pass and a matched symmetric Pi attenuator."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUT = ROOT / "docs" / "assets" / "lab102_rf_passives_metrics.json"


@dataclass(frozen=True)
class PiAttenuator:
    attenuation_db: float
    impedance_ohm: float
    voltage_ratio: float
    series_resistor_ohm: float
    shunt_resistor_ohm: float


def design_pi_attenuator(attenuation_db: float, impedance_ohm: float = 50.0) -> PiAttenuator:
    if attenuation_db <= 0:
        raise ValueError("attenuation_db must be positive")
    if impedance_ohm <= 0:
        raise ValueError("impedance_ohm must be positive")
    ratio = 10.0 ** (attenuation_db / 20.0)
    series = impedance_ohm * (ratio * ratio - 1.0) / (2.0 * ratio)
    shunt = impedance_ohm * (ratio + 1.0) / (ratio - 1.0)
    return PiAttenuator(attenuation_db, impedance_ohm, ratio, series, shunt)


def rc_lowpass_metrics(resistance_ohm: float, capacitance_f: float, frequencies_hz: list[float]) -> dict:
    if resistance_ohm <= 0 or capacitance_f <= 0:
        raise ValueError("resistance_ohm and capacitance_f must be positive")
    if any(frequency < 0 for frequency in frequencies_hz):
        raise ValueError("frequencies_hz must be non-negative")
    cutoff_hz = 1.0 / (2.0 * math.pi * resistance_ohm * capacitance_f)
    response = []
    for frequency_hz in frequencies_hz:
        magnitude = 1.0 / math.sqrt(1.0 + (frequency_hz / cutoff_hz) ** 2)
        response.append(
            {
                "frequency_hz": frequency_hz,
                "magnitude": magnitude,
                "magnitude_db": 20.0 * math.log10(magnitude),
            }
        )
    return {
        "resistance_ohm": resistance_ohm,
        "capacitance_f": capacitance_f,
        "cutoff_hz": cutoff_hz,
        "response": response,
    }


def dbm_to_loaded_rms_voltage(dbm: float, impedance_ohm: float = 50.0) -> float:
    if impedance_ohm <= 0:
        raise ValueError("impedance_ohm must be positive")
    power_w = 10.0 ** ((dbm - 30.0) / 10.0)
    return math.sqrt(power_w * impedance_ohm)


def build_payload(args: argparse.Namespace) -> dict:
    attenuator = design_pi_attenuator(args.attenuation_db, args.impedance_ohm)
    frequencies = [0.0, args.rc_reference_frequency_hz, 10.0 * args.rc_reference_frequency_hz]
    output_dbm = args.input_dbm - args.attenuation_db
    return {
        "lab": "10.2",
        "pi_attenuator": asdict(attenuator),
        "power_budget": {
            "input_dbm": args.input_dbm,
            "output_dbm_ideal": output_dbm,
            "input_loaded_vrms": dbm_to_loaded_rms_voltage(args.input_dbm, args.impedance_ohm),
            "output_loaded_vrms_ideal": dbm_to_loaded_rms_voltage(output_dbm, args.impedance_ohm),
        },
        "rc_lowpass": rc_lowpass_metrics(args.resistance_ohm, args.capacitance_f, frequencies),
        "limitations": [
            "Ideal matched-resistor model; parasitics and resistor tolerances are not included.",
            "Bench validation must verify attenuation, return loss, heating and receiver overload margin.",
        ],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attenuation-db", type=float, default=10.0)
    parser.add_argument("--impedance-ohm", type=float, default=50.0)
    parser.add_argument("--input-dbm", type=float, default=-10.0)
    parser.add_argument("--resistance-ohm", type=float, default=1_000.0)
    parser.add_argument("--capacitance-f", type=float, default=1e-9)
    parser.add_argument("--rc-reference-frequency-hz", type=float, default=100_000.0)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    payload = build_payload(args)
    output = args.json_out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Pi series resistor: {payload['pi_attenuator']['series_resistor_ohm']:.3f} ohm")
    print(f"Pi shunt resistors: {payload['pi_attenuator']['shunt_resistor_ohm']:.3f} ohm each")
    print(f"RC cutoff: {payload['rc_lowpass']['cutoff_hz']:.3f} Hz")
    print(f"JSON: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
