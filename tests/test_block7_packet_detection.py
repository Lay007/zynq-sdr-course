from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_07_tx_rx_chains"
    / "python"
    / "lab_7_4_packet_receiver_detection.py"
)
SPEC = importlib.util.spec_from_file_location(
    "lab_7_4_packet_receiver_detection", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)


def _metric_and_truth(noise_rms: float | None = None):
    cfg = LAB.PacketConfig()
    rng = np.random.default_rng(cfg.seed)
    clean, starts, preamble = LAB.build_burst_stream(cfg, rng)
    noise = cfg.noise_rms if noise_rms is None else noise_rms
    rx = clean + noise * (
        rng.standard_normal(len(clean)) + 1j * rng.standard_normal(len(clean))
    )
    metric = LAB.detection_metric(LAB.agc_normalize(rx), preamble)
    return cfg, metric, starts


def test_metric_peaks_at_the_true_packet_start() -> None:
    _, metric, starts = _metric_and_truth()
    for start in starts:
        window = metric[start - 64 : start + 65]
        assert int(np.argmax(window)) == 64, "metric peak must sit on the true start"
        assert window.max() > 0.7


def test_default_run_detects_every_packet_with_zero_timing_error() -> None:
    cfg, metric, starts = _metric_and_truth()
    packet = (cfg.preamble_symbols + cfg.payload_symbols) * cfg.samples_per_symbol
    gap = cfg.gap_symbols * cfg.samples_per_symbol
    detected = LAB.pick_peaks(metric, cfg.threshold, min_distance=packet + gap // 2)
    metrics, timing = LAB.score_detections(
        detected, starts, cfg.tolerance_samples, len(metric)
    )
    assert (metrics.true_positives, metrics.false_positives, metrics.misses) == (
        12,
        0,
        0,
    )
    assert np.max(np.abs(timing)) == 0.0


def test_tolerance_is_tight_enough_to_catch_a_misplaced_detector() -> None:
    cfg = LAB.PacketConfig()
    assert cfg.tolerance_samples <= 4 * cfg.samples_per_symbol
    starts = np.array([1000, 5000])
    shifted = starts + 150
    metrics, _ = LAB.score_detections(shifted, starts, cfg.tolerance_samples, 10_000)
    assert metrics.true_positives == 0 and metrics.misses == 2


def test_low_threshold_produces_a_false_alarm() -> None:
    cfg, metric, starts = _metric_and_truth()
    packet = (cfg.preamble_symbols + cfg.payload_symbols) * cfg.samples_per_symbol
    gap = cfg.gap_symbols * cfg.samples_per_symbol
    detected = LAB.pick_peaks(metric, 0.10, min_distance=packet + gap // 2)
    metrics, _ = LAB.score_detections(
        detected, starts, cfg.tolerance_samples, len(metric)
    )
    assert metrics.false_positives >= 1
