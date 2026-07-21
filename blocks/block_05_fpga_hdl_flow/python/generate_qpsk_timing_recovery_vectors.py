#!/usr/bin/env python3
"""Generate deterministic vectors for the QPSK Gardner RTL regressions."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parent))
from qpsk_timing_recovery_model import (  # noqa: E402
    load_frame_dibits,
    load_rrc_taps,
    quantize_matched,
    resample_drift,
    symbol_errors,
    timing_recovery_fixed,
    tx_waveform,
)


TB = Path(__file__).resolve().parents[1] / "tb"
DRIFT_SPS = 8.06
START_OFFSET = 65
SYMBOL_COUNT = 140


def hex16(value: int) -> str:
    return f"{int(value) & 0xFFFF:04X}"


def hex_iq(i_value: int, q_value: int) -> str:
    return f"{hex16(i_value)}{hex16(q_value)}"


def main() -> None:
    dibits = load_frame_dibits(SYMBOL_COUNT)
    taps = load_rrc_taps()
    received = resample_drift(tx_waveform(dibits, taps), DRIFT_SPS)
    matched = np.convolve(received, taps, mode="full")
    matched_i, matched_q = quantize_matched(matched)
    recovered = timing_recovery_fixed(
        matched_i, matched_q, START_OFFSET, SYMBOL_COUNT
    )
    errors, count = symbol_errors(recovered.symbols, dibits)
    if count != SYMBOL_COUNT or errors != 0:
        raise RuntimeError(
            f"fixed model failed: {count}/{SYMBOL_COUNT} symbols, {errors} errors"
        )

    (TB / "qpsk_timing_recovery_mf_input.mem").write_text(
        "\n".join(hex_iq(i, q) for i, q in zip(matched_i, matched_q)) + "\n"
    )
    (TB / "qpsk_timing_recovery_expected.mem").write_text(
        "\n".join(
            hex_iq(int(symbol.real), int(symbol.imag))
            for symbol in recovered.symbols
        )
        + "\n"
    )
    (TB / "qpsk_timing_recovery_meta.txt").write_text(
        "# start_offset symbol_count n_mf drift_sps\n"
        f"{START_OFFSET} {SYMBOL_COUNT} {len(matched_i)} {DRIFT_SPS}\n"
    )

    raw_scale = 0.70 * 32768.0
    raw_i = np.clip(np.rint(received.real * raw_scale), -32768, 32767).astype(np.int64)
    raw_q = np.clip(np.rint(received.imag * raw_scale), -32768, 32767).astype(np.int64)
    raw_i = np.concatenate((raw_i, np.zeros(512, dtype=np.int64)))
    raw_q = np.concatenate((raw_q, np.zeros(512, dtype=np.int64)))
    (TB / "qpsk_chain_drift_rx.mem").write_text(
        "\n".join(hex_iq(i, q) for i, q in zip(raw_i, raw_q)) + "\n"
    )
    print(
        f"QPSK timing vectors: {len(matched_i)} MF samples, {len(raw_i)} RX samples, "
        f"SPS={DRIFT_SPS}, model errors={errors}/{2 * SYMBOL_COUNT} bits"
    )


if __name__ == "__main__":
    main()
