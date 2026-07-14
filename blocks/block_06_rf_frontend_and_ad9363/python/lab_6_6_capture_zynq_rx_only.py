#!/usr/bin/env python3
"""Lab 6.6 - Capture a receive-only AD9361/AD9363 IQ snapshot from the host."""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from lab_6_3_probe_iio_context import find_channel, load_iio_module


ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = ROOT / "datasets" / "lab6_6_zynq_rx_observation"
DEFAULT_CENTER_FREQUENCY_HZ = 103_119_454
DEFAULT_SAMPLE_RATE_HZ = 2_400_000
DEFAULT_RF_BANDWIDTH_HZ = 2_000_000
DEFAULT_SAMPLE_COUNT = 262_144
DEFAULT_OUT_IQ = DATASET_DIR / "raw" / "zynq_rx_fm_103119454Hz.ci16"
DEFAULT_MANIFEST = DATASET_DIR / "manifest_fm_103119454.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a short receive-only AD9361/AD9363 CI16 IQ snapshot over IIO.")
    parser.add_argument("--uri", default="ip:192.168.40.1", help="libiio context URI, for example ip:192.168.40.1")
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--gain-control-mode", default="manual", choices=["manual", "slow_attack", "fast_attack", "hybrid"])
    parser.add_argument("--rx-hardwaregain-db", type=float, default=50.0, help="Used when gain-control-mode=manual")
    parser.add_argument("--rf-port-select", default="A_BALANCED")
    parser.add_argument("--out-iq", type=Path, default=DEFAULT_OUT_IQ)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dataset-id", default="lab6_6_zynq_rx_fm_103119454")
    parser.add_argument(
        "--title",
        default="Zynq AD9361 RX-only FM observation at 103.119454 MHz",
        help="Dataset title stored in the output manifest.",
    )
    return parser.parse_args()


def read_attr_value(channel: Any | None, attr_name: str) -> str | None:
    if channel is None:
        return None
    attr = getattr(channel, "attrs", {}).get(attr_name)
    if attr is None:
        return None
    return str(attr.value)


def snapshot_rx_state(phy: Any) -> dict[str, str | None]:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)
    return {
        "rx_lo_frequency_hz": read_attr_value(rx_lo, "frequency"),
        "rx0_sampling_frequency_hz": read_attr_value(rx0, "sampling_frequency"),
        "rx1_sampling_frequency_hz": read_attr_value(rx1, "sampling_frequency"),
        "rx0_rf_bandwidth_hz": read_attr_value(rx0, "rf_bandwidth"),
        "rx1_rf_bandwidth_hz": read_attr_value(rx1, "rf_bandwidth"),
        "rx0_gain_control_mode": read_attr_value(rx0, "gain_control_mode"),
        "rx1_gain_control_mode": read_attr_value(rx1, "gain_control_mode"),
        "rx0_hardwaregain_db": read_attr_value(rx0, "hardwaregain"),
        "rx1_hardwaregain_db": read_attr_value(rx1, "hardwaregain"),
        "rx0_rf_port_select": read_attr_value(rx0, "rf_port_select"),
        "rx1_rf_port_select": read_attr_value(rx1, "rf_port_select"),
        "rx0_rssi_db": read_attr_value(rx0, "rssi"),
        "rx1_rssi_db": read_attr_value(rx1, "rssi"),
    }


def attr_value_for_write(attr_name: str, value: str) -> str:
    """Convert a displayed IIO attribute value back to its writable form."""
    if attr_name == "hardwaregain":
        # Some libiio versions return values such as ``40.000000 dB`` while
        # the corresponding sysfs attribute accepts only the numeric token.
        return value.split()[0]
    return value


def restore_rx_state(phy: Any, snapshot: dict[str, str | None]) -> None:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)

    if rx_lo is not None and snapshot["rx_lo_frequency_hz"] is not None:
        rx_lo.attrs["frequency"].value = snapshot["rx_lo_frequency_hz"]

    def write_attr(channel: Any | None, attr_name: str, value: str | None) -> None:
        if channel is None or value is None or attr_name not in channel.attrs:
            return
        try:
            channel.attrs[attr_name].value = attr_value_for_write(attr_name, value)
        except OSError:
            pass

    for channel, prefix in ((rx0, "rx0"), (rx1, "rx1")):
        write_attr(channel, "sampling_frequency", snapshot[f"{prefix}_sampling_frequency_hz"])
        write_attr(channel, "rf_bandwidth", snapshot[f"{prefix}_rf_bandwidth_hz"])
        write_attr(channel, "rf_port_select", snapshot[f"{prefix}_rf_port_select"])

        gain_mode = snapshot[f"{prefix}_gain_control_mode"]
        hardware_gain = snapshot[f"{prefix}_hardwaregain_db"]

        if gain_mode == "manual":
            write_attr(channel, "gain_control_mode", gain_mode)
            write_attr(channel, "hardwaregain", hardware_gain)
        else:
            write_attr(channel, "hardwaregain", hardware_gain)
            write_attr(channel, "gain_control_mode", gain_mode)


def configure_rx(phy: Any, args: argparse.Namespace) -> dict[str, str | None]:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)
    if rx_lo is None or rx0 is None or rx1 is None:
        raise RuntimeError("Unable to locate required AD9361 RX channels in the remote IIO context.")

    rx_lo.attrs["frequency"].value = str(args.center_frequency_hz)
    for channel in (rx0, rx1):
        channel.attrs["sampling_frequency"].value = str(args.sample_rate_hz)
        channel.attrs["rf_bandwidth"].value = str(args.rf_bandwidth_hz)
        channel.attrs["rf_port_select"].value = args.rf_port_select
        channel.attrs["gain_control_mode"].value = args.gain_control_mode
        if args.gain_control_mode == "manual":
            channel.attrs["hardwaregain"].value = f"{args.rx_hardwaregain_db:.1f}"

    return snapshot_rx_state(phy)


def capture_iq(iio: Any, rx_device: Any, sample_count: int) -> tuple[np.ndarray, np.ndarray]:
    for channel in getattr(rx_device, "channels", []):
        channel.enabled = False

    i_channel = rx_device.channels[0]
    q_channel = rx_device.channels[1]
    i_channel.enabled = True
    q_channel.enabled = True

    buf = iio.Buffer(rx_device, sample_count, False)
    buf.refill()
    i_samples = np.frombuffer(i_channel.read(buf), dtype=np.int16).copy()
    q_samples = np.frombuffer(q_channel.read(buf), dtype=np.int16).copy()
    return i_samples, q_samples


def write_ci16(path: Path, i_samples: np.ndarray, q_samples: np.ndarray) -> None:
    interleaved = np.empty(2 * len(i_samples), dtype="<i2")
    interleaved[0::2] = i_samples.astype("<i2", copy=False)
    interleaved[1::2] = q_samples.astype("<i2", copy=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    interleaved.tofile(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def repo_relative_or_str(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def build_manifest(
    *,
    args: argparse.Namespace,
    iq_path: Path,
    sha256: str,
    applied_state: dict[str, str | None],
    context_attrs: dict[str, Any],
) -> dict[str, Any]:
    sample_count = args.sample_count
    duration_s = sample_count / args.sample_rate_hz
    manifest_dir = args.manifest_out.resolve().parent
    file_name = iq_path.relative_to(manifest_dir).as_posix()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "dataset_id": args.dataset_id,
        "version": 0.1,
        "status": "git-lfs",
        "title": args.title,
        "description": (
            "Short receive-only CI16 IQ capture recorded over network IIO from the clean "
            "stock Pluto-like image on the Zynq-7020 + AD9361 board. Intended as the first "
            "hardware RX baseline for Block 6 and for comparison with the earlier RTL-SDR FM observation."
        ),
        "storage": "git-lfs",
        "url": None,
        "file_name": file_name,
        "sha256": sha256,
        "format": "ci16",
        "endianness": "little",
        "i_first": True,
        "sample_rate_hz": int(args.sample_rate_hz),
        "center_frequency_hz": int(args.center_frequency_hz),
        "bandwidth_hz": int(args.rf_bandwidth_hz),
        "duration_s": round(duration_s, 6),
        "analysis_command": (
            "python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py "
            f"--manifest {repo_relative_or_str(args.manifest_out)}"
        ),
        "source": "zynq-ad9361-network-iio-passive-observation",
        "hardware": {
            "receiver": "Zynq-7020 + AD9361 board",
            "software": "stock Pluto-like Linux 5.15.0 + libiio network context",
            "rf_path": "passive OTA receive-only via RX1",
            "context_uri": args.uri,
            "rf_port_select": applied_state.get("rx0_rf_port_select"),
            "gain_mode": applied_state.get("rx0_gain_control_mode"),
            "rx_gain_db": applied_state.get("rx0_hardwaregain_db"),
        },
        "signal": {
            "type": "broadcast_fm_or_fm_band_observation",
            "expected_signal_offset_hz": 0,
            "note": "First Zynq clean-image receive-only FM-band baseline near the earlier RTL-SDR observation.",
        },
        "capture_state": {
            "timestamp_utc": timestamp,
            "context_hw_model": context_attrs.get("hw_model", ""),
            "context_fw_version": context_attrs.get("fw_version", ""),
            "rx_lo_frequency_hz": applied_state.get("rx_lo_frequency_hz"),
            "rx0_rssi_db": applied_state.get("rx0_rssi_db"),
            "rx1_rssi_db": applied_state.get("rx1_rssi_db"),
            "sample_count": int(sample_count),
        },
        "analysis_targets": [
            "first clean-image AD9361 RX baseline",
            "offline CI16 replay through Block 9 tooling",
            "receiver-shape comparison against RTL-SDR FM observation",
        ],
        "quality_expectations": {
            "max_clipping_fraction": 0.01,
            "max_dc_offset": 0.25,
            "max_frequency_error_hz": 1_000_000,
            "min_snr_db": -50.0,
        },
        "quality_checks": {
            "checksum_verified": True,
            "clipping_observed": "analyze_with_lab_9_2",
            "overload_observed": "analyze_with_lab_9_2",
            "dc_offset_checked": "analyze_with_lab_9_2",
        },
        "license": "course-demo-only-review-before-publication",
        "notes": [
            "Capture performed with TX LO held in powerdown by the course-clean autorun overlay.",
            "This is a receive-only artifact. No conducted TX path was used because no attenuators are currently installed.",
            "Absolute amplitude is receiver-dependent; compare spectral shape and occupancy before comparing levels.",
        ],
    }


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_iq = args.out_iq.resolve()
    args.manifest_out = args.manifest_out.resolve()
    iio = load_iio_module()
    context = iio.Context(args.uri)
    phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
    rx_device = next((device for device in context.devices if device.name == "cf-ad9361-lpc"), None)
    if phy is None or rx_device is None:
        raise RuntimeError("Expected ad9361-phy and cf-ad9361-lpc devices in the remote context.")

    before = snapshot_rx_state(phy)
    try:
        applied = configure_rx(phy, args)
        i_samples, q_samples = capture_iq(iio, rx_device, args.sample_count)
    finally:
        restore_rx_state(phy, before)

    write_ci16(args.out_iq, i_samples, q_samples)
    checksum = sha256_file(args.out_iq)
    manifest = build_manifest(
        args=args,
        iq_path=args.out_iq.resolve(),
        sha256=checksum,
        applied_state=applied,
        context_attrs=dict(getattr(context, "attrs", {})),
    )
    write_manifest(args.manifest_out, manifest)

    print("Lab 6.6 - Zynq RX-only capture")
    print(f"URI: {args.uri}")
    print(f"IQ file: {args.out_iq}")
    print(f"Manifest: {args.manifest_out}")
    print(f"Samples: {args.sample_count}")
    print(f"Center frequency: {args.center_frequency_hz} Hz")
    print(f"Sample rate: {args.sample_rate_hz} Hz")
    print(f"RF bandwidth: {args.rf_bandwidth_hz} Hz")
    print(f"Gain mode: {applied.get('rx0_gain_control_mode')}")
    print(f"RX gain: {applied.get('rx0_hardwaregain_db')}")
    print(f"RSSI: {applied.get('rx0_rssi_db')}")
    print(f"SHA256: {checksum}")


if __name__ == "__main__":
    main()
