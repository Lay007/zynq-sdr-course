from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_06_rf_frontend_and_ad9363" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_6_8_capture_zynq_ota_tone import (  # noqa: E402
    build_manifest,
    format_hardwaregain_db,
    write_attr_value,
)


class NumericOnlyAttr:
    def __init__(self) -> None:
        self._value = ""

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        if " " in value:
            raise OSError("numeric value required")
        self._value = value


def test_write_attr_value_strips_display_units_for_hardwaregain() -> None:
    attr = NumericOnlyAttr()
    channel = SimpleNamespace(attrs={"hardwaregain": attr})

    write_attr_value(channel, "hardwaregain", "-89.750000 dB")

    assert attr.value == "-89.750000"


def test_format_hardwaregain_preserves_quarter_db_step() -> None:
    assert format_hardwaregain_db(-89.75) == "-89.75"
    assert format_hardwaregain_db(-40.0) == "-40.00"


def test_build_manifest_records_peak_search_window_and_relative_path(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    raw_dir = dataset_dir / "raw"
    raw_dir.mkdir(parents=True)
    iq_path = raw_dir / "tone.ci16"
    iq_path.write_bytes(b"\x01\x00\x02\x00")
    manifest_path = dataset_dir / "manifest.yaml"

    args = SimpleNamespace(
        sample_count=2,
        sample_rate_hz=3_840_000,
        center_frequency_hz=915_000_000,
        rf_bandwidth_hz=2_000_000,
        tone_offset_hz=700_000,
        tone_scale=0.25,
        manifest_out=manifest_path,
        dataset_id="tone_capture_test",
        title="Tone capture test",
        uri="ip:192.168.40.1",
    )

    manifest = build_manifest(
        args=args,
        iq_path=iq_path.resolve(),
        sha256="DEADBEEF",
        applied_state={
            "rx0_rf_port_select": "A_BALANCED",
            "tx0_rf_port_select": "A",
            "rx0_gain_control_mode": "manual",
            "rx0_hardwaregain_db": "30.000000 dB",
            "tx0_hardwaregain_db": "-40.000000 dB",
            "rx_lo_frequency_hz": "915000000",
            "tx_lo_frequency_hz": "915000000",
            "rx0_rssi_db": "86.00 dB",
            "rx1_rssi_db": "85.50 dB",
        },
        context_attrs={"hw_model": "Test model", "fw_version": "1.0"},
    )

    assert manifest["file_name"] == "raw/tone.ci16"
    assert manifest["signal"]["expected_signal_offset_hz"] == 700_000
    assert manifest["analysis"]["peak_search_half_span_hz"] == 50_000
    assert "lab_9_2_read_ci16_iq_and_analyze.py" in manifest["analysis_command"]
