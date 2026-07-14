#!/usr/bin/env python3
"""Lab 8.20 - CSS chirp waveform, symbol mapping, and time-frequency view."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class CssConfig:
    spreading_factor: int = 7
    bandwidth_hz: float = 125_000.0
    sample_rate_hz: float = 125_000.0
    symbol_index: int = 37

    @property
    def chips_per_symbol(self) -> int:
        return 1 << self.spreading_factor

    @property
    def samples_per_symbol(self) -> int:
        ratio = self.sample_rate_hz / self.bandwidth_hz
        value = self.chips_per_symbol * ratio
        if not np.isclose(value, round(value)):
            raise ValueError(
                "sample_rate_hz / bandwidth_hz must yield an integer "
                "samples-per-symbol value"
            )
        return int(round(value))

    @property
    def symbol_duration_s(self) -> float:
        return self.chips_per_symbol / self.bandwidth_hz


@dataclass(frozen=True)
class CssMetrics:
    chips_per_symbol: int
    samples_per_symbol: int
    symbol_duration_ms: float
    raw_upchirp_peak_bin: int
    dechirped_symbol_peak_bin: int
    dechirped_peak_to_second_db: float
    constant_envelope_error: float


def css_upchirp(cfg: CssConfig) -> np.ndarray:
    """Create one periodic complex baseband upchirp."""
    n = np.arange(cfg.samples_per_symbol, dtype=np.float64)
    t = n / cfg.sample_rate_hz
    phase_cycles = (
        -0.5 * cfg.bandwidth_hz * t
        + 0.5 * (cfg.bandwidth_hz / cfg.symbol_duration_s) * t**2
    )
    return np.exp(1j * 2.0 * np.pi * phase_cycles)


def css_symbol(cfg: CssConfig, symbol_index: int) -> np.ndarray:
    """Map a symbol to a cyclic shift of the reference upchirp."""
    if not 0 <= symbol_index < cfg.chips_per_symbol:
        raise ValueError("symbol_index must be in [0, 2**SF)")
    samples_per_chip = cfg.samples_per_symbol // cfg.chips_per_symbol
    return np.roll(css_upchirp(cfg), -symbol_index * samples_per_chip)


def peak_to_second_db(spectrum: np.ndarray) -> float:
    power = np.abs(spectrum) ** 2
    if len(power) < 2:
        return float("inf")
    order = np.partition(power, -2)
    peak = float(order[-1])
    second = float(order[-2])
    return 10.0 * np.log10(max(peak, 1e-15) / max(second, 1e-15))


def short_time_spectrum(
    x: np.ndarray, nfft: int = 32, hop: int = 4
) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(nfft)
    frames = []
    centers = []
    for start in range(0, len(x) - nfft + 1, hop):
        frame = x[start : start + nfft] * window
        frames.append(np.fft.fftshift(np.fft.fft(frame, nfft)))
        centers.append(start + nfft / 2)
    return np.asarray(frames).T, np.asarray(centers)


def main() -> None:
    cfg = CssConfig()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    upchirp = css_upchirp(cfg)
    symbol = css_symbol(cfg, cfg.symbol_index)
    dechirped = symbol * np.conj(upchirp)

    raw_fft = np.fft.fft(upchirp)
    dechirped_fft = np.fft.fft(dechirped)
    raw_peak = int(np.argmax(np.abs(raw_fft)))
    detected_peak = int(np.argmax(np.abs(dechirped_fft)))

    metrics = CssMetrics(
        chips_per_symbol=cfg.chips_per_symbol,
        samples_per_symbol=cfg.samples_per_symbol,
        symbol_duration_ms=1e3 * cfg.symbol_duration_s,
        raw_upchirp_peak_bin=raw_peak,
        dechirped_symbol_peak_bin=detected_peak,
        dechirped_peak_to_second_db=peak_to_second_db(dechirped_fft),
        constant_envelope_error=float(np.max(np.abs(np.abs(symbol) - 1.0))),
    )

    time_ms = 1e3 * np.arange(cfg.samples_per_symbol) / cfg.sample_rate_hz
    instantaneous_frequency = (
        np.diff(np.unwrap(np.angle(upchirp)))
        * cfg.sample_rate_hz
        / (2.0 * np.pi)
    )

    plt.figure(figsize=(8.0, 4.4))
    plt.plot(time_ms[:-1], instantaneous_frequency / 1e3, linewidth=1.1)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Time, ms")
    plt.ylabel("Instantaneous frequency, kHz")
    plt.title("Lab 8.20 - CSS reference upchirp")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab820_css_upchirp_frequency.png", dpi=180)
    plt.close()

    stft, centers = short_time_spectrum(symbol)
    freq_khz = (
        np.fft.fftshift(np.fft.fftfreq(stft.shape[0], d=1.0 / cfg.sample_rate_hz))
        / 1e3
    )
    plt.figure(figsize=(8.0, 4.4))
    plt.imshow(
        20.0 * np.log10(np.maximum(np.abs(stft), 1e-8)),
        origin="lower",
        aspect="auto",
        extent=[
            1e3 * centers[0] / cfg.sample_rate_hz,
            1e3 * centers[-1] / cfg.sample_rate_hz,
            freq_khz[0],
            freq_khz[-1],
        ],
    )
    plt.xlabel("Time, ms")
    plt.ylabel("Frequency, kHz")
    plt.title(f"Lab 8.20 - CSS symbol {cfg.symbol_index} time-frequency view")
    plt.colorbar(label="Magnitude, dB")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab820_css_symbol_spectrogram.png", dpi=180)
    plt.close()

    bins = np.arange(cfg.chips_per_symbol)
    plt.figure(figsize=(8.0, 4.4))
    plt.plot(
        bins,
        20.0 * np.log10(np.maximum(np.abs(dechirped_fft), 1e-12)),
        linewidth=1.0,
    )
    plt.axvline(detected_peak, linestyle="--", label=f"peak bin = {detected_peak}")
    plt.grid(True, alpha=0.35)
    plt.xlabel("FFT bin")
    plt.ylabel("Magnitude, dB")
    plt.title("Lab 8.20 - Dechirped CSS symbol")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab820_css_dechirped_fft.png", dpi=180)
    plt.close()

    (ASSET_DIR / "lab820_css_metrics.json").write_text(
        json.dumps({"config": asdict(cfg), "metrics": asdict(metrics)}, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(asdict(metrics), indent=2))


if __name__ == "__main__":
    main()
