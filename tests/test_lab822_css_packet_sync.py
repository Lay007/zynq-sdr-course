from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "blocks" / "block_08_modulation_and_synchronization" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from lab_8_21_css_dechirp_fft import (  # noqa: E402
    detector_mapping,
    symbol_bank,
    upchirp,
)
from lab_8_22_css_packet_sync_per import (  # noqa: E402
    PacketConfig,
    apply_cfo,
    build_packet,
    decode_packet,
    packet_start_metrics,
)


def detector_fixture() -> tuple[PacketConfig, np.ndarray, np.ndarray, np.ndarray]:
    cfg = PacketConfig()
    reference = upchirp(cfg.chips_per_symbol)
    bank = symbol_bank(cfg.chips_per_symbol)
    _, inverse_mapping = detector_mapping(bank, reference)
    return cfg, reference, bank, inverse_mapping


def test_noiseless_packet_sync_recovers_start_cfo_and_payload() -> None:
    cfg, reference, bank, inverse_mapping = detector_fixture()
    payload = np.arange(cfg.payload_symbols, dtype=np.int64) * 7
    packet = build_packet(cfg, bank, reference, payload)
    rx = np.zeros(
        (cfg.prefix_symbols + cfg.frame_symbols + cfg.suffix_symbols)
        * cfg.chips_per_symbol,
        dtype=np.complex128,
    )
    start = cfg.prefix_symbols * cfg.chips_per_symbol
    rx[start : start + packet.size] = packet
    rx = apply_cfo(rx, cfg.cfo_bins, cfg.chips_per_symbol)

    result, _ = decode_packet(rx, cfg, reference, inverse_mapping, payload)

    assert result.detected
    assert result.start_symbol == cfg.prefix_symbols
    assert abs(result.cfo_estimate_bins - cfg.cfo_bins) < 1e-9
    assert result.sync_word_ok
    assert result.downchirps_ok
    assert result.symbol_errors_uncorrected == cfg.payload_symbols
    assert result.symbol_errors_corrected == 0


def test_noise_only_window_stays_below_detection_threshold() -> None:
    cfg, reference, _, _ = detector_fixture()
    rng = np.random.default_rng(822)
    sample_count = (
        cfg.prefix_symbols + cfg.frame_symbols + cfg.suffix_symbols
    ) * cfg.chips_per_symbol
    noise = (
        rng.standard_normal(sample_count) + 1j * rng.standard_normal(sample_count)
    ) / np.sqrt(2.0)

    metrics = packet_start_metrics(noise, cfg, reference)

    assert float(np.max(metrics)) < cfg.detection_threshold
