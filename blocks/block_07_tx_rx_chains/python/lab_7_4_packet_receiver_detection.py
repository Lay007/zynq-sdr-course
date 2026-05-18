#!/usr/bin/env python3
"""Lab 7.4 - Packet receiver chain and frame detection.

Synthetic burst signal with known packet starts:
  preamble + payload in AWGN channel with random packet amplitudes.

Receiver flow:
  AGC normalization -> matched-filter preamble correlation -> threshold detector.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class PacketConfig:
    sample_rate_hz: float = 1.0e6
    samples_per_symbol: int = 4
    packet_count: int = 12
    gap_symbols: int = 500
    preamble_symbols: int = 64
    payload_symbols: int = 256
    noise_rms: float = 0.22
    threshold: float = 0.20
    tolerance_samples: int = 220
    seed: int = 74


@dataclass(frozen=True)
class PacketMetrics:
    true_positives: int
    false_positives: int
    misses: int
    detection_probability: float
    miss_rate: float
    false_alarm_rate: float
    mean_timing_error_samples: float
    std_timing_error_samples: float


def bpsk(bits: np.ndarray) -> np.ndarray:
    return np.where(bits == 0, 1.0, -1.0).astype(np.float64)


def qpsk(bits: np.ndarray) -> np.ndarray:
    pairs = bits.reshape(-1, 2)
    i = np.where(pairs[:, 0] == 0, 1.0, -1.0)
    q = np.where(pairs[:, 1] == 0, 1.0, -1.0)
    return (i + 1j * q) / np.sqrt(2.0)


def upsample_rect(symbols: np.ndarray, sps: int) -> np.ndarray:
    return np.repeat(symbols, sps).astype(np.complex128)


def build_burst_stream(cfg: PacketConfig, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pre_bits = rng.integers(0, 2, size=cfg.preamble_symbols, dtype=np.uint8)
    preamble = upsample_rect(bpsk(pre_bits), cfg.samples_per_symbol)

    payload_bits = rng.integers(0, 2, size=2 * cfg.payload_symbols * cfg.packet_count, dtype=np.uint8)
    payload_symbols = qpsk(payload_bits).reshape(cfg.packet_count, cfg.payload_symbols)
    payload_samples = [upsample_rect(payload_symbols[i], cfg.samples_per_symbol) for i in range(cfg.packet_count)]

    packet_len = len(preamble) + len(payload_samples[0])
    gap_len = cfg.gap_symbols * cfg.samples_per_symbol
    total_len = cfg.packet_count * packet_len + (cfg.packet_count + 1) * gap_len
    stream = np.zeros(total_len, dtype=np.complex128)

    starts = []
    idx = gap_len
    for i in range(cfg.packet_count):
        amp = rng.uniform(0.55, 1.25)
        packet = amp * np.concatenate([preamble, payload_samples[i]])
        stream[idx : idx + packet_len] += packet
        starts.append(idx)
        idx += packet_len + gap_len

    return stream, np.array(starts, dtype=np.int64), preamble


def agc_normalize(x: np.ndarray, target_rms: float = 1.0) -> np.ndarray:
    rms = np.sqrt(np.mean(np.abs(x) ** 2))
    if rms < 1e-15:
        return x.copy()
    return x * (target_rms / rms)


def detection_metric(x: np.ndarray, preamble: np.ndarray) -> np.ndarray:
    matched = np.correlate(x, np.conj(preamble[::-1]), mode="valid")
    pre_norm = np.sqrt(np.sum(np.abs(preamble) ** 2))
    energy = np.convolve(np.abs(x) ** 2, np.ones(len(preamble)), mode="valid")
    return np.abs(matched) / np.maximum(pre_norm * np.sqrt(energy), 1e-12)


def pick_peaks(metric: np.ndarray, threshold: float, min_distance: int) -> np.ndarray:
    idx = np.where(metric >= threshold)[0]
    if len(idx) == 0:
        return np.array([], dtype=np.int64)
    peaks: list[int] = []
    last = -10**9
    for i in idx:
        if i - last < min_distance:
            if metric[i] > metric[last]:
                peaks[-1] = int(i)
                last = int(i)
            continue
        peaks.append(int(i))
        last = int(i)
    return np.array(peaks, dtype=np.int64)


def score_detections(detected: np.ndarray, truth: np.ndarray, tol: int, total_points: int) -> tuple[PacketMetrics, np.ndarray]:
    matched_truth = np.zeros(len(truth), dtype=bool)
    errors = []
    fp = 0
    tp = 0
    for d in detected:
        delta = np.abs(truth - d)
        nearest = int(np.argmin(delta))
        if delta[nearest] <= tol and not matched_truth[nearest]:
            matched_truth[nearest] = True
            tp += 1
            errors.append(float(d - truth[nearest]))
        else:
            fp += 1
    misses = int(np.sum(~matched_truth))
    timing = np.array(errors, dtype=np.float64) if errors else np.array([0.0], dtype=np.float64)
    metrics = PacketMetrics(
        true_positives=tp,
        false_positives=fp,
        misses=misses,
        detection_probability=float(tp / max(len(truth), 1)),
        miss_rate=float(misses / max(len(truth), 1)),
        false_alarm_rate=float(fp / max(total_points, 1)),
        mean_timing_error_samples=float(np.mean(timing)),
        std_timing_error_samples=float(np.std(timing)),
    )
    return metrics, timing


def save_metric_plot(path: Path, metric: np.ndarray, truth: np.ndarray, detected: np.ndarray, threshold: float) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    n = np.arange(len(metric))
    plt.figure(figsize=(8.2, 4.5))
    plt.plot(n, metric, linewidth=1.1, label="normalized preamble metric")
    plt.axhline(threshold, color="tab:red", linestyle="--", label="threshold")
    if len(truth) > 0:
        plt.scatter(truth, metric[np.clip(truth, 0, len(metric) - 1)], s=30, marker="o", label="true starts")
    if len(detected) > 0:
        plt.scatter(detected, metric[np.clip(detected, 0, len(metric) - 1)], s=30, marker="x", label="detected")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Metric")
    plt.title("Lab 7.4 - Frame detection metric")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_timeline(path: Path, x: np.ndarray, truth: np.ndarray, detected: np.ndarray) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    n = np.arange(len(x))
    plt.figure(figsize=(8.2, 4.5))
    plt.plot(n, np.abs(x), linewidth=0.8, label="|rx|")
    for t in truth:
        plt.axvline(int(t), color="tab:green", linewidth=0.8, alpha=0.5)
    for d in detected:
        plt.axvline(int(d), color="tab:orange", linewidth=0.8, alpha=0.5)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Magnitude")
    plt.title("Lab 7.4 - Packet timeline (green true, orange detected)")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    cfg = PacketConfig()
    rng = np.random.default_rng(cfg.seed)

    clean, starts, preamble = build_burst_stream(cfg, rng)
    rx = clean + cfg.noise_rms * (rng.standard_normal(len(clean)) + 1j * rng.standard_normal(len(clean)))
    rx_agc = agc_normalize(rx)

    metric = detection_metric(rx_agc, preamble)
    packet_samples = (cfg.preamble_symbols + cfg.payload_symbols) * cfg.samples_per_symbol
    gap_samples = cfg.gap_symbols * cfg.samples_per_symbol
    # Keep only one strong candidate per packet region.
    min_distance = packet_samples + gap_samples // 2
    detected = pick_peaks(metric, cfg.threshold, min_distance=min_distance)

    metrics, timing_errors = score_detections(detected, starts, cfg.tolerance_samples, len(metric))

    metric_path = ASSET_DIR / "lab74_packet_detection_metric.png"
    timeline_path = ASSET_DIR / "lab74_packet_detection_timeline.png"
    metrics_path = ASSET_DIR / "lab74_packet_receiver_metrics.json"

    save_metric_plot(metric_path, metric, starts, detected, cfg.threshold)
    save_timeline(timeline_path, rx_agc, starts, detected)
    metrics_path.write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "metrics": asdict(metrics),
                "detected_starts": detected.tolist(),
                "true_starts": starts.tolist(),
                "timing_errors_samples": timing_errors.tolist(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 7.4 - Packet receiver detection")
    print(f"True packets: {cfg.packet_count}")
    print(f"Detected candidates: {len(detected)}")
    print(
        "TP / FP / Miss: "
        f"{metrics.true_positives} / {metrics.false_positives} / {metrics.misses}"
    )
    print(
        "Detection probability / miss rate / false alarm rate: "
        f"{metrics.detection_probability:.3f} / {metrics.miss_rate:.3f} / {metrics.false_alarm_rate:.6f}"
    )
    print(
        "Timing error mean/std (samples): "
        f"{metrics.mean_timing_error_samples:.2f} / {metrics.std_timing_error_samples:.2f}"
    )
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
