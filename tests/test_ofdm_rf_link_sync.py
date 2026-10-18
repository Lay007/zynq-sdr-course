"""Frame synchronization of tools/ofdm_rf_link.py (issue #48 stage 4), without the RTL."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ofdm_rf_link as O  # noqa: E402


def _burst(rng, lead=500, symbols=8):
    """Silence, the sync preamble, random OFDM-like symbols (CP 16), silence."""
    pre = O.preamble(3700.0)
    body = []
    for _ in range(symbols):
        spec = np.zeros(O.N, complex)
        for b in O.USED:
            spec[b] = (rng.choice([-1, 1]) + 1j * rng.choice([-1, 1])) / np.sqrt(2)
        s = np.fft.ifft(spec)
        s *= 3700.0 / np.sqrt(np.mean(np.abs(s) ** 2))
        body.append(np.concatenate([s[-O.CP:], s]))
    return np.concatenate([np.zeros(lead), pre, *body, np.zeros(400)]), lead + O.CP


def test_preamble_halves_are_equal():
    pre = O.preamble(1000.0)
    assert len(pre) == O.CP + O.N
    assert np.allclose(pre[O.CP:O.CP + 32], pre[O.CP + 32:])


def test_frame_found_within_one_sample_with_cfo_and_noise():
    rng = np.random.default_rng(3)
    for lead in (300, 517, 899):
        x, true_start = _burst(rng, lead)
        y = O.channel(x, rng, 20.0, 3000.0, 2.083e6, 0.4, 0.03, 0.3, 2.0, 3700.0)
        start, peak, cfo = O.find_frame(y)
        assert abs(start - true_start) <= 1, (lead, start, true_start)
        assert peak > 0.8
        assert abs(cfo * 2.083e6 - 3000.0) < 500.0


def test_metric_is_bounded_at_the_burst_end():
    # Normalized by the energy of both halves, the metric cannot exceed 1; the textbook form,
    # normalized by the second half only, reached 594 where that half fell into the silence.
    rng = np.random.default_rng(4)
    x, _ = _burst(rng)
    y = O.channel(x, rng, 40.0, 0.0, 2.083e6, 0.0, 0.0, 0.0, 0.0, 3700.0)
    _, peak, _ = O.find_frame(y)
    assert peak <= 1.0 + 1e-9
