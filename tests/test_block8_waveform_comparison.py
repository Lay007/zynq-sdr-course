from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = ROOT / "blocks" / "block_08_modulation_and_synchronization" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from lab_8_11_16qam_tradeoffs import demap_16qam, map_16qam  # noqa: E402
from lab_8_12_gfsk_bt_ber import (  # noqa: E402
    GfskConfig,
    discriminator_demodulate,
    gfsk_modulate,
)
from lab_8_13_dsss_processing_gain import (  # noqa: E402
    DsssConfig,
    acquisition_example,
    m_sequence,
)


def test_16qam_gray_mapper_round_trip_all_symbols() -> None:
    labels = np.arange(16, dtype=np.uint8)[:, None]
    bits = np.unpackbits(labels, axis=1)[:, -4:].reshape(-1)

    recovered = demap_16qam(map_16qam(bits))

    assert np.array_equal(recovered, bits)
    assert np.isclose(np.mean(np.abs(map_16qam(bits)) ** 2), 1.0)


def test_gfsk_has_constant_envelope_and_noiseless_decisions() -> None:
    cfg = GfskConfig()
    rng = np.random.default_rng(812)
    bits = rng.integers(0, 2, 1000, dtype=np.uint8)

    waveform = gfsk_modulate(bits, cfg, bt=0.5)
    recovered = discriminator_demodulate(waveform, cfg)
    guard = cfg.filter_span_symbols

    assert np.max(np.abs(np.abs(waveform) - 1.0)) < 1e-12
    assert np.array_equal(recovered[guard:-guard], bits[guard:-guard])


def test_dsss_m_sequence_and_acquisition() -> None:
    cfg = DsssConfig()
    code = m_sequence(cfg.lfsr_order)
    correlation, detected = acquisition_example(
        cfg, code, np.random.default_rng(cfg.seed)
    )

    assert code.size == 127
    assert np.isclose(np.mean(code * np.roll(code, 1)), -1.0 / 127.0)
    assert detected == cfg.acquisition_prefix_chips
    assert correlation[detected] > np.median(correlation) * 3.5
