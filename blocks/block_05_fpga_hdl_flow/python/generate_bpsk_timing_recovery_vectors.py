#!/usr/bin/env python3
"""Generate vectors for the BPSK Gardner timing-recovery testbenches.

Uses the shared reference model in bpsk_timing_recovery_model.py (the bit-exact
fixed-point function is the HDL spec). Emits, into the Block-5 tb dir:

  bpsk_timing_recovery_mf_input.mem       matched-filter samples (SPS=8.03 drift, hex)
  bpsk_timing_recovery_model_bits.txt     model hard decisions (bit-exact HDL target)
  bpsk_timing_recovery_expected_bits.txt  transmitted frame bits
  bpsk_timing_recovery_meta.txt           start_offset symbol_count n_mf drift
  bpsk_chain_drift_rx.mem                  pre-matched-filter RX for the full-chain tb
  bpsk_chain_drift_meta.txt               n_rx drift
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bpsk_timing_recovery_model import (  # noqa: E402
    load_frame_bits, load_rrc_taps, tx_waveform, resample_drift,
    timing_recovery_fixed, ber,
)

TB = Path(__file__).resolve().parents[1] / "tb"
DRIFT = 8.03
MODULE_START_OFFSET = 64
MODULE_AMP_FS = 0.07         # hardware-like 7% full scale
CHAIN_AMP_FS = 0.30


def to_hex16(v) -> str:
    return f"{int(v) & 0xFFFF:04X}"


def main() -> None:
    bits = load_frame_bits(281)
    taps = load_rrc_taps()
    tx = tx_waveform(bits, taps)

    # --- module-level vectors (matched-filter input) ---
    rx = resample_drift(tx, DRIFT)
    mf = np.convolve(rx, taps, mode="full") * MODULE_AMP_FS
    mf_int = np.clip(np.round(mf * 32768), -32768, 32767).astype(int)
    rec = timing_recovery_fixed(mf_int, MODULE_START_OFFSET, 281)
    assert ber(rec, bits)[0] == 0, "model not BER=0 at this start_offset; pick another"

    (TB / "bpsk_timing_recovery_mf_input.mem").write_text(
        "\n".join(to_hex16(v) for v in mf_int) + "\n")
    (TB / "bpsk_timing_recovery_model_bits.txt").write_text(
        "\n".join(str(int(b)) for b in rec[:281]) + "\n")
    (TB / "bpsk_timing_recovery_expected_bits.txt").write_text(
        "\n".join(str(int(b)) for b in bits[:281]) + "\n")
    (TB / "bpsk_timing_recovery_meta.txt").write_text(
        "# start_offset symbol_count n_mf drift_sps\n"
        f"{MODULE_START_OFFSET} 281 {len(mf_int)} {DRIFT}\n")

    # --- full-chain RX vector (pre matched-filter) ---
    rx_chain = -resample_drift(tx, DRIFT)   # inverted like the loopback testbench
    rx_int = np.clip(np.round(rx_chain * CHAIN_AMP_FS * 32768), -32768, 32767).astype(int)
    rx_int = np.concatenate([rx_int, np.zeros(64, dtype=int)])
    (TB / "bpsk_chain_drift_rx.mem").write_text(
        "\n".join(to_hex16(v) for v in rx_int) + "\n")
    (TB / "bpsk_chain_drift_meta.txt").write_text(
        f"# n_rx drift_sps\n{len(rx_int)} {DRIFT}\n")

    print(f"timing-recovery vectors: {len(mf_int)} MF samples (module), "
          f"{len(rx_int)} RX samples (chain), drift SPS={DRIFT}, model BER=0")


if __name__ == "__main__":
    main()
