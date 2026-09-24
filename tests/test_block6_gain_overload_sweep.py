from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_06_rf_frontend_and_ad9363"
    / "python"
    / "lab_6_2_gain_overload_sweep.py"
)
SPEC = importlib.util.spec_from_file_location("lab_6_2_gain_overload_sweep", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SWEEP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SWEEP  # dataclasses needs the module registered before exec
SPEC.loader.exec_module(SWEEP)


def test_self_test_sweep_detects_clipping_only_at_high_gain() -> None:
    result = SWEEP.run_self_test()

    assert result["self_test_pass"] is True
    assert result["hardware_measurement_claimed"] is False
    assert result["evidence_scope"] == "synthetic-self-test-only"

    rows = result["rows"]
    assert all(row["synthetic"] for row in rows)
    assert rows[0]["overload"] is False
    assert rows[-1]["overload"] is True
    assert rows[-1]["clipping_count"] > 0
    assert rows[0]["clipping_count"] == 0


def test_analyze_iq_flags_a_clipped_full_scale_tone() -> None:
    n = 4096
    t = np.arange(n)
    clipped = np.clip(1.4 * np.cos(2 * np.pi * 0.05 * t), -1.0, 1.0) + 1j * np.clip(
        1.4 * np.sin(2 * np.pi * 0.05 * t), -1.0, 1.0
    )
    metrics = SWEEP.analyze_iq(clipped)
    assert metrics["clipping_count"] > 0
    assert metrics["overload"] is True


def test_analyze_iq_does_not_flag_a_clean_low_level_tone() -> None:
    n = 4096
    rng = np.random.default_rng(6)
    t = np.arange(n)
    x = 0.2 * np.exp(1j * 2 * np.pi * 0.05 * t) + 0.01 * (
        rng.standard_normal(n) + 1j * rng.standard_normal(n)
    )
    metrics = SWEEP.analyze_iq(x)
    assert metrics["clipping_count"] == 0
    assert metrics["overload"] is False


def test_render_markdown_table_matches_template_columns() -> None:
    result = SWEEP.run_self_test()
    table = SWEEP.render_markdown_table(result["rows"])
    header = table.splitlines()[0]
    for column in ("Test ID", "RX/TX path", "RX gain setting", "Observed peak", "Recommended?"):
        assert column in header
    assert "[SYNTHETIC]" in table


def test_analyze_manifest_reads_a_real_capture_and_reports_it_as_such(tmp_path: Path) -> None:
    capture = tmp_path / "GAIN-001.ci16"
    rng = np.random.default_rng(11)
    n = 2048
    samples = (0.3 * rng.standard_normal(n)).astype("<i2")
    interleaved = np.empty(2 * n, dtype="<i2")
    interleaved[0::2] = samples
    interleaved[1::2] = samples
    interleaved.tofile(capture)

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "test_id": "GAIN-001",
                    "rx_tx_path": "cabled",
                    "tx_setting": "-30 dB",
                    "rx_gain_db": "10 dB",
                    "external_attenuation_db": "30",
                    "capture_path": "GAIN-001.ci16",
                    "iq_format": "ci16",
                    "notes": "unit test capture",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = SWEEP.analyze_manifest(manifest_path)
    assert result["hardware_measurement_claimed"] is True
    assert result["evidence_scope"] == "draft-from-real-capture"
    assert len(result["rows"]) == 1
    assert result["rows"][0]["synthetic"] is False
    assert result["rows"][0]["test_id"] == "GAIN-001"


def test_analyze_manifest_rejects_empty_list(tmp_path: Path) -> None:
    manifest_path = tmp_path / "empty.json"
    manifest_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        SWEEP.analyze_manifest(manifest_path)


def test_sfdr_sees_clipping_that_the_median_snr_misses() -> None:
    # Clipping puts power into a few harmonic bins. The peak-over-median SNR barely
    # notices (it even rises with the tone level); SFDR collapses.
    clean = SWEEP.analyze_iq(SWEEP.synthetic_capture(30.0))
    clipped = SWEEP.analyze_iq(SWEEP.synthetic_capture(34.0))
    assert clean["clipping_count"] == 0 and clipped["clipping_count"] > 0
    assert clipped["snr_db"] > clean["snr_db"]
    assert clipped["sfdr_db"] < clean["sfdr_db"] - 30.0
