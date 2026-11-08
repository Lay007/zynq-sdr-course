#!/usr/bin/env python3
"""Lab 6.3 - Probe a remote IIO context from the host.

This script connects to a libiio context such as ``ip:192.168.40.1``,
prints a compact device summary, and optionally writes the discovered state
to JSON for later reporting.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_URI = "ip:192.168.40.1"
DEFAULT_WINDOWS_LIBIIO_BIN = Path("C:/Program Files/IIO Oscilloscope/bin")
_DLL_DIR_HANDLES: list[Any] = []


def add_windows_libiio_bin_to_path(bin_dir: Path = DEFAULT_WINDOWS_LIBIIO_BIN) -> bool:
    """Expose libiio.dll from the default Windows ADI install path."""
    if os.name != "nt" or not bin_dir.exists():
        return False

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    if str(bin_dir) not in path_entries:
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        try:
            _DLL_DIR_HANDLES.append(add_dll_directory(str(bin_dir)))
        except OSError:
            pass

    return True


def load_iio_module() -> Any:
    add_windows_libiio_bin_to_path()
    try:
        import iio  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on local install state
        raise RuntimeError(
            "Unable to import pylibiio/libiio. Install `pylibiio` with "
            "`python -m pip install --user pylibiio` and ensure `libiio.dll` is "
            "available. On Windows, `winget install -e --id "
            "AnalogDevicesInc.IIO-Oscilloscope` provides the default DLL path."
        ) from exc
    return iio


def read_attr_map(attr_map: dict[str, Any]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for name, attr in sorted(attr_map.items()):
        try:
            payload[name] = str(attr.value)
        except Exception as exc:  # pragma: no cover - depends on device permissions
            payload[name] = f"<read error: {exc}>"
    return payload


def channel_matches(channel: Any, channel_id: str, output: bool | None = None) -> bool:
    if getattr(channel, "id", None) != channel_id:
        return False
    if output is None:
        return True
    return bool(getattr(channel, "output", False)) is output


def find_channel(device: Any, channel_id: str, output: bool | None = None) -> Any | None:
    for channel in getattr(device, "channels", []):
        if channel_matches(channel, channel_id, output=output):
            return channel
    return None


def read_channel_attr(channel: Any | None, attr_name: str) -> str | None:
    if channel is None:
        return None
    attr = getattr(channel, "attrs", {}).get(attr_name)
    if attr is None:
        return None
    try:
        return str(attr.value)
    except Exception as exc:  # pragma: no cover - depends on device permissions
        return f"<read error: {exc}>"


def extract_ad9361_summary(device: Any) -> dict[str, str] | None:
    if getattr(device, "name", None) != "ad9361-phy":
        return None

    rx_lo = find_channel(device, "altvoltage0", output=True)
    tx_lo = find_channel(device, "altvoltage1", output=True)
    rx0 = find_channel(device, "voltage0", output=False)
    tx0 = find_channel(device, "voltage0", output=True)

    return {
        "rx_lo_frequency_hz": read_channel_attr(rx_lo, "frequency") or "",
        "tx_lo_frequency_hz": read_channel_attr(tx_lo, "frequency") or "",
        "tx_lo_powerdown": read_channel_attr(tx_lo, "powerdown") or "",
        "rx_rf_bandwidth_hz": read_channel_attr(rx0, "rf_bandwidth") or "",
        "tx_rf_bandwidth_hz": read_channel_attr(tx0, "rf_bandwidth") or "",
        "rx_sampling_frequency_hz": read_channel_attr(rx0, "sampling_frequency") or "",
        "tx_sampling_frequency_hz": read_channel_attr(tx0, "sampling_frequency") or "",
        "rx_gain_control_mode": read_channel_attr(rx0, "gain_control_mode") or "",
        "rx_hardwaregain_db": read_channel_attr(rx0, "hardwaregain") or "",
        "tx_hardwaregain_db": read_channel_attr(tx0, "hardwaregain") or "",
        "rx_rf_port_select": read_channel_attr(rx0, "rf_port_select") or "",
        "tx_rf_port_select": read_channel_attr(tx0, "rf_port_select") or "",
    }


def summarize_channel(channel: Any) -> dict[str, Any]:
    return {
        "id": getattr(channel, "id", None),
        "name": getattr(channel, "name", None),
        "label": getattr(channel, "label", None),
        "output": bool(getattr(channel, "output", False)),
        "scan_element": bool(getattr(channel, "scan_element", False)),
        "attrs": read_attr_map(getattr(channel, "attrs", {})),
    }


def device_matches_filter(device: Any, device_filter: str | None) -> bool:
    if not device_filter:
        return True
    needle = device_filter.lower()
    fields = [
        str(getattr(device, "id", "") or ""),
        str(getattr(device, "name", "") or ""),
        str(getattr(device, "label", "") or ""),
    ]
    return any(needle in field.lower() for field in fields)


def summarize_device(device: Any, include_debug_attrs: bool) -> dict[str, Any]:
    payload = {
        "id": getattr(device, "id", None),
        "name": getattr(device, "name", None),
        "label": getattr(device, "label", None),
        "attrs": read_attr_map(getattr(device, "attrs", {})),
        "channels": [summarize_channel(channel) for channel in getattr(device, "channels", [])],
    }
    if include_debug_attrs:
        payload["debug_attrs"] = read_attr_map(getattr(device, "debug_attrs", {}))

    ad9361_summary = extract_ad9361_summary(device)
    if ad9361_summary is not None:
        payload["ad9361_summary"] = ad9361_summary

    return payload


def probe_context(uri: str, device_filter: str | None, include_debug_attrs: bool) -> dict[str, Any]:
    iio = load_iio_module()
    context = iio.Context(uri)
    return {
        "uri": uri,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "collection_scope": {"device_filter": device_filter, "include_debug_attrs": include_debug_attrs},
        "context_name": getattr(context, "name", ""),
        "context_description": getattr(context, "description", ""),
        "context_attrs": dict(sorted(getattr(context, "attrs", {}).items())),
        "devices": [
            summarize_device(device, include_debug_attrs=include_debug_attrs)
            for device in getattr(context, "devices", [])
            if device_matches_filter(device, device_filter)
        ],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def validate_saved_probe(payload: Any) -> dict[str, Any]:
    """Check the Lab 6.3 snapshot structure before replaying untrusted JSON."""
    if not isinstance(payload, dict):
        raise ValueError("probe must be a JSON object")
    for key in ("uri", "context_name", "context_description"):
        if not isinstance(payload.get(key), str):
            raise ValueError(f"probe requires string {key}")
    if not isinstance(payload.get("context_attrs"), dict) or not isinstance(payload.get("devices"), list):
        raise ValueError("probe requires context_attrs object and devices list")
    if "observed_at_utc" in payload:
        value = payload["observed_at_utc"]
        if not isinstance(value, str) or datetime.fromisoformat(value).utcoffset() is None:
            raise ValueError("observed_at_utc must be a timestamp with a timezone")
    for device in payload["devices"]:
        if not isinstance(device, dict) or not {"id", "name", "label", "attrs", "channels"} <= device.keys():
            raise ValueError("invalid probe device")
        if not isinstance(device["attrs"], dict) or not isinstance(device["channels"], list):
            raise ValueError("device requires attrs object and channels list")
        if "ad9361_summary" in device and not isinstance(device["ad9361_summary"], dict):
            raise ValueError("ad9361_summary must be an object")
        for channel in device["channels"]:
            if not isinstance(channel, dict) or not isinstance(channel.get("attrs"), dict):
                raise ValueError("invalid probe channel")
            if any(type(channel.get(key)) is not bool for key in ("output", "scan_element")):
                raise ValueError("channel output and scan_element must be booleans")
    return payload


def build_profile_report(payload: dict[str, Any], *, board_id: str, profile_id: str,
                         source: str) -> dict[str, Any]:
    """Describe IIO observations; identifiers are operator declarations, not detection."""
    if source not in {"live-iio", "saved-probe"}:
        raise ValueError("unknown observation source")
    validate_saved_probe(payload)
    return {
        "schema_version": 1,
        "report_generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "declared_identity": {"board_id": board_id, "profile_id": profile_id},
        "observation": payload,
        "observed_at_utc": payload.get("observed_at_utc"),
        "enumerated_scan_channels": [
            {"device_id": device["id"], "channel_id": channel.get("id"),
             "direction": "tx" if channel["output"] else "rx"}
            for device in payload["devices"] for channel in device["channels"]
            if channel["scan_element"]
        ],
        "not_established": [
            "boot_chain_identity", "fpga_image_identity", "physical_sample_clock",
            "dma_transfer", "rollback", "rf_performance", "currently_deployed_profile",
        ],
        "limitations": [
            "Saved input is supplied evidence; replay does not observe a board.",
            "IIO attributes describe configured values; enumeration does not prove clock edges or DMA.",
            "This probe does not mute TX or establish RF safety; powerdown is only read.",
        ],
    }


def print_summary(payload: dict[str, Any]) -> None:
    print("Lab 6.3 - IIO context probe")
    print(f"URI: {payload['uri']}")
    print(f"Context: {payload['context_name']}")
    print(f"Description: {payload['context_description']}")
    if payload["context_attrs"]:
        print("Context attributes:")
        for key, value in payload["context_attrs"].items():
            print(f"  {key}: {value}")

    devices = payload["devices"]
    print(f"Devices found: {len(devices)}")
    for device in devices:
        label = device["label"] or "-"
        print(f"- {device['id']} name={device['name']} label={label} channels={len(device['channels'])}")
        if "ad9361_summary" in device:
            print("  AD9361 summary:")
            for key, value in device["ad9361_summary"].items():
                print(f"    {key}: {value}")
        else:
            for key, value in list(device["attrs"].items())[:6]:
                print(f"  {key}: {value}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Probe a remote IIO context and summarize its devices")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--uri", help="libiio context URI, for example ip:192.168.40.1")
    source.add_argument("--probe-json", type=Path, help="Replay saved Lab 6.3 JSON without libiio or a connection")
    parser.add_argument("--device-filter", default=None, help="Only include devices whose id/name/label matches")
    parser.add_argument(
        "--include-debug-attrs",
        action="store_true",
        help="Include device debug attributes in JSON output",
    )
    parser.add_argument("--json-out", type=Path, default=None, help="Optional JSON report path")
    parser.add_argument("--profile-report", type=Path, help="Write an evidence-scoped firmware profile observation")
    parser.add_argument("--board-id", help="Operator-declared board identifier")
    parser.add_argument("--profile-id", help="Operator-declared profile candidate")
    args = parser.parse_args(argv)
    if args.profile_report and (not args.board_id or not args.profile_id):
        parser.error("--profile-report requires --board-id and --profile-id")
    if args.profile_report and not (args.uri or args.probe_json):
        parser.error("live --profile-report requires an explicit --uri")
    if args.profile_report and args.include_debug_attrs:
        parser.error("--profile-report excludes debug attribute reads")
    if args.probe_json and (args.device_filter or args.include_debug_attrs):
        parser.error("saved probes cannot be filtered or queried for debug attributes")
    if args.probe_json:
        try:
            payload = validate_saved_probe(json.loads(args.probe_json.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            parser.error(f"invalid saved probe: {exc}")
    else:
        payload = probe_context(
            uri=args.uri or DEFAULT_URI,
            device_filter=args.device_filter,
            include_debug_attrs=args.include_debug_attrs,
        )
    print_summary(payload)

    if args.profile_report:
        report = build_profile_report(payload, board_id=args.board_id, profile_id=args.profile_id,
                                      source="saved-probe" if args.probe_json else "live-iio")
        write_json(args.profile_report, report)
        print(f"Profile observation: {args.profile_report}")

    if args.json_out is not None:
        write_json(args.json_out, payload)
        print(f"JSON report: {args.json_out}")


if __name__ == "__main__":
    main()
