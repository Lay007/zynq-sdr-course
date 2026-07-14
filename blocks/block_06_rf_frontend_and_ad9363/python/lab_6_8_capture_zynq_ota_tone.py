#!/usr/bin/env python3
"""Lab 6.8 - Capture a short OTA DDS tone with the stock AD9361 shell."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from lab_6_3_probe_iio_context import find_channel, load_iio_module
from lab_6_6_capture_zynq_rx_only import (
    attr_value_for_write,
    capture_iq,
    repo_relative_or_str,
    sha256_file,
    write_ci16,
)


ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = ROOT / "datasets" / "lab6_8_zynq_ota_tone_observation"
DEFAULT_CENTER_FREQUENCY_HZ = 915_000_000
DEFAULT_SAMPLE_RATE_HZ = 3_840_000
DEFAULT_RF_BANDWIDTH_HZ = 2_000_000
DEFAULT_TONE_OFFSET_HZ = 700_000
DEFAULT_TONE_SCALE = 0.25
DEFAULT_SAMPLE_COUNT = 262_144
DEFAULT_RX_GAIN_DB = 30.0
DEFAULT_TX_ATTENUATION_DB = -40.0
DEFAULT_OUT_IQ = DATASET_DIR / "raw" / "zynq_ota_tone_915MHz_700kHz_live_20260622.ci16"
DEFAULT_MANIFEST = DATASET_DIR / "manifest_tone_915MHz_700kHz_live_20260622.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a short over-the-air AD9361 DDS tone and write a CI16 manifest.")
    parser.add_argument("--uri", default="ip:192.168.40.1", help="libiio context URI, for example ip:192.168.40.1")
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--tone-offset-hz", type=int, default=DEFAULT_TONE_OFFSET_HZ)
    parser.add_argument("--tone-scale", type=float, default=DEFAULT_TONE_SCALE)
    parser.add_argument("--rx-hardwaregain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--tx-hardwaregain-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--out-iq", type=Path, default=DEFAULT_OUT_IQ)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dataset-id", default="lab6_8_zynq_ota_tone_915MHz_700kHz_live_20260622")
    parser.add_argument(
        "--title",
        default="Zynq AD9361 stock-shell OTA DDS tone observation at 915 MHz / 700 kHz (live 2026-06-22)",
        help="Dataset title stored in the output manifest.",
    )
    return parser.parse_args()


def read_attr_value(channel: Any | None, attr_name: str) -> str | None:
    if channel is None:
        return None
    attr = getattr(channel, "attrs", {}).get(attr_name)
    if attr is None:
        return None
    try:
        return str(attr.value)
    except OSError:
        return None


def write_attr_value(channel: Any | None, attr_name: str, value: str | int | float | None, *, strict: bool = True) -> None:
    if channel is None or value is None:
        return
    attr = getattr(channel, "attrs", {}).get(attr_name)
    if attr is None:
        return
    try:
        attr.value = attr_value_for_write(attr_name, str(value))
    except OSError:
        if strict:
            raise


def snapshot_ad9361_state(phy: Any) -> dict[str, str | None]:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    tx_lo = find_channel(phy, "altvoltage1", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)
    tx0 = find_channel(phy, "voltage0", output=True)
    tx1 = find_channel(phy, "voltage1", output=True)
    return {
        "rx_lo_frequency_hz": read_attr_value(rx_lo, "frequency"),
        "tx_lo_frequency_hz": read_attr_value(tx_lo, "frequency"),
        "tx_lo_powerdown": read_attr_value(tx_lo, "powerdown"),
        "rx0_sampling_frequency_hz": read_attr_value(rx0, "sampling_frequency"),
        "rx1_sampling_frequency_hz": read_attr_value(rx1, "sampling_frequency"),
        "tx0_sampling_frequency_hz": read_attr_value(tx0, "sampling_frequency"),
        "tx1_sampling_frequency_hz": read_attr_value(tx1, "sampling_frequency"),
        "rx0_rf_bandwidth_hz": read_attr_value(rx0, "rf_bandwidth"),
        "rx1_rf_bandwidth_hz": read_attr_value(rx1, "rf_bandwidth"),
        "tx0_rf_bandwidth_hz": read_attr_value(tx0, "rf_bandwidth"),
        "tx1_rf_bandwidth_hz": read_attr_value(tx1, "rf_bandwidth"),
        "rx0_gain_control_mode": read_attr_value(rx0, "gain_control_mode"),
        "rx1_gain_control_mode": read_attr_value(rx1, "gain_control_mode"),
        "rx0_hardwaregain_db": read_attr_value(rx0, "hardwaregain"),
        "rx1_hardwaregain_db": read_attr_value(rx1, "hardwaregain"),
        "tx0_hardwaregain_db": read_attr_value(tx0, "hardwaregain"),
        "tx1_hardwaregain_db": read_attr_value(tx1, "hardwaregain"),
        "rx0_rf_port_select": read_attr_value(rx0, "rf_port_select"),
        "rx1_rf_port_select": read_attr_value(rx1, "rf_port_select"),
        "tx0_rf_port_select": read_attr_value(tx0, "rf_port_select"),
        "tx1_rf_port_select": read_attr_value(tx1, "rf_port_select"),
        "rx0_rssi_db": read_attr_value(rx0, "rssi"),
        "rx1_rssi_db": read_attr_value(rx1, "rssi"),
    }


def restore_ad9361_state(phy: Any, snapshot: dict[str, str | None]) -> None:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    tx_lo = find_channel(phy, "altvoltage1", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)
    tx0 = find_channel(phy, "voltage0", output=True)
    tx1 = find_channel(phy, "voltage1", output=True)

    write_attr_value(rx_lo, "frequency", snapshot["rx_lo_frequency_hz"], strict=False)
    write_attr_value(tx_lo, "frequency", snapshot["tx_lo_frequency_hz"], strict=False)
    write_attr_value(tx_lo, "powerdown", snapshot["tx_lo_powerdown"], strict=False)

    def restore_common(channel: Any | None, prefix: str) -> None:
        write_attr_value(channel, "sampling_frequency", snapshot[f"{prefix}_sampling_frequency_hz"], strict=False)
        write_attr_value(channel, "rf_bandwidth", snapshot[f"{prefix}_rf_bandwidth_hz"], strict=False)
        write_attr_value(channel, "rf_port_select", snapshot[f"{prefix}_rf_port_select"], strict=False)

    def restore_rx(channel: Any | None, prefix: str) -> None:
        restore_common(channel, prefix)
        hardware_gain = snapshot[f"{prefix}_hardwaregain_db"]
        gain_mode = snapshot[f"{prefix}_gain_control_mode"]
        if gain_mode == "manual":
            write_attr_value(channel, "hardwaregain", hardware_gain, strict=False)
            write_attr_value(channel, "gain_control_mode", gain_mode, strict=False)
        else:
            write_attr_value(channel, "gain_control_mode", gain_mode, strict=False)
            write_attr_value(channel, "hardwaregain", hardware_gain, strict=False)

    def restore_tx(channel: Any | None, prefix: str) -> None:
        restore_common(channel, prefix)
        write_attr_value(channel, "hardwaregain", snapshot[f"{prefix}_hardwaregain_db"], strict=False)

    restore_rx(rx0, "rx0")
    restore_rx(rx1, "rx1")
    restore_tx(tx0, "tx0")
    restore_tx(tx1, "tx1")


def dds_tone_channels(dds: Any) -> list[Any]:
    return [
        channel
        for channel in getattr(dds, "channels", [])
        if bool(getattr(channel, "output", False)) and str(getattr(channel, "id", "")).startswith("altvoltage")
    ]


def snapshot_dds_state(dds: Any) -> dict[str, dict[str, str | None]]:
    payload: dict[str, dict[str, str | None]] = {}
    for channel in dds_tone_channels(dds):
        payload[str(channel.id)] = {
            "frequency": read_attr_value(channel, "frequency"),
            "phase": read_attr_value(channel, "phase"),
            "scale": read_attr_value(channel, "scale"),
            "raw": read_attr_value(channel, "raw"),
        }
    return payload


def restore_dds_state(dds: Any, snapshot: dict[str, dict[str, str | None]]) -> None:
    for channel in dds_tone_channels(dds):
        write_attr_value(channel, "raw", 0, strict=False)
    for channel in dds_tone_channels(dds):
        state = snapshot.get(str(channel.id))
        if state is None:
            continue
        write_attr_value(channel, "frequency", state.get("frequency"), strict=False)
        write_attr_value(channel, "phase", state.get("phase"), strict=False)
        write_attr_value(channel, "scale", state.get("scale"), strict=False)
        write_attr_value(channel, "raw", state.get("raw"), strict=False)


def configure_ad9361_tone_capture(phy: Any, args: argparse.Namespace) -> dict[str, str | None]:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    tx_lo = find_channel(phy, "altvoltage1", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)
    tx0 = find_channel(phy, "voltage0", output=True)
    tx1 = find_channel(phy, "voltage1", output=True)
    if None in (rx_lo, tx_lo, rx0, rx1, tx0, tx1):
        raise RuntimeError("Unable to locate required AD9361 RX/TX channels in the remote IIO context.")

    write_attr_value(rx_lo, "frequency", args.center_frequency_hz)
    write_attr_value(tx_lo, "frequency", args.center_frequency_hz)
    write_attr_value(tx_lo, "powerdown", 0)

    for channel in (rx0, rx1):
        write_attr_value(channel, "sampling_frequency", args.sample_rate_hz)
        write_attr_value(channel, "rf_bandwidth", args.rf_bandwidth_hz)
        write_attr_value(channel, "gain_control_mode", "manual")
        write_attr_value(channel, "hardwaregain", f"{args.rx_hardwaregain_db:.1f}")
        write_attr_value(channel, "rf_port_select", args.rx_rf_port_select)

    for channel in (tx0, tx1):
        write_attr_value(channel, "sampling_frequency", args.sample_rate_hz)
        write_attr_value(channel, "rf_bandwidth", args.rf_bandwidth_hz)
        write_attr_value(channel, "hardwaregain", f"{args.tx_hardwaregain_db:.1f}")
        write_attr_value(channel, "rf_port_select", args.tx_rf_port_select)

    return snapshot_ad9361_state(phy)


def configure_dds_tone(dds: Any, args: argparse.Namespace) -> None:
    channels = {str(channel.id): channel for channel in dds_tone_channels(dds)}
    if "altvoltage0" not in channels or "altvoltage2" not in channels:
        raise RuntimeError("Unable to locate TX1_I_F1 / TX1_Q_F1 DDS tone channels.")

    for channel in channels.values():
        write_attr_value(channel, "raw", 0, strict=False)
        write_attr_value(channel, "scale", "0.0", strict=False)

    write_attr_value(channels["altvoltage0"], "frequency", args.tone_offset_hz)
    write_attr_value(channels["altvoltage0"], "phase", 90_000)
    write_attr_value(channels["altvoltage0"], "scale", args.tone_scale)
    write_attr_value(channels["altvoltage0"], "raw", 1)

    write_attr_value(channels["altvoltage2"], "frequency", args.tone_offset_hz)
    write_attr_value(channels["altvoltage2"], "phase", 0)
    write_attr_value(channels["altvoltage2"], "scale", args.tone_scale)
    write_attr_value(channels["altvoltage2"], "raw", 1)


def build_manifest(
    *,
    args: argparse.Namespace,
    iq_path: Path,
    sha256: str,
    applied_state: dict[str, str | None],
    context_attrs: dict[str, Any],
) -> dict[str, Any]:
    duration_s = args.sample_count / args.sample_rate_hz
    manifest_dir = args.manifest_out.resolve().parent
    file_name = iq_path.relative_to(manifest_dir).as_posix()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "dataset_id": args.dataset_id,
        "version": 0.1,
        "status": "git-lfs",
        "title": args.title,
        "description": (
            "Short OTA self-observation CI16 IQ capture recorded on the stock Pluto-like Zynq-7020 + AD9361 shell. "
            "The board transmits a DDS-generated single tone from TX1 with conservative power, receives it on RX1 "
            "through separate antennas over a short air path, and stores the result for offline Block 9 analysis."
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
        "processing": {
            "fft_length": 65536,
        },
        "analysis": {
            "peak_search_center_hz": int(args.tone_offset_hz),
            "peak_search_half_span_hz": 50_000,
            "note": "Restrict the peak search to the expected tone neighborhood so full-band edge spurs do not mask the wanted tone.",
        },
        "source": "zynq-ad9361-network-iio-ota-dds-tone",
        "hardware": {
            "transceiver": "Zynq-7020 + AD9361 board",
            "software": "stock Pluto-like Linux 5.15.0 + libiio network context",
            "rf_path": "short OTA self-observation via separate TX1 and RX1 antennas",
            "context_uri": args.uri,
            "rx_rf_port_select": applied_state.get("rx0_rf_port_select"),
            "tx_rf_port_select": applied_state.get("tx0_rf_port_select"),
            "rx_gain_mode": applied_state.get("rx0_gain_control_mode"),
            "rx_gain_db": applied_state.get("rx0_hardwaregain_db"),
            "tx_attenuation_db": applied_state.get("tx0_hardwaregain_db"),
        },
        "signal": {
            "type": "single_tone_dds_rf_tx_rx",
            "expected_signal_offset_hz": int(args.tone_offset_hz),
            "dds_scale": float(args.tone_scale),
            "note": "TX1_I_F1 / TX1_Q_F1 enabled with 90 degree quadrature phasing.",
        },
        "capture_state": {
            "timestamp_utc": timestamp,
            "context_hw_model": context_attrs.get("hw_model", ""),
            "context_fw_version": context_attrs.get("fw_version", ""),
            "rx_lo_frequency_hz": applied_state.get("rx_lo_frequency_hz"),
            "tx_lo_frequency_hz": applied_state.get("tx_lo_frequency_hz"),
            "rx0_rssi_db": applied_state.get("rx0_rssi_db"),
            "rx1_rssi_db": applied_state.get("rx1_rssi_db"),
            "sample_count": int(args.sample_count),
        },
        "analysis_targets": [
            "first stock-shell OTA DDS tone proof on the Zynq AD9361 platform",
            "offline CI16 replay through Block 9 tooling",
            "frequency-plan validation before BPSK over-the-air bring-up",
        ],
        "quality_expectations": {
            "max_clipping_fraction": 0.01,
            "max_dc_offset": 0.25,
            "max_frequency_error_hz": 25_000,
            "min_snr_db": 10.0,
        },
        "quality_checks": {
            "checksum_verified": True,
            "clipping_observed": "analyze_with_lab_9_2",
            "overload_observed": "analyze_with_lab_9_2",
            "dc_offset_checked": "analyze_with_lab_9_2",
            "tone_peak_window_checked": "analyze_with_lab_9_2",
        },
        "license": "course-demo-only-review-before-publication",
        "notes": [
            "Capture performed with AGC disabled and a short over-the-air path between TX1 and RX1 antennas.",
            "This dataset uses the lowest tested radiated setting that made the expected tone the dominant spectral line: TX attenuation -40 dB and RX gain 30 dB.",
            "Lower-power attempts such as TX -60 dB / RX 20 dB still showed the tone near the expected offset, but full-band edge spurs remained stronger than the wanted tone.",
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
    dds = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
    rx_device = next((device for device in context.devices if device.name == "cf-ad9361-lpc"), None)
    if phy is None or dds is None or rx_device is None:
        raise RuntimeError("Expected ad9361-phy, cf-ad9361-dds-core-lpc and cf-ad9361-lpc devices in the remote context.")

    ad9361_before = snapshot_ad9361_state(phy)
    dds_before = snapshot_dds_state(dds)
    try:
        applied_state = configure_ad9361_tone_capture(phy, args)
        configure_dds_tone(dds, args)
        i_samples, q_samples = capture_iq(iio, rx_device, args.sample_count)
    finally:
        restore_dds_state(dds, dds_before)
        restore_ad9361_state(phy, ad9361_before)

    write_ci16(args.out_iq, i_samples, q_samples)
    checksum = sha256_file(args.out_iq)
    manifest = build_manifest(
        args=args,
        iq_path=args.out_iq,
        sha256=checksum,
        applied_state=applied_state,
        context_attrs=dict(getattr(context, "attrs", {})),
    )
    write_manifest(args.manifest_out, manifest)

    print("Lab 6.8 - Zynq OTA DDS tone capture")
    print(f"URI: {args.uri}")
    print(f"IQ file: {args.out_iq}")
    print(f"Manifest: {args.manifest_out}")
    print(f"Samples: {args.sample_count}")
    print(f"Center frequency: {args.center_frequency_hz} Hz")
    print(f"Sample rate: {args.sample_rate_hz} Hz")
    print(f"RF bandwidth: {args.rf_bandwidth_hz} Hz")
    print(f"Tone offset: {args.tone_offset_hz} Hz")
    print(f"Tone scale: {args.tone_scale}")
    print(f"RX gain: {applied_state.get('rx0_hardwaregain_db')}")
    print(f"TX attenuation: {applied_state.get('tx0_hardwaregain_db')}")
    print(f"RSSI: {applied_state.get('rx0_rssi_db')}")
    print(f"SHA256: {checksum}")


if __name__ == "__main__":
    main()
