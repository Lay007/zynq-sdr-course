#!/usr/bin/env python3
"""Lab 8.22 - packet-level CSS synchronization, CFO correction, and PER."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lab_8_21_css_dechirp_fft import (
    add_awgn,
    detect_symbols,
    detector_mapping,
    symbol_bank,
    upchirp,
)


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class PacketConfig:
    spreading_factor: int = 7
    bandwidth_hz: float = 125_000.0
    preamble_symbols: int = 8
    sync_word: tuple[int, int] = (18, 52)
    downchirp_symbols: int = 2
    payload_symbols: int = 16
    prefix_symbols: int = 4
    suffix_symbols: int = 2
    packets_per_point: int = 1000
    false_alarm_trials: int = 1000
    snr_db_values: tuple[float, ...] = (-15.0, -12.0, -9.0, -6.0, -3.0)
    cfo_bins: float = 1.25
    detection_threshold: float = 3.5
    sro_ppm_values: tuple[float, ...] = (0.0, 50.0, 100.0, 250.0, 500.0)
    sro_snr_db: float = -3.0
    seed: int = 822

    @property
    def chips_per_symbol(self) -> int:
        return 1 << self.spreading_factor

    @property
    def frame_symbols(self) -> int:
        return (
            self.preamble_symbols
            + len(self.sync_word)
            + self.downchirp_symbols
            + self.payload_symbols
        )


@dataclass(frozen=True)
class DecodeResult:
    detected: bool
    start_symbol: int
    timing_metric: float
    cfo_integer_bins: int
    cfo_fractional_bins: float
    cfo_estimate_bins: float
    sync_word_ok: bool
    downchirps_ok: bool
    symbol_errors_uncorrected: int
    symbol_errors_corrected: int


def build_packet(
    cfg: PacketConfig,
    bank: np.ndarray,
    reference: np.ndarray,
    payload: np.ndarray,
) -> np.ndarray:
    if payload.size != cfg.payload_symbols:
        raise ValueError(f"payload must contain {cfg.payload_symbols} symbols")
    preamble = np.tile(reference, cfg.preamble_symbols)
    sync = bank[np.asarray(cfg.sync_word)].reshape(-1)
    downchirps = np.tile(np.conj(reference), cfg.downchirp_symbols)
    return np.concatenate((preamble, sync, downchirps, bank[payload].reshape(-1)))


def apply_sample_rate_offset(x: np.ndarray, sro_ppm: float) -> np.ndarray:
    if sro_ppm == 0.0:
        return x.copy()
    source_positions = np.arange(x.size, dtype=np.float64) * (1.0 + sro_ppm * 1e-6)
    indices = np.arange(x.size, dtype=np.float64)
    real = np.interp(source_positions, indices, np.real(x), left=0.0, right=0.0)
    imag = np.interp(source_positions, indices, np.imag(x), left=0.0, right=0.0)
    return real + 1j * imag


def apply_cfo(x: np.ndarray, cfo_bins: float, n_chips: int) -> np.ndarray:
    n = np.arange(x.size, dtype=np.float64)
    return x * np.exp(1j * 2.0 * np.pi * cfo_bins * n / n_chips)


def packet_start_metrics(
    rx: np.ndarray,
    cfg: PacketConfig,
    reference: np.ndarray,
) -> np.ndarray:
    n_chips = cfg.chips_per_symbol
    symbol_count = rx.size // n_chips
    candidate_count = symbol_count - cfg.frame_symbols + 1
    metrics = np.zeros(candidate_count, dtype=np.float64)
    for start in range(candidate_count):
        candidate = rx[
            start * n_chips : (start + cfg.preamble_symbols) * n_chips
        ].reshape(cfg.preamble_symbols, n_chips)
        spectra = np.fft.fft(candidate * np.conj(reference)[None, :], axis=1)
        accumulated = np.sum(np.abs(spectra) ** 2, axis=0)
        metrics[start] = float(np.max(accumulated) / max(np.mean(accumulated), 1e-15))
    return metrics


def estimate_cfo_bins(
    preamble: np.ndarray,
    reference: np.ndarray,
) -> tuple[int, float, float]:
    dechirped = preamble * np.conj(reference)[None, :]
    spectra = np.fft.fft(dechirped, axis=1)
    peak_bin = int(np.argmax(np.sum(np.abs(spectra) ** 2, axis=0)))
    n_chips = reference.size
    integer_bins = peak_bin if peak_bin <= n_chips // 2 else peak_bin - n_chips
    coefficients = spectra[:, peak_bin]
    phase_step = np.angle(np.sum(coefficients[1:] * np.conj(coefficients[:-1])))
    fractional_bins = float(phase_step / (2.0 * np.pi))
    return integer_bins, fractional_bins, float(integer_bins + fractional_bins)


def decode_packet(
    rx: np.ndarray,
    cfg: PacketConfig,
    reference: np.ndarray,
    inverse_mapping: np.ndarray,
    payload: np.ndarray,
) -> tuple[DecodeResult, np.ndarray]:
    n_chips = cfg.chips_per_symbol
    metrics = packet_start_metrics(rx, cfg, reference)
    peak_metric = float(np.max(metrics))
    tied_starts = np.flatnonzero(np.isclose(metrics, peak_metric, rtol=1e-10))
    start = int(tied_starts[-1])
    detected = peak_metric >= cfg.detection_threshold
    if not detected:
        return (
            DecodeResult(
                detected=False,
                start_symbol=start,
                timing_metric=peak_metric,
                cfo_integer_bins=0,
                cfo_fractional_bins=0.0,
                cfo_estimate_bins=0.0,
                sync_word_ok=False,
                downchirps_ok=False,
                symbol_errors_uncorrected=cfg.payload_symbols,
                symbol_errors_corrected=cfg.payload_symbols,
            ),
            metrics,
        )

    preamble = rx[
        start * n_chips : (start + cfg.preamble_symbols) * n_chips
    ].reshape(cfg.preamble_symbols, n_chips)
    integer_cfo, fractional_cfo, cfo_estimate = estimate_cfo_bins(
        preamble, reference
    )

    n = np.arange(rx.size, dtype=np.float64)
    corrected = rx * np.exp(
        -1j * 2.0 * np.pi * cfo_estimate * n / n_chips
    )

    sync_start = start + cfg.preamble_symbols
    sync_rx = corrected[
        sync_start * n_chips : (sync_start + len(cfg.sync_word)) * n_chips
    ].reshape(len(cfg.sync_word), n_chips)
    sync_detected, _ = detect_symbols(sync_rx, reference, inverse_mapping)
    sync_word_ok = bool(
        np.array_equal(sync_detected, np.asarray(cfg.sync_word, dtype=np.int64))
    )

    down_start = sync_start + len(cfg.sync_word)
    down_rx = corrected[
        down_start * n_chips : (down_start + cfg.downchirp_symbols) * n_chips
    ].reshape(cfg.downchirp_symbols, n_chips)
    down_spectra = np.fft.fft(down_rx * reference[None, :], axis=1)
    downchirps_ok = bool(np.all(np.argmax(np.abs(down_spectra), axis=1) == 0))

    payload_start = down_start + cfg.downchirp_symbols
    payload_stop = payload_start + cfg.payload_symbols
    payload_rx = rx[
        payload_start * n_chips : payload_stop * n_chips
    ].reshape(cfg.payload_symbols, n_chips)
    payload_corrected = corrected[
        payload_start * n_chips : payload_stop * n_chips
    ].reshape(cfg.payload_symbols, n_chips)
    decoded_raw, _ = detect_symbols(payload_rx, reference, inverse_mapping)
    decoded_corrected, _ = detect_symbols(
        payload_corrected, reference, inverse_mapping
    )

    return (
        DecodeResult(
            detected=True,
            start_symbol=start,
            timing_metric=peak_metric,
            cfo_integer_bins=integer_cfo,
            cfo_fractional_bins=fractional_cfo,
            cfo_estimate_bins=cfo_estimate,
            sync_word_ok=sync_word_ok,
            downchirps_ok=downchirps_ok,
            symbol_errors_uncorrected=int(np.count_nonzero(decoded_raw != payload)),
            symbol_errors_corrected=int(
                np.count_nonzero(decoded_corrected != payload)
            ),
        ),
        metrics,
    )


def simulate_received_packet(
    cfg: PacketConfig,
    bank: np.ndarray,
    reference: np.ndarray,
    payload: np.ndarray,
    snr_db: float,
    rng: np.random.Generator,
    *,
    sro_ppm: float = 0.0,
) -> np.ndarray:
    packet = build_packet(cfg, bank, reference, payload)
    packet = apply_sample_rate_offset(packet, sro_ppm)
    total_symbols = cfg.prefix_symbols + cfg.frame_symbols + cfg.suffix_symbols
    tx = np.zeros(total_symbols * cfg.chips_per_symbol, dtype=np.complex128)
    start = cfg.prefix_symbols * cfg.chips_per_symbol
    tx[start : start + packet.size] = packet
    tx = apply_cfo(tx, cfg.cfo_bins, cfg.chips_per_symbol)
    return add_awgn(tx[None, :], snr_db, rng)[0]


def packet_sweep(
    cfg: PacketConfig,
    bank: np.ndarray,
    reference: np.ndarray,
    inverse_mapping: np.ndarray,
    rng: np.random.Generator,
) -> list[dict[str, float | int]]:
    sweep: list[dict[str, float | int]] = []
    for snr_db in cfg.snr_db_values:
        misses = 0
        raw_packet_errors = 0
        corrected_packet_errors = 0
        corrected_symbol_errors = 0
        for _ in range(cfg.packets_per_point):
            payload = rng.integers(
                0, cfg.chips_per_symbol, size=cfg.payload_symbols
            )
            rx = simulate_received_packet(
                cfg, bank, reference, payload, snr_db, rng
            )
            result, _ = decode_packet(
                rx, cfg, reference, inverse_mapping, payload
            )
            missed = (
                not result.detected
                or result.start_symbol != cfg.prefix_symbols
                or not result.sync_word_ok
                or not result.downchirps_ok
            )
            misses += int(missed)
            raw_packet_errors += int(
                missed or result.symbol_errors_uncorrected > 0
            )
            corrected_packet_errors += int(
                missed or result.symbol_errors_corrected > 0
            )
            corrected_symbol_errors += result.symbol_errors_corrected
        compared_symbols = cfg.packets_per_point * cfg.payload_symbols
        sweep.append(
            {
                "snr_db": float(snr_db),
                "packet_count": cfg.packets_per_point,
                "compared_payload_symbols": compared_symbols,
                "missed_detection_rate": float(misses / cfg.packets_per_point),
                "per_uncorrected": float(
                    raw_packet_errors / cfg.packets_per_point
                ),
                "per_corrected": float(
                    corrected_packet_errors / cfg.packets_per_point
                ),
                "ser_corrected": float(
                    corrected_symbol_errors / compared_symbols
                ),
            }
        )
    return sweep


def false_alarm_rate(
    cfg: PacketConfig,
    rng: np.random.Generator,
    reference: np.ndarray,
) -> float:
    false_alarms = 0
    sample_count = (
        cfg.prefix_symbols + cfg.frame_symbols + cfg.suffix_symbols
    ) * cfg.chips_per_symbol
    for _ in range(cfg.false_alarm_trials):
        noise = (
            rng.standard_normal(sample_count)
            + 1j * rng.standard_normal(sample_count)
        ) / np.sqrt(2.0)
        metrics = packet_start_metrics(noise, cfg, reference)
        false_alarms += int(float(np.max(metrics)) >= cfg.detection_threshold)
    return float(false_alarms / cfg.false_alarm_trials)


def sro_sweep(
    cfg: PacketConfig,
    bank: np.ndarray,
    reference: np.ndarray,
    inverse_mapping: np.ndarray,
    rng: np.random.Generator,
) -> list[dict[str, float | int]]:
    results: list[dict[str, float | int]] = []
    trial_count = 200
    for sro_ppm in cfg.sro_ppm_values:
        packet_errors_uncorrected = 0
        packet_errors_corrected = 0
        symbol_errors_uncorrected = 0
        symbol_errors_corrected = 0
        for _ in range(trial_count):
            payload = rng.integers(
                0, cfg.chips_per_symbol, size=cfg.payload_symbols
            )
            rx = simulate_received_packet(
                cfg,
                bank,
                reference,
                payload,
                cfg.sro_snr_db,
                rng,
                sro_ppm=sro_ppm,
            )
            result_uncorrected, _ = decode_packet(
                rx, cfg, reference, inverse_mapping, payload
            )
            sro_corrected_rx = apply_sample_rate_offset(rx, -sro_ppm)
            result_corrected, _ = decode_packet(
                sro_corrected_rx, cfg, reference, inverse_mapping, payload
            )
            failed_uncorrected = (
                not result_uncorrected.detected
                or result_uncorrected.start_symbol != cfg.prefix_symbols
                or not result_uncorrected.sync_word_ok
                or not result_uncorrected.downchirps_ok
                or result_uncorrected.symbol_errors_corrected > 0
            )
            failed_corrected = (
                not result_corrected.detected
                or result_corrected.start_symbol != cfg.prefix_symbols
                or not result_corrected.sync_word_ok
                or not result_corrected.downchirps_ok
                or result_corrected.symbol_errors_corrected > 0
            )
            packet_errors_uncorrected += int(failed_uncorrected)
            packet_errors_corrected += int(failed_corrected)
            symbol_errors_uncorrected += (
                result_uncorrected.symbol_errors_corrected
            )
            symbol_errors_corrected += result_corrected.symbol_errors_corrected
        results.append(
            {
                "sro_ppm": float(sro_ppm),
                "packet_count": trial_count,
                "per_uncorrected": float(
                    packet_errors_uncorrected / trial_count
                ),
                "per_corrected": float(
                    packet_errors_corrected / trial_count
                ),
                "ser_uncorrected": float(
                    symbol_errors_uncorrected
                    / (trial_count * cfg.payload_symbols)
                ),
                "ser_corrected": float(
                    symbol_errors_corrected
                    / (trial_count * cfg.payload_symbols)
                ),
            }
        )
    return results


def save_plots(
    cfg: PacketConfig,
    timing_metrics: np.ndarray,
    packet_results: list[dict[str, float | int]],
    sro_results: list[dict[str, float | int]],
) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(np.arange(timing_metrics.size), timing_metrics, marker="o")
    plt.axhline(
        cfg.detection_threshold,
        linestyle="--",
        color="tab:red",
        label="detection threshold",
    )
    plt.axvline(
        cfg.prefix_symbols,
        linestyle=":",
        color="tab:green",
        label="true packet start",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Candidate start, symbols")
    plt.ylabel("Dechirped peak / mean power")
    plt.title("Lab 8.22 - CSS packet-start timing metric")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab822_css_timing_metric.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    snr = [float(item["snr_db"]) for item in packet_results]
    floor = 0.5 / cfg.packets_per_point
    plt.semilogy(
        snr,
        [max(float(item["per_uncorrected"]), floor) for item in packet_results],
        marker="o",
        label="without synchronization/CFO correction",
    )
    plt.semilogy(
        snr,
        [max(float(item["per_corrected"]), floor) for item in packet_results],
        marker="o",
        label="packet synchronization + CFO correction",
    )
    plt.semilogy(
        snr,
        [
            max(float(item["missed_detection_rate"]), floor)
            for item in packet_results
        ],
        marker="s",
        label="missed detection",
    )
    plt.grid(True, which="both", alpha=0.35)
    plt.xlabel("SNR, dB")
    plt.ylabel("Packet probability")
    plt.title("Lab 8.22 - CSS PER and missed detection")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab822_css_per_vs_snr.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(
        [float(item["sro_ppm"]) for item in sro_results],
        [float(item["per_uncorrected"]) for item in sro_results],
        marker="o",
        label="PER without SRO correction",
    )
    plt.plot(
        [float(item["sro_ppm"]) for item in sro_results],
        [float(item["per_corrected"]) for item in sro_results],
        marker="s",
        label="PER after SRO correction",
    )
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample-rate offset, ppm")
    plt.ylabel("Error rate")
    plt.title(f"Lab 8.22 - SRO sensitivity at {cfg.sro_snr_db:.0f} dB")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_DIR / "lab822_css_sro_sensitivity.png", dpi=180)
    plt.close()


def main() -> None:
    cfg = PacketConfig()
    rng = np.random.default_rng(cfg.seed)
    reference = upchirp(cfg.chips_per_symbol)
    bank = symbol_bank(cfg.chips_per_symbol)
    _, inverse_mapping = detector_mapping(bank, reference)

    example_payload = np.arange(cfg.payload_symbols, dtype=np.int64) * 7
    example_rx = simulate_received_packet(
        cfg, bank, reference, example_payload, -6.0, rng
    )
    example, timing_metrics = decode_packet(
        example_rx, cfg, reference, inverse_mapping, example_payload
    )

    packet_results = packet_sweep(
        cfg, bank, reference, inverse_mapping, rng
    )
    false_alarm = false_alarm_rate(cfg, rng, reference)
    sro_results = sro_sweep(
        cfg, bank, reference, inverse_mapping, rng
    )

    reference_point = next(
        item for item in packet_results if item["snr_db"] == -6.0
    )
    metrics = {
        "packets_per_snr_point": cfg.packets_per_point,
        "false_alarm_trials": cfg.false_alarm_trials,
        "false_alarm_rate": false_alarm,
        "example_start_symbol": example.start_symbol,
        "example_timing_metric": example.timing_metric,
        "example_sync_word_ok": example.sync_word_ok,
        "example_downchirps_ok": example.downchirps_ok,
        "example_cfo_true_bins": cfg.cfo_bins,
        "example_cfo_estimate_bins": example.cfo_estimate_bins,
        "example_cfo_error_bins": example.cfo_estimate_bins - cfg.cfo_bins,
        "reference_snr_db": -6.0,
        "reference_per_uncorrected": reference_point["per_uncorrected"],
        "reference_per_corrected": reference_point["per_corrected"],
        "reference_ser_corrected": reference_point["ser_corrected"],
        "lowest_snr_missed_detection_rate": packet_results[0][
            "missed_detection_rate"
        ],
        "highest_snr_per_corrected": packet_results[-1]["per_corrected"],
    }

    save_plots(cfg, timing_metrics, packet_results, sro_results)
    payload = {
        "config": asdict(cfg),
        "metrics": metrics,
        "snr_sweep": packet_results,
        "sro_sweep": sro_results,
    }
    (ASSET_DIR / "lab822_css_packet_metrics.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
