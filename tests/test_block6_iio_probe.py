from __future__ import annotations

import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_06_rf_frontend_and_ad9363" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_6_3_probe_iio_context import (  # noqa: E402
    device_matches_filter,
    extract_ad9361_summary,
    read_attr_map,
)


class Attr:
    def __init__(self, value: str) -> None:
        self.value = value


class BrokenAttr:
    @property
    def value(self) -> str:
        raise OSError("permission denied")


class Channel:
    def __init__(self, channel_id: str, name: str, output: bool, attrs: dict[str, object]) -> None:
        self.id = channel_id
        self.name = name
        self.label = None
        self.output = output
        self.scan_element = False
        self.attrs = attrs


class Device:
    def __init__(self, device_id: str, name: str, channels: list[Channel]) -> None:
        self.id = device_id
        self.name = name
        self.label = None
        self.channels = channels
        self.attrs = {}
        self.debug_attrs = {}


def test_read_attr_map_converts_values_and_errors() -> None:
    payload = read_attr_map({"ok": Attr("123"), "bad": BrokenAttr()})
    assert payload["ok"] == "123"
    assert payload["bad"].startswith("<read error:")


def test_extract_ad9361_summary_reads_expected_channels() -> None:
    device = Device(
        device_id="iio:device0",
        name="ad9361-phy",
        channels=[
            Channel("altvoltage0", "RX_LO", True, {"frequency": Attr("2400000000")}),
            Channel("altvoltage1", "TX_LO", True, {"frequency": Attr("2450000000")}),
            Channel(
                "voltage0",
                "",
                False,
                {
                    "rf_bandwidth": Attr("18000000"),
                    "sampling_frequency": Attr("30720000"),
                    "gain_control_mode": Attr("slow_attack"),
                    "hardwaregain": Attr("71.000000 dB"),
                    "rf_port_select": Attr("A_BALANCED"),
                },
            ),
            Channel(
                "voltage0",
                "",
                True,
                {
                    "rf_bandwidth": Attr("18000000"),
                    "sampling_frequency": Attr("30720000"),
                    "hardwaregain": Attr("-10.000000 dB"),
                    "rf_port_select": Attr("A"),
                },
            ),
        ],
    )

    summary = extract_ad9361_summary(device)
    assert summary is not None
    assert summary["rx_lo_frequency_hz"] == "2400000000"
    assert summary["tx_lo_frequency_hz"] == "2450000000"
    assert summary["rx_gain_control_mode"] == "slow_attack"
    assert summary["rx_hardwaregain_db"] == "71.000000 dB"
    assert summary["tx_hardwaregain_db"] == "-10.000000 dB"


def test_device_matches_filter_checks_id_and_name() -> None:
    device = Device(device_id="iio:device0", name="ad9361-phy", channels=[])
    assert device_matches_filter(device, None)
    assert device_matches_filter(device, "ad9361")
    assert device_matches_filter(device, "device0")
    assert not device_matches_filter(device, "xadc")
