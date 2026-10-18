#!/usr/bin/env python3
"""Bit-exact model of rtl/ofdm_frame_sync.v (issue #48 stage 4b): find an OFDM frame in a stream.

Streaming Schmidl & Cox on 12-bit samples (the Q1.15 input shifted right by 4, as from the AD9361),
after a DC tracker (m += (x - m) >> DC_K, x - m; m kept with DC_F fraction bits). Without it a DC
offset alone makes the silence "periodic": in simulation a burst followed by silence with a 3 % DC
offset triggered a second, false frame 93 samples after the burst.

    p[n] = conj(x[n-32]) * x[n]                 P[n] = sum of the last 32 p   (window start d = n-63)
    e[n] = |x[n]|^2                              E[n] = sum of the last 64 e,  R = E >> 1
    above[n] = R > E_MIN  and  4 * |P >> S|^2 > 3 * (R >> S)^2        (M > 0.75, no division)

A run of `above` at least MIN_RUN long is the plateau of the preamble; when it ends, its centre
c = (first + last) / 2 (window starts) gives the start of the preamble body, c + CP/2, and the first
symbol after the preamble starts at c + CP/2 + 64 - BACKOFF. The model returns those first-symbol
sample indices (index of the input sample, from 0).
"""
from __future__ import annotations

import numpy as np

H, N, CP = 32, 64, 16


DC_K, DC_F = 8, 8


def dc_track(v: np.ndarray) -> np.ndarray:
    """y = x - m, m += (x - m) >> DC_K, with m held in DC_F extra fraction bits (integers throughout)."""
    m = 0
    out = np.empty_like(v)
    for k, x in enumerate(v):
        y = (int(x) << DC_F) - m
        out[k] = y >> DC_F
        m += y >> DC_K
    return out


def detect(samples_q15: np.ndarray, e_min: int = 2000, shift: int = 8, min_run: int = 8,
           backoff: int = 4) -> list[int]:
    """samples_q15: complex ints (Q1.15). Returns the first-symbol start index of every frame found."""
    xr = dc_track(np.asarray(samples_q15.real, dtype=np.int64) >> 4)
    xi = dc_track(np.asarray(samples_q15.imag, dtype=np.int64) >> 4)
    n_total = len(xr)
    # products conj(x[n-32]) * x[n] for n >= 32
    pr = np.zeros(n_total, dtype=np.int64)
    pi = np.zeros(n_total, dtype=np.int64)
    pr[H:] = xr[:-H] * xr[H:] + xi[:-H] * xi[H:]
    pi[H:] = xr[:-H] * xi[H:] - xi[:-H] * xr[H:]
    e = xr * xr + xi * xi
    # running sums exactly as the RTL keeps them: P over the last 32 products, E over the last 64 energies
    cpr, cpi, ce = np.cumsum(pr), np.cumsum(pi), np.cumsum(e)

    def window_sum(c, length, n):
        return c[n] - (c[n - length] if n >= length else 0)

    found = []
    run_start = None
    run_last = None
    for n in range(n_total):
        P_r = window_sum(cpr, H, n)
        P_i = window_sum(cpi, H, n)
        R = window_sum(ce, N, n) >> 1
        ps_r, ps_i, rs = P_r >> shift, P_i >> shift, R >> shift
        above = R > e_min and 4 * (ps_r * ps_r + ps_i * ps_i) > 3 * rs * rs
        d = n - (N - 1)                         # window start of this metric value
        if above:
            if run_start is None:
                run_start = d
            run_last = d
        elif run_start is not None:
            if run_last - run_start + 1 >= min_run:
                c = (run_start + run_last) >> 1
                found.append(c + CP // 2 + N - backoff)
            run_start = None
    return found
