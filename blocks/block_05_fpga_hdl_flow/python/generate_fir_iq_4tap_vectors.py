#!/usr/bin/env python3
"""Generate deterministic vectors for Lab 5.2 FIR IQ 4-tap RTL simulation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TB_DIR = ROOT / "blocks" / "block_05_fpga_hdl_flow" / "tb"

H = [4096, 12288, 12288, 4096]  # Q1.15: [0.125, 0.375, 0.375, 0.125]
SHIFT = 15

INPUTS = [
    (1, 32767, 0),
    (1, 0, 32767),
    (1, -32768, 0),
    (1, 8192, -8192),
    (0, 0, 0),
    (1, 1234, -5678),
    (1, -2222, 3333),
    (1, 42, -42),
    (0, 0, 0),
    (1, 16000, 8000),
]


def sat16(value: int) -> int:
    return max(-32768, min(32767, value))


def round_shift(value: int, shift: int = SHIFT) -> int:
    # Match the educational RTL model: add +0.5 LSB before arithmetic shift.
    return (value + (1 << (shift - 1))) >> shift


def main() -> None:
    TB_DIR.mkdir(parents=True, exist_ok=True)
    xi = [0, 0, 0, 0]
    xq = [0, 0, 0, 0]
    expected = []

    for valid, i_value, q_value in INPUTS:
        if valid:
            xi = [i_value] + xi[:3]
            xq = [q_value] + xq[:3]
            acc_i = sum(x * h for x, h in zip(xi, H))
            acc_q = sum(x * h for x, h in zip(xq, H))
            yi = sat16(round_shift(acc_i))
            yq = sat16(round_shift(acc_q))
            expected.append((1, yi, yq))
        else:
            expected.append((0, 0, 0))

    input_path = TB_DIR / "fir_iq_4tap_input_vectors.txt"
    expected_path = TB_DIR / "fir_iq_4tap_expected_vectors.txt"

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
