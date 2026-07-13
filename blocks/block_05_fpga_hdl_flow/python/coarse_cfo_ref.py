#!/usr/bin/env python3
"""Reference model for a feedforward coarse-CFO estimator, fixed-point-faithful.

Two boards have independent references, so the received carrier sits tens of kHz off. A
Costas loop cannot ACQUIRE that -- its pull-in is a few hundred Hz -- so a wide, feedforward
estimate has to remove the bulk first and hand the Costas a few-hundred-Hz residual.

Method: the 4th-power estimator of Lab 8.1, in streaming differential form so it maps to RTL.

  y[n] = a[n]*exp(j(w*n + phi)),  a[n] in QPSK -> a[n]^4 = exp(j*pi) = -1 (modulation stripped)
  y[n]^4 = -exp(j(4*w*n + 4*phi))
  d = sum_n  y[n]^4 * conj(y[n-1]^4) = sum_n exp(j*4*w)      (the per-symbol term is constant)
  angle(d) = 4*w  (mod 2*pi)   ->   w = angle(d)/4

w is the per-symbol phase increment; unambiguous for 4w in (-pi,pi] i.e. w in (-pi/4, pi/4],
which is +-1/8 cycle/symbol = +-60 kHz at 480 kSym/s. Comfortably covers the 25-30 kHz an
independent pair of AD9361s produces.

This file proves three things before any RTL is written:
  1) the float method recovers a swept CFO;
  2) the same thing works when y^4 is computed with the bit-shifts an FPGA would use (angle
     is scale-invariant, so truncating after each square is harmless);
  3) an EXACT integer CORDIC for the angle matches, so the RTL can use it and stay bit-exact.
"""
from __future__ import annotations

import numpy as np

SPS_SYMS_RATE = 480_000.0        # symbol rate at the shipped config (3.84 MHz / 8)
PHASE_W = 24                     # NCO accumulator width, full scale 2^PHASE_W = 2*pi (matches Costas)


# ---------------------------------------------------------------------------
# float method (the truth we validate against; identical maths to Lab 8.1)
# ---------------------------------------------------------------------------
def cfo_4th_float(sym: np.ndarray) -> float:
    """Per-symbol phase increment w (rad/symbol) from the differential 4th power."""
    y4 = sym ** 4
    d = np.sum(y4[1:] * np.conj(y4[:-1]))
    return float(np.angle(d) / 4.0)


# ---------------------------------------------------------------------------
# exact integer CORDIC vectoring -> atan2, so the RTL can match bit for bit
# ---------------------------------------------------------------------------
def _cordic_gain_table(n_iter: int) -> list[int]:
    # atan(2^-i) scaled to the PHASE_W circle (2^PHASE_W == 2*pi)
    return [int(round(np.arctan2(1.0, float(1 << i)) / (2.0 * np.pi) * (1 << PHASE_W)))
            for i in range(n_iter)]


_CORDIC_N = 20
_CORDIC_ATAN = _cordic_gain_table(_CORDIC_N)


def cordic_atan2(y: int, x: int) -> int:
    """Angle of (x + j y) in PHASE_W phase units, exact integer CORDIC.
    Result in (-2^(PHASE_W-1), 2^(PHASE_W-1)] == (-pi, pi]."""
    HALF = 1 << (PHASE_W - 1)          # pi
    angle = 0
    # fold to the right half-plane so the rotation converges; track the quadrant
    if x < 0:
        if y >= 0:
            x, y = y, -x
            angle += HALF // 2         # +pi/2
        else:
            x, y = -y, x
            angle -= HALF // 2         # -pi/2
    for i in range(_CORDIC_N):
        if y > 0:
            x, y = x + (y >> i), y - (x >> i)
            angle += _CORDIC_ATAN[i]
        elif y < 0:
            x, y = x - (y >> i), y + (x >> i)
            angle -= _CORDIC_ATAN[i]
    # wrap into (-pi, pi]
    if angle > HALF:
        angle -= (1 << PHASE_W)
    elif angle <= -HALF:
        angle += (1 << PHASE_W)
    return angle


# ---------------------------------------------------------------------------
# fixed-point streaming estimate, exactly what the RTL will compute
# ---------------------------------------------------------------------------
def cfo_4th_fixed(sym: np.ndarray, win: int, sq_shift: int = 15, amp: float = 32767.0) -> tuple[int, int, int]:
    """Return (omega_phase_units, acc_i, acc_q) over the first `win` symbols.
    `omega` is the per-symbol increment as a signed PHASE_W value (full scale 2*pi).

    `sq_shift` must track the input magnitude: each square multiplies magnitude, so to keep
    y2, y4 in the same range as the input the shift is ~log2(|sym|). At Q15 full scale
    (|sym|~32767) that is 15; for the raw matched-filter symbols on hardware (|sym|~2000) it
    is ~11. `amp` only scales the float input into integers for the model -- angle is
    scale-invariant, so what matters is that sq_shift matches the resulting integer range."""
    si = np.round(np.real(sym) * amp).astype(np.int64)
    sq = np.round(np.imag(sym) * amp).astype(np.int64)

    def sq_complex(i, q):
        # (i+jq)^2 = (i^2 - q^2) + j 2iq, then shift to keep it ~16-bit (angle is scale-free)
        return ((i * i - q * q) >> sq_shift), ((2 * i * q) >> sq_shift)

    acc_i = 0
    acc_q = 0
    y4p_i = y4p_q = None
    for n in range(win):
        y2i, y2q = sq_complex(si[n], sq[n])
        y4i, y4q = sq_complex(y2i, y2q)
        if y4p_i is not None:
            # y4 * conj(y4_prev)
            acc_i += y4i * y4p_i + y4q * y4p_q
            acc_q += y4q * y4p_i - y4i * y4p_q
        y4p_i, y4p_q = y4i, y4q
    omega4 = cordic_atan2(int(acc_q), int(acc_i))       # = 4*w
    # divide by 4 with sign (arithmetic shift)
    omega = omega4 >> 2
    return omega, int(acc_i), int(acc_q)


def phase_units_to_hz(omega: int) -> float:
    frac = omega / (1 << PHASE_W)          # cycles per symbol
    return frac * SPS_SYMS_RATE


# ---------------------------------------------------------------------------
# NCO derotate with the same Q15 LUT the Costas uses (256 entries)
# ---------------------------------------------------------------------------
def derotate_fixed(sym: np.ndarray, omega: int) -> np.ndarray:
    out = np.empty_like(sym)
    theta = 0
    lut_cos = np.array([int(round(32767 * np.cos(2 * np.pi * k / 256))) for k in range(256)])
    lut_sin = np.array([int(round(32767 * np.sin(2 * np.pi * k / 256))) for k in range(256)])
    for n in range(len(sym)):
        idx = ((-theta) >> (PHASE_W - 8)) & 0xFF     # top 8 bits of -theta
        c = lut_cos[idx]
        s = lut_sin[idx]
        i = int(round(np.real(sym[n]) * 32767))
        q = int(round(np.imag(sym[n]) * 32767))
        yi = (i * c - q * s) >> 15
        yq = (i * s + q * c) >> 15
        out[n] = (yi + 1j * yq) / 32767.0
        theta = (theta + omega) & ((1 << PHASE_W) - 1)
    return out


def _qpsk(nsym, cfo_hz, phi, snr_db, seed):
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, 2 * nsym)
    i = np.where(bits[0::2] == 0, 1.0, -1.0)
    q = np.where(bits[1::2] == 0, 1.0, -1.0)
    tx = (i + 1j * q) / np.sqrt(2)
    n = np.arange(nsym)
    w = 2 * np.pi * cfo_hz / SPS_SYMS_RATE
    rx = tx * np.exp(1j * (w * n + phi))
    if snr_db is not None:
        sigma = np.sqrt(0.5 * 10 ** (-snr_db / 10))
        rx += sigma * (rng.standard_normal(nsym) + 1j * rng.standard_normal(nsym))
    return tx, rx, bits


def main():
    print("=== float method: CFO sweep, 140-symbol burst, ~20 dB SNR ===")
    win = 128
    for cfo in (-30000, -18000, -5000, 0, 7000, 22000, 30000):
        _, rx, _ = _qpsk(140, cfo, 0.6, 20, seed=cfo & 0xffff)
        w = cfo_4th_float(rx[:win])
        est = w / (2 * np.pi) * SPS_SYMS_RATE
        print(f"  true {cfo:+7d} Hz   est {est:+9.1f} Hz   err {est-cfo:+7.1f} Hz")

    print("\n=== fixed-point streaming + integer CORDIC vs float ===")
    for cfo in (-30000, -12000, 0, 15000, 30000):
        _, rx, _ = _qpsk(140, cfo, 0.6, 20, seed=(cfo & 0xffff) ^ 0x55)
        wf = cfo_4th_float(rx[:win]) / (2 * np.pi) * SPS_SYMS_RATE
        omega, ai, aq = cfo_4th_fixed(rx, win)
        wfix = phase_units_to_hz(omega)
        print(f"  true {cfo:+7d}   float {wf:+9.1f}   fixed {wfix:+9.1f}   d(fix-float) {wfix-wf:+6.1f} Hz")

    print("\n=== end to end: estimate -> derotate -> residual CFO (what the Costas then sees) ===")
    for cfo in (-30000, -20000, 20000, 30000):
        _, rx, _ = _qpsk(140, cfo, 0.6, 25, seed=(cfo & 0xffff) ^ 0xAA)
        omega, _, _ = cfo_4th_fixed(rx, win)
        corr = derotate_fixed(rx, omega)
        resid = cfo_4th_float(corr[:win]) / (2 * np.pi) * SPS_SYMS_RATE
        print(f"  true {cfo:+7d} Hz   residual after derotate {resid:+7.1f} Hz   "
              f"({'Costas can track' if abs(resid) < 2000 else 'STILL TOO BIG'})")

    print("\n=== HARDWARE-SCALE amplitude (|sym|~2000, not Q15) -- pick the square-shift ===")
    # The matched-filter symbols on silicon are ~+-2000, not +-32767. sq_shift=15 underflows
    # the 4th power to zero; the shift must be ~log2(|sym|). Sweep it.
    AMP_HW = 2000.0
    for sh in (9, 10, 11, 12, 13, 15):
        errs = []
        for cfo in (-30000, -12000, 0, 15000, 30000):
            _, rx, _ = _qpsk(140, cfo, 0.6, 20, seed=(cfo & 0xffff) ^ 0x33)
            omega, ai, aq = cfo_4th_fixed(rx, win, sq_shift=sh, amp=AMP_HW)
            est = phase_units_to_hz(omega)
            errs.append(abs(est - cfo) if abs(ai) + abs(aq) > 0 else 9e9)
        worst = max(errs)
        note = "DEAD (underflow)" if worst > 1e6 else f"worst err {worst:5.0f} Hz"
        print(f"  sq_shift={sh:2d}  {note}")

    print("\n=== window length vs estimate error (amp~2000, shift=11) -- sets the delay-line depth ===")
    for win_len in (32, 48, 64, 96, 128):
        errs = []
        for cfo in (-30000, -18000, -5000, 8000, 22000, 30000):
            for sd in range(3):
                _, rx, _ = _qpsk(140, cfo, 0.6, 20, seed=(cfo & 0xffff) ^ (sd * 0x9e37))
                omega, _, _ = cfo_4th_fixed(rx, win_len, sq_shift=11, amp=2000.0)
                errs.append(abs(phase_units_to_hz(omega) - cfo))
        print(f"  window={win_len:3d} symbols   mean err {np.mean(errs):5.0f} Hz   worst {np.max(errs):5.0f} Hz "
              f"({'Costas-trackable' if np.max(errs) < 2000 else 'too noisy'})")


if __name__ == "__main__":
    main()
