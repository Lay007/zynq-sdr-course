#!/usr/bin/env python3
"""Reference models for the BPSK Gardner symbol timing-recovery loop (Lab 5.8b).

Two interchangeable models of the same loop:

  * timing_recovery_float() - readable floating-point reference,
  * timing_recovery_fixed() - bit-exact integer model that the HDL
    (blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_timing_recovery.v) ports directly,
    and that generate_bpsk_timing_recovery_vectors.py uses for the testbenches.

Both use a decrementing modulo-1 NCO (2 strobes/symbol), a linear interpolator
(mu ~= nco<<2 for the nominal step w = 2/SPS), a sign-Gardner timing-error detector
e = sgn(y_mid)*sgn(y_on[k]-y_on[k-1]) (amplitude-independent), and a PI loop filter
with power-of-two gains (k1 = 1/256, k2 = 1/4096).

Run directly for a float-vs-fixed-vs-fixed-phase comparison on a time-drifted burst
(SPS != 8): both timing-recovery models reach BER 0 while the fixed-phase decimator
of Lab 5.8 cannot follow the drift.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np

RTL = Path(__file__).resolve().parents[1] / "rtl"
SPS = 8

# Fixed-point loop constants (Q.16), shared with the HDL.
NCO_ONE = 1 << 16
W_NOMINAL = (2 * NCO_ONE) // SPS     # 16384  (2 strobes/symbol)
K1_TERM = NCO_ONE // 256             # 256    proportional |step|
K2_TERM = NCO_ONE // 4096            # 16     integral |increment|
W_MIN = W_NOMINAL - 2048
W_MAX = W_NOMINAL + 2048


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def load_frame_bits(n: int = 281) -> np.ndarray:
    vals = []
    for s in (RTL / "bpsk_frame_bits.mem").read_text().split():
        s = s.strip()
        if s:
            vals.append(int(s, 2) if set(s) <= {"0", "1"} else int(s, 16))
    return np.array(vals[:n], dtype=int)


def load_rrc_taps() -> np.ndarray:
    taps = []
    for s in (RTL / "bpsk_rrc_tx_fir_taps.mem").read_text().split():
        s = s.strip()
        if s:
            x = int(s, 16)
            taps.append(x - 0x10000 if x >= 0x8000 else x)
    return np.array(taps, dtype=float) / 32768.0


def tx_waveform(bits: np.ndarray, taps: np.ndarray, amp: float = 0.82) -> np.ndarray:
    syms = (bits * 2 - 1).astype(float) * amp     # 0 -> -1, 1 -> +1
    up = np.zeros(len(syms) * SPS)
    up[::SPS] = syms
    return np.convolve(up, taps, mode="full")


def resample_drift(x: np.ndarray, sps_actual: float) -> np.ndarray:
    """Resample x (SPS samples/symbol) so the receiver sees sps_actual samples/symbol."""
    step = SPS / sps_actual
    n = int((len(x) - 2) / step)
    t = np.arange(n) * step
    i0 = np.floor(t).astype(int)
    frac = t - i0
    return x[i0] * (1 - frac) + x[i0 + 1] * frac


def _sgn(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def ber(rec: np.ndarray, bits: np.ndarray) -> tuple[int, int]:
    """BER allowing the BPSK 180-degree ambiguity (matched in HW by the BER counter)."""
    n = min(len(rec), len(bits))
    rec, b = rec[:n], bits[:n]
    e = int(np.sum(rec != b))
    e_inv = int(np.sum((1 - rec) != b))
    return min(e, e_inv), n


# --------------------------------------------------------------------------- #
# floating-point reference
# --------------------------------------------------------------------------- #
def timing_recovery_float(mf: np.ndarray, start_offset: int, n_sym: int,
                          k1: float = 1.0 / 256, k2: float = 1.0 / 4096) -> np.ndarray:
    """Gardner timing recovery on the matched-filter output. Returns hard bits."""
    nco, w, integ = 0.0, 0.25, 0.0
    x_prev = y_on_prev = y_mid = 0.0
    parity, started, in_count, emitted = 0, False, 0, 0
    bits_out = []
    for cur in mf:
        if not started:
            if in_count == start_offset:
                started, nco = True, 0.0
            else:
                in_count += 1
                x_prev = cur
                continue
        if nco < w:
            mu = min(nco / w, 0.999985)
            y = x_prev + mu * (cur - x_prev)
            if parity == 0:
                e = _sgn(y_mid) * _sgn(y - y_on_prev)
                integ += k2 * e
                w = min(max(0.25 + k1 * e + integ, 0.20), 0.30)
                y_on_prev = y
                bits_out.append(1 if y < 0 else 0)
                emitted += 1
                if emitted >= n_sym:
                    break
            else:
                y_mid = y
            parity ^= 1
            nco = nco - w + 1.0
        else:
            nco -= w
        x_prev = cur
    return np.array(bits_out, dtype=int)


# --------------------------------------------------------------------------- #
# bit-exact fixed-point model (HDL spec)
# --------------------------------------------------------------------------- #
def timing_recovery_fixed(mf_int: np.ndarray, start_offset: int, n_sym: int) -> np.ndarray:
    """Integer model mirroring bpsk_symbol_timing_recovery.v exactly.

    mf_int: matched-filter output as 16-bit signed integers. Returns hard bits.
    """
    nco, w, integ = 0, W_NOMINAL, 0
    x_prev = y_on_prev = y_mid = 0
    parity, started, in_count, emitted = 0, False, 0, 0
    bits_out = []
    for cur in (int(v) for v in mf_int):
        if not started:
            if in_count == start_offset:
                started, nco = True, 0
            else:
                in_count += 1
                x_prev = cur
                continue
        if nco < w:
            mu = min(nco << 2, 0xFFFF)
            y = x_prev + ((mu * (cur - x_prev)) >> 16)
            if parity == 0:
                e = _sgn(y_mid) * _sgn(y - y_on_prev)
                integ += K2_TERM * e
                w = max(W_MIN, min(W_MAX, W_NOMINAL + K1_TERM * e + integ))
                y_on_prev = y
                bits_out.append(1 if y < 0 else 0)
                emitted += 1
                if emitted >= n_sym:
                    break
            else:
                y_mid = y
            parity ^= 1
            nco = nco - w + NCO_ONE
        else:
            nco -= w
        x_prev = cur
    return np.array(bits_out, dtype=int)


def fixed_phase_decimate(mf: np.ndarray, start_offset: int, n_sym: int) -> np.ndarray:
    """Lab 5.8 fixed-phase decimator (no timing recovery), for comparison."""
    idx = start_offset + np.arange(n_sym) * SPS
    idx = idx[idx < len(mf)]
    return (mf[idx] < 0).astype(int)


# --------------------------------------------------------------------------- #
# demo / comparison
# --------------------------------------------------------------------------- #
def main() -> None:
    bits = load_frame_bits(281)
    taps = load_rrc_taps()
    tx = tx_waveform(bits, taps)
    print("BPSK Gardner timing-recovery models  (float / fixed-point / fixed-phase)")
    print("drift | float TR | fixed-pt TR | fixed-phase (Lab 5.8)")
    for sps in [8.00, 8.03, 8.05, 8.08, 7.95, 7.92]:
        rx = resample_drift(tx, sps) * 0.07            # 7% full-scale, like the radio
        mf = np.convolve(rx, taps, mode="full")
        mf_int = np.clip(np.round(mf * 32768), -32768, 32767).astype(int)
        bf = bx = bp = 999
        for so in range(40, 130):
            bf = min(bf, ber(timing_recovery_float(mf, so, 281), bits)[0])
            bx = min(bx, ber(timing_recovery_fixed(mf_int, so, 281), bits)[0])
            bp = min(bp, ber(fixed_phase_decimate(mf_int, so, 281), bits)[0])
        print(f" {sps:5.2f} | {bf:8d} | {bx:11d} | {bp:d}")


if __name__ == "__main__":
    main()
