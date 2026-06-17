#!/usr/bin/env python3
"""Reusable signal helpers for Block 2 executable demos."""

from __future__ import annotations

import numpy as np


def make_complex_tone(
    sample_rate_hz: float,
    sample_count: int,
    tone_hz: float,
    *,
    amplitude: float = 1.0,
    phase_rad: float = 0.0,
) -> np.ndarray:
    t = np.arange(sample_count) / sample_rate_hz
    return amplitude * np.exp(1j * (2.0 * np.pi * tone_hz * t + phase_rad))


def make_real_tone(
    sample_rate_hz: float,
    sample_count: int,
    tone_hz: float,
    *,
    amplitude: float = 1.0,
    phase_rad: float = 0.0,
) -> np.ndarray:
    t = np.arange(sample_count) / sample_rate_hz
    return amplitude * np.cos(2.0 * np.pi * tone_hz * t + phase_rad)


def spectrum_db(x: np.ndarray, sample_rate_hz: float, fft_length: int = 65536) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), fft_length)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate_hz))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def estimate_peak_hz(
    x: np.ndarray,
    sample_rate_hz: float,
    *,
    fft_length: int = 65536,
    exclude_dc_hz: float = 0.0,
) -> float:
    freq, mag_db = spectrum_db(x, sample_rate_hz, fft_length)
    if exclude_dc_hz > 0.0:
        masked = np.where(np.abs(freq) < exclude_dc_hz, -1e15, mag_db)
        return float(freq[int(np.argmax(masked))])
    return float(freq[int(np.argmax(mag_db))])


def estimate_positive_peak_hz(x: np.ndarray, sample_rate_hz: float, *, fft_length: int = 65536) -> float:
    freq, mag_db = spectrum_db(x, sample_rate_hz, fft_length)
    positive = freq >= 0.0
    return float(freq[positive][int(np.argmax(mag_db[positive]))])


def estimate_negative_peak_hz(x: np.ndarray, sample_rate_hz: float, *, fft_length: int = 65536) -> float:
    freq, mag_db = spectrum_db(x, sample_rate_hz, fft_length)
    negative = freq <= 0.0
    return float(freq[negative][int(np.argmax(mag_db[negative]))])


def alias_frequency_hz(tone_hz: float, sample_rate_hz: float) -> float:
    return float(((tone_hz + 0.5 * sample_rate_hz) % sample_rate_hz) - 0.5 * sample_rate_hz)


def clipping_fraction(x: np.ndarray, limit: float = 0.999) -> float:
    return float(np.mean((np.abs(np.real(x)) > limit) | (np.abs(np.imag(x)) > limit)))


def rms_dbfs(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.abs(x) ** 2)))
    return float(20.0 * np.log10(max(rms, 1e-15)))
