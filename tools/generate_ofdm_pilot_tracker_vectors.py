#!/usr/bin/env python3
"""Generate shared test vectors for ofdm_pilot_phase_tracker.v.

Each line of the output holds one OFDM symbol, in decimal:

    p0_re p0_im p0_ref  p1_re p1_im p1_ref  p2_re p2_im p2_ref  p3_re p3_im p3_ref
    exp_coeff_re exp_coeff_im exp_phase exp_zero_energy

Pilots are listed in the order the extractor streams them (bins 7, 21, 43, 57,
i.e. k = +7, +21, -21, -7), with the references it produces (+32767, -32768,
+32767, +32767). Expected values come from the bit-exact model in
tools/ofdm_pilot_phase_tracker_fixed.py. pytest checks that the committed file
matches the model, and the Verilog testbench checks the RTL against the file.
"""

from __future__ import annotations

import argparse
import cmath
import math
import random
from pathlib import Path

from tools.ofdm_pilot_phase_tracker_fixed import track_symbol

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "verification" / "vectors" / "block08_ofdm_pilot_tracker_vectors.txt"
STREAM_REFS = [32767, -32768, 32767, 32767]


def _clip16(value: float) -> int:
    return max(-32768, min(32767, round(value)))


def _symbol(amplitude: float, degrees: float, jitter_deg: float = 0.0, rng: random.Random | None = None):
    pilots = []
    for ref in STREAM_REFS:
        sign = 1.0 if ref >= 0 else -1.0
        extra = rng.uniform(-jitter_deg, jitter_deg) if rng else 0.0
        value = sign * amplitude * cmath.exp(1j * math.radians(degrees + extra))
        pilots.append((_clip16(value.real), _clip16(value.imag)))
    return pilots


def build_cases() -> list[list[tuple[int, int]]]:
    cases = [_symbol(12000, deg) for deg in range(-180, 180, 15)]
    cases += [_symbol(12000, deg) for deg in (-90.0, 90.0, 89.9, -89.9, 179.9, -179.9, 0.1, -0.1)]
    cases += [_symbol(amp, 37.0) for amp in (300, 3000, 20000, 32000)]
    cases.append([(0, 0)] * 4)  # zero energy -> identity coefficient
    rng = random.Random(48)
    cases += [_symbol(rng.uniform(2000, 20000), rng.uniform(-180, 180), 8.0, rng) for _ in range(12)]
    return cases


def render(cases: list[list[tuple[int, int]]]) -> str:
    lines = []
    for pilots in cases:
        result = track_symbol(pilots, STREAM_REFS)
        fields: list[int] = []
        for (re, im), ref in zip(pilots, STREAM_REFS, strict=True):
            fields += [re, im, ref]
        fields += [*result.coefficient, result.phase, int(result.zero_energy)]
        lines.append(" ".join(str(v) for v in fields))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(build_cases()), encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
