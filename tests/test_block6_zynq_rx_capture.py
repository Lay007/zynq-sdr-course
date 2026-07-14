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
    restore_rx_state,
    sha256_file,
    write_ci16,
)


class FakeAttr:
    def __init__(self, value: str, *, reject_units: bool = False) -> None:
        self._value = value
        self.reject_units = reject_units

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        if self.reject_units and " " in value:
            raise OSError("numeric value required")
        self._value = value


def fake_channel(channel_id: str, *, output: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=channel_id,
        output=output,
        attrs={
            "frequency": FakeAttr("0"),
            "sampling_frequency": FakeAttr("0"),
            "rf_bandwidth": FakeAttr("0"),
            "rf_port_select": FakeAttr("A_BALANCED"),
            "gain_control_mode": FakeAttr("manual"),
            "hardwaregain": FakeAttr("0", reject_units=True),
        },
    )


def test_write_ci16_interleaves_i_and_q(tmp_path: Path) -> None:
    path = tmp_path / "capture.ci16"
    i_samples = np.array([1, -2, 3], dtype=np.int16)
    q_samples = np.array([4, -5, 6], dtype=np.int16)

    write_ci16(path, i_samples, q_samples)
    raw = np.fromfile(path, dtype="<i2")

    assert raw.tolist() == [1, 4, -2, -5, 3, 6]


def test_restore_rx_state_strips_hardwaregain_units() -> None:
    rx_lo = fake_channel("altvoltage0", output=True)
    rx0 = fake_channel("voltage0")
    rx1 = fake_channel("voltage1")
    phy = SimpleNamespace(channels=[rx_lo, rx0, rx1])
    snapshot = {
        "rx_lo_frequency_hz": "915000000",
        "rx0_sampling_frequency_hz": "30720000",
        "rx1_sampling_frequency_hz": "30720000",
        "rx0_rf_bandwidth_hz": "18000000",
        "rx1_rf_bandwidth_hz": "18000000",
        "rx0_gain_control_mode": "manual",
        "rx1_gain_control_mode": "manual",
        "rx0_hardwaregain_db": "40.000000 dB",
        "rx1_hardwaregain_db": "73.000000 dB",
        "rx0_rf_port_select": "A_BALANCED",
        "rx1_rf_port_select": "A_BALANCED",
    }

    restore_rx_state(phy, snapshot)

    assert rx_lo.attrs["frequency"].value == "915000000"
    assert rx0.attrs["hardwaregain"].value == "40.000000"
    assert rx1.attrs["hardwaregain"].value == "73.000000"


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
