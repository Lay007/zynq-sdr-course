#!/usr/bin/env python3
"""Vectors for tb_ofdm_rx_sync_chain's self-check (issue #48 stage 4b).

One frame of tools/ofdm_rf_link.py (sync preamble + the RTL transmitter's training symbol and
DATA_SYMBOLS data symbols) through the channel model (SNR 30 dB, CFO 3 kHz at 2.083 MS/s, a
fractional delay, 12-bit), written as the received stream, plus the data bit pairs the receiver must
decide, in data-index order per symbol. Deterministic (fixed seed); requires iverilog (for the RTL
transmitter).

    python tools/generate_ofdm_sync_chain_vectors.py
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ofdm_frame_sync_fixed as F  # noqa: E402
import ofdm_rf_link as O  # noqa: E402

OUT_IQ = ROOT / "verification/vectors/block08_ofdm_sync_chain_iq.txt"
OUT_BITS = ROOT / "verification/vectors/block08_ofdm_sync_chain_bits.txt"
DATA_SYMBOLS = 4


def main() -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    rng = np.random.default_rng(2026)
    args = argparse.Namespace(data_symbols=DATA_SYMBOLS, train_symbols=1)
    with tempfile.TemporaryDirectory() as tmp:
        burst, data, start = O.make_frame(Path(tmp), rng, args)
    rx = O.channel(burst, rng, 30.0, 3000.0, 2.083e6, 0.37, 0.0, 0.0, 0.0, 3700.0)
    found = F.detect(rx)
    assert len(found) == 1 and abs(found[0] - (start + O.N - 4)) <= 4, found
    OUT_IQ.write_text("".join(f"{int(r)} {int(i)}\n" for r, i in zip(rx.real, rx.imag)))
    OUT_BITS.write_text("".join(f"{int(b)}\n" for b in data))
    print(f"wrote {len(rx)} samples and {len(data)} bit pairs; frame sync model: first symbol at {found[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
