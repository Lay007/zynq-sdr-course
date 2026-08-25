#!/usr/bin/env python3
"""Generate deterministic vectors and twiddle ROMs for the SF7 CSS detector."""

from __future__ import annotations

import random
from pathlib import Path

import css_sf7_fixed_ref as ref


ROOT = Path(__file__).resolve().parents[3]
VECTOR_DIR = (
    ROOT / "blocks" / "block_08_modulation_and_synchronization" / "tb" / "vectors"
)

CFO_CASES = [(11, -0.30), (63, -0.15), (90, 0.15), (120, 0.30)]
NOISE_SYMBOLS = [5, 42, 77, 101]
NOISE_STD = 400
NOISE_SEED = 46


def _hex16(value: int) -> str:
    return format(value & 0xFFFF, "04x")


def _write_mem(path: Path, values: list[int]) -> None:
    path.write_text("\n".join(_hex16(v) for v in values) + "\n", encoding="utf-8")


def main() -> None:
    """Write every generated input used by the self-checking RTL regression."""
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    ref_i, ref_q = ref.conj_reference_fixed()
    tw_i, tw_q = ref.twiddle_fixed()

    _write_mem(VECTOR_DIR / "css_sf7_twiddle_i_q15.hex", tw_i)
    _write_mem(VECTOR_DIR / "css_sf7_twiddle_q_q15.hex", tw_q)

    rng = random.Random(NOISE_SEED)
    samples: list[tuple[int, int]] = []
    expected: list[tuple[int, int, int]] = []

    def emit(rx_i: list[int], rx_q: list[int]) -> None:
        result = ref.detect_fixed(rx_i, rx_q, ref_i, ref_q, tw_i, tw_q)
        samples.extend(zip(rx_i, rx_q))
        expected.append(
            (result.peak_bin, result.second_bin, result.overflow_count)
        )

    for symbol in range(ref.N):
        emit(*ref.symbol_samples_fixed(symbol))

    for symbol, cfo in CFO_CASES:
        emit(*ref.symbol_samples_fixed(symbol, cfo_bins=cfo))

    for symbol in NOISE_SYMBOLS:
        rx_i, rx_q = ref.symbol_samples_fixed(symbol)
        rx_i = [
            ref._sat(value + round(rng.gauss(0, NOISE_STD)), ref.IQ_W)
            for value in rx_i
        ]
        rx_q = [
            ref._sat(value + round(rng.gauss(0, NOISE_STD)), ref.IQ_W)
            for value in rx_q
        ]
        emit(rx_i, rx_q)

    (VECTOR_DIR / "css_sf7_detector_input.txt").write_text(
        "".join(f"{i_value} {q_value}\n" for i_value, q_value in samples),
        encoding="utf-8",
    )
    (VECTOR_DIR / "css_sf7_detector_expected.txt").write_text(
        "".join(
            f"{peak} {second} {overflow}\n"
            for peak, second, overflow in expected
        ),
        encoding="utf-8",
    )
    (VECTOR_DIR / "css_sf7_detector_meta.txt").write_text(
        f"{len(expected)}\n", encoding="utf-8"
    )

    print(
        f"CSS SF7 detector vectors: {len(expected)} cases, "
        f"{len(samples)} samples, N={ref.N}"
    )


if __name__ == "__main__":
    main()
