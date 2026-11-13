"""Instructor reference for synthetic diagnostics; this is not learner completion."""

import numpy as np


def correct_cfo(rx, estimated_hz, sample_rate_hz):
    n = np.arange(len(rx))
    return rx * np.exp(-1j * 2 * np.pi * estimated_hz * n / sample_rate_hz)


def decode_iq(interleaved):
    pairs = np.asarray(interleaved, dtype=np.float64).reshape(-1, 2)
    return (pairs[:, 0] + 1j * pairs[:, 1]) / 32768.0


def fir_q15(samples, coefficients):
    result = []
    for n in range(len(samples)):
        # Python integers preserve the full sum. Four full-scale Q1.15 products
        # require 34 signed accumulator bits, before narrowing the output.
        acc = sum(int(coefficients[k]) * int(samples[n - k])
                  for k in range(min(n + 1, len(coefficients))))
        result.append(max(-32768, min(32767, (acc + 16384) >> 15)))
    return result
