from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_11_integrated_sdr_project"
    / "python"
    / "lab_11_38_offline_qpsk_rx.py"
)
SPEC = importlib.util.spec_from_file_location("lab_11_38_offline_qpsk_rx", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
RX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RX)


def test_self_test_finds_uncropped_frame_and_recovers_bits() -> None:
    result = RX.run_self_test()

    assert result["self_test_pass"] is True
    assert result["hardware_rx_claimed"] is False
    assert result["evidence_scope"] == "offline-reference-rx-only"
    assert result["bit_errors"] == 0
    assert result["compared_bits"] == 280
    assert result["sync_metric"] >= 0.80
    assert result["self_test_cfo_error_hz"] <= 500.0
    assert result["evm_percent"] <= 15.0


def test_frame_acquisition_is_not_tied_to_one_prefix_offset() -> None:
    for prefix in (137, 911):
        samples = RX.synthetic_reference_capture(
            prefix_samples=prefix,
            suffix_samples=500,
            cfo_hz=-22_000.0,
            phase_rad=-0.41,
            snr_db=38.0,
            seed=prefix,
        )
        result = RX.analyse_reference_capture(samples, RX.MODEL_SAMPLE_RATE_HZ)

        assert result["bit_errors"] == 0
        assert result["sync_metric"] >= 0.80
        assert abs(result["cfo_hz"] + 22_000.0) <= 500.0


def test_rational_resampler_exposes_exact_rate_ratio_and_preserves_dc() -> None:
    up, down = RX.rational_ratio(2_400_000.0, RX.MODEL_SAMPLE_RATE_HZ)
    assert (up, down) == (8, 5)

    source = np.ones(128, dtype=np.complex128) * (0.75 - 0.25j)
    resampled = RX.rational_resample(source, up, down)

    assert len(resampled) > len(source)
    interior = resampled[20:-20]
    assert np.max(np.abs(interior - (0.75 - 0.25j))) < 1e-10


def test_ci16_and_cu8_adapters_make_numerical_representation_explicit(tmp_path: Path) -> None:
    ci16_path = tmp_path / "sample.ci16"
    np.array([16384, -8192, -32768, 32767], dtype="<i2").tofile(ci16_path)
    ci16 = RX.read_iq(ci16_path, "ci16")
    np.testing.assert_allclose(
        ci16,
        np.array([0.5 - 0.25j, -1.0 + (32767 / 32768.0) * 1j]),
    )

    cu8_path = tmp_path / "sample.cu8"
    np.array([255, 128, 0, 127], dtype=np.uint8).tofile(cu8_path)
    cu8 = RX.read_iq(cu8_path, "cu8")
    np.testing.assert_allclose(
        cu8,
        np.array(
            [
                1.0 + (0.5 / 127.5) * 1j,
                -1.0 - (0.5 / 127.5) * 1j,
            ]
        ),
    )


def test_metadata_contract_rejects_sample_count_drift(tmp_path: Path) -> None:
    capture = tmp_path / "capture.ci16"
    np.array([100, -100, 200, -200], dtype="<i2").tofile(capture)
    metadata = tmp_path / "capture.json"
    metadata.write_text(
        json.dumps(
            {
                "recording_id": "unit-test",
                "sampling": {
                    "sample_rate_hz": RX.MODEL_SAMPLE_RATE_HZ,
                    "sample_count": 3,
                    "iq_format": "ci16",
                    "endianness": "little",
                    "i_first": True,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sample_count=3"):
        RX.analyse_capture_file(capture, metadata)
