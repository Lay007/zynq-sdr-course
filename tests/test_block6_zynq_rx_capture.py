from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_06_rf_frontend_and_ad9363" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_6_6_capture_zynq_rx_only import (  # noqa: E402
    build_manifest,
    sha256_file,
    write_ci16,
)


def test_write_ci16_interleaves_i_and_q(tmp_path: Path) -> None:
    path = tmp_path / "capture.ci16"
    i_samples = np.array([1, -2, 3], dtype=np.int16)
    q_samples = np.array([4, -5, 6], dtype=np.int16)

    write_ci16(path, i_samples, q_samples)
    raw = np.fromfile(path, dtype="<i2")

    assert raw.tolist() == [1, 4, -2, -5, 3, 6]


def test_build_manifest_uses_relative_file_name_and_analysis_command(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    raw_dir = dataset_dir / "raw"
    raw_dir.mkdir(parents=True)
    iq_path = raw_dir / "capture.ci16"
    iq_path.write_bytes(b"\x01\x00\x02\x00")
    manifest_path = dataset_dir / "manifest.yaml"

    args = SimpleNamespace(
        sample_count=2,
        sample_rate_hz=2_400_000,
        center_frequency_hz=103_119_454,
        rf_bandwidth_hz=2_000_000,
        manifest_out=manifest_path,
        dataset_id="test_capture",
        title="Test capture",
        uri="ip:192.168.40.1",
    )
    checksum = sha256_file(iq_path)

    manifest = build_manifest(
        args=args,
        iq_path=iq_path.resolve(),
        sha256=checksum,
        applied_state={
            "rx0_rf_port_select": "A_BALANCED",
            "rx0_gain_control_mode": "manual",
            "rx0_hardwaregain_db": "50.000000 dB",
            "rx_lo_frequency_hz": "103119454",
            "rx0_rssi_db": "72.25 dB",
            "rx1_rssi_db": "71.75 dB",
        },
        context_attrs={"hw_model": "Test model", "fw_version": "1.0"},
    )

    assert manifest["file_name"] == "raw/capture.ci16"
    assert "blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py" in manifest[
        "analysis_command"
    ]

    text = yaml.safe_dump(manifest, sort_keys=False)
    assert "dataset_id: test_capture" in text
