"""Intentionally faulty learner starting point. Copy with check.py init before editing."""

import numpy as np


def correct_cfo(rx, estimated_hz, sample_rate_hz):
    """Return complex samples after removing the supplied CFO estimate."""
    n = np.arange(len(rx))
    return rx * np.exp(1j * 2 * np.pi * estimated_hz * n / sample_rate_hz)


def decode_iq(interleaved):
    """Decode signed int16 [I0, Q0, I1, Q1, ...] to complex Q1.15 samples."""
    pairs = np.asarray(interleaved, dtype=np.float64).reshape(-1, 2)
    return (pairs[:, 1] + 1j * pairs[:, 0]) / 32768.0


def fir_q15(samples, coefficients):
    """Causal FIR, zero initial state; coefficients[0] multiplies the newest sample.

    Inputs and coefficients are signed Q1.15 integers. Round the full accumulator
    to nearest (ties toward positive infinity), then saturate to signed int16.
    Return one integer output per input sample, with no appended filter tail.
    """
    result = []
    for n in range(len(samples)):
        acc = sum(int(coefficients[k]) * int(samples[n - k])
                  for k in range(min(n + 1, len(coefficients))))
        acc = (acc + 2**31) % 2**32 - 2**31
        result.append(max(-32768, min(32767, (acc + 16384) >> 15)))
    return result
