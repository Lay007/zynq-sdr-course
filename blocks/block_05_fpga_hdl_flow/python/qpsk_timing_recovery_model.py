#!/usr/bin/env python3
"""Reference models for continuous QPSK Gardner timing recovery (Lab 5.13b).

The fixed-point model is the executable specification for
``qpsk_symbol_timing_recovery.v``.  Both models use two interpolated strobes per
symbol, a complex sign-Gardner detector, and a PI-controlled modulo-one NCO.
Unlike the burst phase picker, the loop can follow a non-integer and slowly
changing samples-per-symbol ratio.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


RTL = Path(__file__).resolve().parents[1] / "rtl"
SPS = 8
NCO_W = 16
NCO_ONE = 1 << NCO_W
W_NOMINAL = (2 * NCO_ONE) // SPS
# The first live A/B showed useful lock-rate improvement but excessive loop
# jitter: omega wandered by roughly +/-2.3% on a tens-of-ppm clock mismatch.
# Halving both PI terms retains the modeled pull-in range while reducing the
# symbol-to-symbol timing modulation seen by the downstream Costas loop.
K1_TERM = NCO_ONE // 512
K2_TERM = NCO_ONE // 8192
W_MIN = W_NOMINAL - 2048
W_MAX = W_NOMINAL + 2048


@dataclass(frozen=True)
class TimingResult:
    symbols: np.ndarray
    omega: np.ndarray
    errors: np.ndarray


def load_rrc_taps() -> np.ndarray:
    taps: list[int] = []
    for token in (RTL / "bpsk_rrc_tx_fir_taps.mem").read_text().split():
        value = int(token, 16)
        taps.append(value - 0x10000 if value >= 0x8000 else value)
    return np.asarray(taps, dtype=float) / 32768.0


def load_frame_dibits(n_symbols: int = 140) -> np.ndarray:
    bits = [int(token, 2) for token in (RTL / "bpsk_frame_bits.mem").read_text().split()]
    bits = np.asarray(bits[: 2 * n_symbols], dtype=np.int8)
    return bits[0::2] + 2 * bits[1::2]


def dibits_to_symbols(dibits: np.ndarray, amplitude: float = 0.82 / np.sqrt(2.0)) -> np.ndarray:
    i = np.where((dibits & 1) != 0, -amplitude, amplitude)
    q = np.where((dibits & 2) != 0, -amplitude, amplitude)
    return i + 1j * q


def tx_waveform(dibits: np.ndarray, taps: np.ndarray) -> np.ndarray:
    upsampled = np.zeros(len(dibits) * SPS, dtype=complex)
    upsampled[::SPS] = dibits_to_symbols(dibits)
    return np.convolve(upsampled, taps, mode="full")


def resample_drift(samples: np.ndarray, sps_actual: float) -> np.ndarray:
    """Resample an SPS waveform so the receiver observes ``sps_actual``."""
    step = SPS / sps_actual
    count = int((len(samples) - 2) / step)
    time = np.arange(count) * step
    base = np.floor(time).astype(int)
    fraction = time - base
    return samples[base] * (1.0 - fraction) + samples[base + 1] * fraction


def _sgn(value: float | int) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def _ted(mid: complex, current: complex, previous: complex) -> int:
    """Amplitude-independent complex sign-Gardner error in {-1, 0, +1}."""
    axis_sum = _sgn(mid.real) * _sgn(current.real - previous.real)
    axis_sum += _sgn(mid.imag) * _sgn(current.imag - previous.imag)
    return _sgn(axis_sum)


def timing_recovery_float(
    matched: np.ndarray,
    start_offset: int,
    symbol_count: int,
    *,
    k1: float = 1.0 / 512,
    k2: float = 1.0 / 8192,
) -> TimingResult:
    nco, omega, integral = 0.0, 0.25, 0.0
    previous_input = 0j
    previous_on = 0j
    middle = 0j
    parity = 0
    started = False
    input_count = 0
    symbols: list[complex] = []
    omega_trace: list[float] = []
    error_trace: list[int] = []

    for current in matched:
        if not started:
            if input_count == start_offset:
                started = True
                nco = 0.0
            else:
                input_count += 1
                previous_input = current
                continue
        if nco < omega:
            previous_omega = omega
            mu = min(nco / omega, 1.0 - 1.0 / NCO_ONE)
            interpolated = previous_input + mu * (current - previous_input)
            if parity == 0:
                error = _ted(middle, interpolated, previous_on)
                integral += k2 * error
                omega = min(max(0.25 + k1 * error + integral, 0.20), 0.30)
                previous_on = interpolated
                symbols.append(interpolated)
                omega_trace.append(omega)
                error_trace.append(error)
                if len(symbols) >= symbol_count:
                    break
            else:
                middle = interpolated
            parity ^= 1
            # The RTL's nonblocking assignments update the NCO with the old step
            # on the same edge that commits a newly filtered omega.
            nco = nco - previous_omega + 1.0
        else:
            nco -= omega
        previous_input = current

    return TimingResult(np.asarray(symbols), np.asarray(omega_trace), np.asarray(error_trace))


def timing_recovery_fixed(
    matched_i: np.ndarray,
    matched_q: np.ndarray,
    start_offset: int,
    symbol_count: int,
) -> TimingResult:
    """Integer model mirroring ``qpsk_symbol_timing_recovery.v``."""
    nco, omega, integral = 0, W_NOMINAL, 0
    previous_i = previous_q = 0
    previous_on_i = previous_on_q = 0
    middle_i = middle_q = 0
    parity = 0
    started = False
    input_count = 0
    symbols: list[complex] = []
    omega_trace: list[int] = []
    error_trace: list[int] = []

    for current_i, current_q in zip(matched_i, matched_q):
        current_i, current_q = int(current_i), int(current_q)
        if not started:
            if input_count == start_offset:
                started = True
                nco = 0
            else:
                input_count += 1
                previous_i, previous_q = current_i, current_q
                continue
        if nco < omega:
            previous_omega = omega
            mu = min(nco << 2, NCO_ONE - 1)
            interpolated_i = previous_i + ((mu * (current_i - previous_i)) >> NCO_W)
            interpolated_q = previous_q + ((mu * (current_q - previous_q)) >> NCO_W)
            if parity == 0:
                error = _ted(
                    complex(middle_i, middle_q),
                    complex(interpolated_i, interpolated_q),
                    complex(previous_on_i, previous_on_q),
                )
                integral += K2_TERM * error
                omega = max(W_MIN, min(W_MAX, W_NOMINAL + K1_TERM * error + integral))
                previous_on_i, previous_on_q = interpolated_i, interpolated_q
                symbols.append(complex(interpolated_i, interpolated_q))
                omega_trace.append(omega)
                error_trace.append(error)
                if len(symbols) >= symbol_count:
                    break
            else:
                middle_i, middle_q = interpolated_i, interpolated_q
            parity ^= 1
            nco = nco - previous_omega + NCO_ONE
        else:
            nco -= omega
        previous_i, previous_q = current_i, current_q

    return TimingResult(np.asarray(symbols), np.asarray(omega_trace), np.asarray(error_trace))


def fixed_phase_symbols(matched: np.ndarray, start_offset: int, symbol_count: int) -> np.ndarray:
    indices = start_offset + np.arange(symbol_count) * SPS
    return matched[indices[indices < len(matched)]]


def hard_dibits(symbols: np.ndarray) -> np.ndarray:
    return (symbols.real < 0).astype(np.int8) + 2 * (symbols.imag < 0).astype(np.int8)


def symbol_errors(symbols: np.ndarray, expected: np.ndarray) -> tuple[int, int]:
    """Return the best QPSK error count across the four carrier ambiguities."""
    count = min(len(symbols), len(expected))
    if count == 0:
        return len(expected), 0
    best = count
    for rotation in (1, 1j, -1, -1j):
        best = min(best, int(np.count_nonzero(hard_dibits(symbols[:count] * rotation) != expected[:count])))
    return best, count


def quantize_matched(matched: np.ndarray, amplitude: float = 0.12) -> tuple[np.ndarray, np.ndarray]:
    scaled = matched * amplitude * 32768.0
    return (
        np.clip(np.rint(scaled.real), -32768, 32767).astype(np.int64),
        np.clip(np.rint(scaled.imag), -32768, 32767).astype(np.int64),
    )


def best_errors(dibits: np.ndarray, sps_actual: float) -> tuple[int, int, int]:
    taps = load_rrc_taps()
    received = resample_drift(tx_waveform(dibits, taps), sps_actual)
    matched = np.convolve(received, taps, mode="full")
    matched_i, matched_q = quantize_matched(matched)
    best_fixed = best_float = best_phase = len(dibits)
    for offset in range(40, 130):
        fixed = timing_recovery_fixed(matched_i, matched_q, offset, len(dibits))
        floating = timing_recovery_float(matched, offset, len(dibits))
        best_fixed = min(best_fixed, symbol_errors(fixed.symbols, dibits)[0])
        best_float = min(best_float, symbol_errors(floating.symbols, dibits)[0])
        best_phase = min(
            best_phase,
            symbol_errors(fixed_phase_symbols(matched, offset, len(dibits)), dibits)[0],
        )
    return best_float, best_fixed, best_phase


def main() -> None:
    frame = load_frame_dibits()
    print("QPSK Gardner timing recovery (symbol errors, best start offset)")
    print("actual SPS | float | fixed | fixed phase")
    for actual_sps in (8.0, 8.03, 8.06, 7.97, 7.94):
        floating, fixed, phase = best_errors(frame, actual_sps)
        print(f"{actual_sps:10.3f} | {floating:5d} | {fixed:5d} | {phase:11d}")


if __name__ == "__main__":
    main()
