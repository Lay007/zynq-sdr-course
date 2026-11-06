from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest


MODULE_DIR = Path(__file__).resolve().parents[1] / "blocks" / "block_06_rf_frontend_and_ad9363" / "python"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from lab_6_3_probe_iio_context import (  # noqa: E402
    device_matches_filter,
    extract_ad9361_summary,
    read_attr_map,
)
import lab_6_3_probe_iio_context as probe  # noqa: E402


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
            Channel("altvoltage1", "TX_LO", True, {"frequency": Attr("2450000000"), "powerdown": Attr("1")}),
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
    assert summary["tx_lo_powerdown"] == "1"


def test_device_matches_filter_checks_id_and_name() -> None:
    device = Device(device_id="iio:device0", name="ad9361-phy", channels=[])
    assert device_matches_filter(device, None)
    assert device_matches_filter(device, "ad9361")
    assert device_matches_filter(device, "device0")
    assert not device_matches_filter(device, "xadc")


def saved_probe() -> dict:
    """Synthetic structure only; this fixture contains no observed board results."""
    return {
        "uri": "synthetic:offline", "context_name": "fixture", "context_description": "synthetic",
        "context_attrs": {}, "devices": [
            {"id": "fixture0", "name": "fixture-rx", "label": None, "attrs": {}, "channels": [
                {"id": "voltage0", "output": False, "scan_element": True, "attrs": {}}
            ]}
        ],
    }


def test_saved_report_preserves_evidence_and_does_not_import_iio(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(probe, "load_iio_module", lambda: pytest.fail("offline mode imported libiio"))
    payload = saved_probe()
    payload["observed_at_utc"] = "2020-01-01T00:00:00+00:00"
    source, output = tmp_path / "probe.json", tmp_path / "profile.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    probe.main(["--probe-json", str(source), "--profile-report", str(output),
                "--board-id", "declared-A", "--profile-id", "candidate"])
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["source"] == "saved-probe"
    assert report["observed_at_utc"] == payload["observed_at_utc"]
    assert report["declared_identity"] == {"board_id": "declared-A", "profile_id": "candidate"}
    assert report["observation"] == payload
    assert report["enumerated_scan_channels"][0]["direction"] == "rx"
    assert {"dma_transfer", "physical_sample_clock", "currently_deployed_profile"} <= set(report["not_established"])


def test_legacy_probe_has_unknown_observation_time() -> None:
    report = probe.build_profile_report(saved_probe(), board_id="A", profile_id="unknown", source="saved-probe")
    assert report["observed_at_utc"] is None


@pytest.mark.parametrize("arguments", [
    ["--profile-report", "out.json", "--board-id", "A", "--profile-id", "candidate"],
    ["--profile-report", "out.json", "--uri", "ip:explicit", "--board-id", "A"],
    ["--profile-report", "out.json", "--uri", "ip:explicit", "--board-id", "A",
     "--profile-id", "candidate", "--include-debug-attrs"],
    ["--probe-json", "saved.json", "--uri", "ip:explicit"],
])
def test_invalid_cli_rejected_before_connection(arguments, monkeypatch) -> None:
    monkeypatch.setattr(probe, "probe_context", lambda **kwargs: pytest.fail("unexpected connection"))
    with pytest.raises(SystemExit) as exc:
        probe.main(arguments)
    assert exc.value.code == 2


@pytest.mark.parametrize("payload", [[], {}, {**saved_probe(), "devices": [None]},
                                      {**saved_probe(), "observed_at_utc": "2020-01-01"}])
def test_malformed_saved_probe_rejected(payload) -> None:
    with pytest.raises(ValueError):
        probe.validate_saved_probe(payload)


def test_live_probe_only_reads_attributes_and_never_allocates_buffers(monkeypatch) -> None:
    class ReadOnlyAttr:
        @property
        def value(self):
            return "1"

        @value.setter
        def value(self, value):
            pytest.fail("attribute write")

    device = Device("fixture0", "ad9361-phy", [
        Channel("altvoltage1", "TX_LO", True, {"powerdown": ReadOnlyAttr()}),
    ])
    class FakeContext:
        name, description, attrs, devices = "fixture", "synthetic", {}, [device]

    class FakeIIO:
        @staticmethod
        def Context(uri):
            assert uri == "synthetic:explicit"
            return FakeContext()

        @staticmethod
        def Buffer(*args, **kwargs):
            pytest.fail("buffer allocation")

    monkeypatch.setattr(probe, "load_iio_module", lambda: FakeIIO)
    payload = probe.probe_context("synthetic:explicit", None, False)
    assert payload["devices"][0]["ad9361_summary"]["tx_lo_powerdown"] == "1"
    assert payload["observed_at_utc"]
    assert payload["collection_scope"]["include_debug_attrs"] is False
