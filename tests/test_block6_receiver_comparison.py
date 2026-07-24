from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_06_rf_frontend_and_ad9363" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_6_9_compare_receivers import (  # noqa: E402
    analyze_tone,
    build_payload,
    quantize_iq,
    read_iq,
    synthetic_captures,
)


def test_quantize_iq_uses_signed_grid_and_clips() -> None:
    samples = np.array([-1.2 - 1.2j, -0.5 + 0.5j, 0.999 + 0.999j, 1.2 + 1.2j])

    quantized = quantize_iq(samples, 8)

    assert quantized.real.min() == -1.0
    assert quantized.imag.min() == -1.0
    assert quantized.real.max() == 127 / 128
    assert quantized.imag.max() == 127 / 128
    assert quantized[1].real == -0.5
    assert quantized[1].imag == 0.5


def test_read_iq_normalizes_cu8_and_12bit_ci16(tmp_path: Path) -> None:
    cu8_path = tmp_path / "rtl.cu8"
    np.array([0, 255, 128, 127], dtype=np.uint8).tofile(cu8_path)
    ci16_path = tmp_path / "ad936x.ci16"
    np.array([-2048, 2047, 1024, -1024], dtype="<i2").tofile(ci16_path)

    rtl = read_iq(cu8_path, "cu8", stored_bits=8)
    ad936x = read_iq(ci16_path, "ci16", stored_bits=12)

    assert rtl[0].real == pytest.approx(-1.0)
    assert rtl[0].imag == pytest.approx(1.0)
    assert ad936x[0].real == pytest.approx(-1.0)
    assert ad936x[0].imag == pytest.approx(2047 / 2048)
    assert ad936x[1] == pytest.approx(0.5 - 0.5j)


def test_analyze_tone_detects_frequency_and_reports_positive_dynamic_range() -> None:
    sample_rate_hz = 2_400_000.0
    tone_hz = 120_000.0
    rtl, ad936x = synthetic_captures(65_536, sample_rate_hz, tone_hz, seed=6901)

    rtl_metrics = analyze_tone(
        rtl,
        sample_rate_hz,
        tone_hz,
        analysis_bandwidth_hz=1_800_000.0,
        tone_search_span_hz=20_000.0,
        nominal_bits=8,
    )
    ad936x_metrics = analyze_tone(
        ad936x,
        sample_rate_hz,
        tone_hz,
        analysis_bandwidth_hz=1_800_000.0,
        tone_search_span_hz=20_000.0,
        nominal_bits=12,
    )

    assert abs(float(rtl_metrics["frequency_error_hz"])) < 50.0
    assert abs(float(ad936x_metrics["frequency_error_hz"])) < 50.0
    assert float(rtl_metrics["sinad_db"]) > 25.0
    assert float(ad936x_metrics["sinad_db"]) > float(rtl_metrics["sinad_db"])
    assert float(ad936x_metrics["noise_density_dbfs_hz"]) < float(rtl_metrics["noise_density_dbfs_hz"])


def test_build_payload_separates_native_and_same_resolution_comparisons() -> None:
    rtl_metrics = {"sinad_db": 30.0, "sfdr_db": 40.0, "noise_density_dbfs_hz": -100.0}
    native_metrics = {"sinad_db": 45.0, "sfdr_db": 60.0, "noise_density_dbfs_hz": -120.0}
    quantization_metrics = [
        {"bits": 8, "metrics": {"sinad_db": 35.0}},
        {"bits": 12, "metrics": {"sinad_db": 44.5}},
    ]

    payload = build_payload(
        mode="synthetic",
        rtl_metrics=rtl_metrics,
        ad936x_native_metrics=native_metrics,
        quantization_metrics=quantization_metrics,
        source={"seed": 1},
    )

    comparison = payload["comparison"]
    assert comparison["ad936x_native_minus_rtl_sinad_db"] == pytest.approx(15.0)
    assert comparison["ad936x_native_to_8bit_sinad_penalty_db"] == pytest.approx(10.0)
    assert comparison["ad936x_8bit_minus_rtl_8bit_sinad_db"] == pytest.approx(5.0)
