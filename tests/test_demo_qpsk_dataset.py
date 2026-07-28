from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from analyze_demo_qpsk_dataset import analyze, verify_checksum  # noqa: E402
from generate_demo_qpsk_dataset import (  # noqa: E402
    AMPLITUDE,
    NUM_SYMBOLS,
    SAMPLE_RATE_HZ,
    SAMPLES_PER_SYMBOL,
    generate_qpsk_symbols,
)


def synthetic_ci16_samples() -> np.ndarray:
    symbols = generate_qpsk_symbols(NUM_SYMBOLS)
    samples = np.repeat(symbols, SAMPLES_PER_SYMBOL)
    i = np.round(np.real(samples) * AMPLITUDE).astype(np.int16)
    q = np.round(np.imag(samples) * AMPLITUDE).astype(np.int16)
    return i.astype(np.float64) + 1j * q.astype(np.float64)


def test_demo_qpsk_analysis_recovers_known_payload_without_errors() -> None:
    summary, _, _, _ = analyze(
        synthetic_ci16_samples(),
        SAMPLE_RATE_HZ,
        SAMPLES_PER_SYMBOL,
        AMPLITUDE,
    )

    assert summary["num_symbols"] == NUM_SYMBOLS
    assert summary["compared_bits"] == NUM_SYMBOLS * 2
    assert summary["symbol_errors"] == 0
    assert summary["bit_errors"] == 0
    assert summary["ser"] == 0.0
    assert summary["ber"] == 0.0
    assert summary["evm_rms_percent"] < 0.01


def test_verify_checksum_rejects_modified_payload(tmp_path: Path) -> None:
    payload = tmp_path / "fixture.ci16"
    payload.write_bytes(b"known payload")
    expected = hashlib.sha256(payload.read_bytes()).hexdigest()

    assert verify_checksum(payload, expected) == expected
    payload.write_bytes(b"modified payload")

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_checksum(payload, expected)
