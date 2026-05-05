#!/usr/bin/env python3
"""Generate deterministic vectors for Lab 5.3 NCO IQ mixer RTL simulation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"

SHIFT = 15
PHASE_INC = 1
PHASE_MOD = 16

SIN_LUT = [
    0,
    12540,
    23170,
    30274,
    32767,
    30274,
    23170,
    12540,
    0,
    -12540,
    -23170,
    -30274,
    -32768,
    -30274,
    -23170,
    -12540,
]

INPUTS = [
    (1, 12000, 0),
    (1, 12000, 0),
    (1, 12000, 0),
    (1, 12000, 0),
    (0, 0, 0),
    (1, 8000, -4000),
    (1, -6000, 6000),
    (1, 1000, 2000),
    (1, 0, -12000),
    (0, 0, 0),
    (1, 32767, 0),
    (1, -12000, 5000),
]


def cos_lut(phase: int) -> int:
    return SIN_LUT[(phase + 4) % PHASE_MOD]


def sin_lut(phase: int) -> int:
    return SIN_LUT[phase % PHASE_MOD]


def sat16(value: int) -> int:
    return max(-32768, min(32767, value))


def round_shift(value: int, shift: int = SHIFT) -> int:
    # Match educational RTL model: add +0.5 LSB before arithmetic shift.
    return (value + (1 << (shift - 1))) >> shift


def main() -> None:
    TB_DIR.mkdir(parents=True, exist_ok=True)
    phase = 0
    expected = []

    for valid, i_value, q_value in INPUTS:
        if valid:
            c = cos_lut(phase)
            s = sin_lut(phase)
            acc_i = i_value * c - q_value * s
            acc_q = i_value * s + q_value * c
            yi = sat16(round_shift(acc_i))
            yq = sat16(round_shift(acc_q))
            expected.append((1, yi, yq))
            phase = (phase + PHASE_INC) % PHASE_MOD
        else:
            expected.append((0, 0, 0))

    input_path = TB_DIR / "nco_mixer_iq_input_vectors.txt"
    expected_path = TB_DIR / "nco_mixer_iq_expected_vectors.txt"

    with input_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for row in INPUTS:
            f.write(f"{row[0]} {row[1]} {row[2]}\n")

    with expected_path.open("w", encoding="utf-8") as f:
        f.write("# valid i q\n")
        for row in expected:
            f.write(f"{row[0]} {row[1]} {row[2]}\n")

    print(f"Wrote {input_path}")
    print(f"Wrote {expected_path}")


if __name__ == "__main__":
    main()
