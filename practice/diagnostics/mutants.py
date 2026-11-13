"""Instructor negative controls, never imported by a learner implementation."""

import numpy as np


def uncorrected_cfo(rx, estimated_hz, sample_rate_hz):
    return rx.copy()


def conjugated_iq(interleaved):
    pairs = np.asarray(interleaved, dtype=np.float64).reshape(-1, 2)
    return (pairs[:, 0] - 1j * pairs[:, 1]) / 32768.0


def fir_variant(samples, coefficients, *, shift=15, saturate=True, reverse=False):
    if reverse:
        coefficients = coefficients[::-1]
    result = []
    for n in range(len(samples)):
        acc = sum(int(coefficients[k]) * int(samples[n - k])
                  for k in range(min(n + 1, len(coefficients))))
        value = (acc + (1 << (shift - 1))) >> shift
        result.append(max(-32768, min(32767, value)) if saturate
                      else (value + 32768) % 65536 - 32768)
    return result
