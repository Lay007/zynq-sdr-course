from __future__ import annotations

import importlib.util
import sys
from math import pi
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "blocks" / "block_08_modulation_and_synchronization" / "python" / "qpsk_carrier_recovery.py"

spec = importlib.util.spec_from_file_location("qpsk_carrier_recovery", SCRIPT)
assert spec is not None and spec.loader is not None
LAB89 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = LAB89
spec.loader.exec_module(LAB89)


def _dibits(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2, size=(n, 2))


@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_preamble_picks_the_quarter_turn_and_scores_only_the_payload(k: int) -> None:
    dibits = _dibits(400, 1)
    rotated = LAB89.qpsk_gray_mod(dibits) * np.exp(1j * pi / 2 * k)
    payload, ber = LAB89.resolve_90deg_ambiguity(rotated, dibits)
    assert len(payload) == 400 - LAB89.PREAMBLE_SYMBOLS
    assert ber == 0.0


def test_payload_errors_are_not_hidden_by_the_rotation_choice() -> None:
    # Corrupt payload symbols only: a whole-frame min-BER choice could not hide
    # them either, but the preamble-based choice must report them.
    dibits = _dibits(400, 2)
    rx = LAB89.qpsk_gray_mod(dibits)
    rx[100:120] *= -1
    _, ber = LAB89.resolve_90deg_ambiguity(rx, dibits)
    assert ber == pytest.approx(40 / (2 * (400 - LAB89.PREAMBLE_SYMBOLS)))


def test_costas_loop_recovers_cfo_ring() -> None:
    LAB89.RNG = np.random.default_rng(3)
    dibits = _dibits(4000, 4)
    rx = LAB89.add_cfo_awgn(LAB89.qpsk_gray_mod(dibits), 0.01, 12.0)
    assert np.mean(LAB89.demod(rx) != dibits) > 0.4
    y, _ = LAB89.costas_qpsk(rx)
    assert LAB89.acquisition_symbols(y, dibits) < 500
    _, ber = LAB89.resolve_90deg_ambiguity(y[500:], dibits[500:])
    assert ber == 0.0
