#!/usr/bin/env python3
"""Lab 11.19 - Runtime self-timed `bridge_txrx_mux` bring-up."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_12_runtime_fpga_manager_reload import (
    md5_bytes,
    probe_gpreg_id,
    read_remote_file_info,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)
from lab_11_13_stock_vs_runtime_rx_compare import probe_iio_context_summary, try_reboot_to_stock
from lab_11_14_stock_shell_bpsk_ota import (
    configure_ad9361_bpsk,
    disable_dds_tones,
    enforce_safe_tx_restore_over_ssh,
    load_iio_module,
    restore_ad9361_state,
    snapshot_ad9361_state,
)
from lab_11_15_runtime_bridge_rx_host_tx_probe import (
    DEFAULT_BASE_ADDR,
    DEFAULT_BIT_BIN_PATH,
    DEFAULT_CENTER_FREQUENCY_HZ,
    DEFAULT_EXPECTED_ID,
    DEFAULT_FRAME_BIT_COUNT,
    DEFAULT_HOST,
    DEFAULT_IIO_URI,
    DEFAULT_PASSWORD,
    DEFAULT_POLL_DELAY_MS,
    DEFAULT_POLL_LIMIT,
    DEFAULT_PORT,
    DEFAULT_PREAMBLE_COUNT,
    DEFAULT_RF_BANDWIDTH_HZ,
    DEFAULT_RX_GAIN_DB,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_REMOTE_FIRMWARE_NAME,
    DEFAULT_SETTLE_MS,
    DEFAULT_START_HOLD_MS,
    DEFAULT_START_OFFSET,
    DEFAULT_TIMEOUT_S,
    DEFAULT_TX_ATTENUATION_DB,
    DEFAULT_TX_REFERENCE_PATH,
    DEFAULT_USER,
    RuntimeBridgeRxHostTxProbeConfig,
    attempt_runtime_bringup,
    load_reference_config,
    make_waveform_config,
    safe_probe,
)
from lab_11_8_axi_gpreg_bpsk_bringup import (
    DEFAULT_RX_DECISION_MODE,
    SshDevMemRegisterIo,
    parse_rx_decision_mode,
)
from lab_11_24_capture_dds_tone_rtl_monitor_wav import (
    DEFAULT_ADC_DEVICE_NAME,
    DEFAULT_ADC_DRIVER_NAME,
    DEFAULT_DDS_DEVICE_NAME,
    DEFAULT_DDS_DRIVER_NAME,
    rebind_platform_driver,
    write_runtime_dds_ratecntrl,
)
from runtime_rx_common import force_rx_common_ctrl_request


ROOT = Path(__file__).resolve().parents[3]
DOC_ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_JSON_STEM = "lab125_runtime_bridge_txrx_self_timed"
DEFAULT_REBOOT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class SelfTimedBringupConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    iio_uri: str
    bit_bin_path: str
    remote_firmware_name: str
    gpreg_base_addr: int
    expected_id: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
    rx_decision_mode: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    center_frequency_hz: int
    sample_rate_hz: int
    rf_bandwidth_hz: int
    tx_attenuation_db: float
    rx_gain_db: float
    settle_ms: int
    rx_rf_port_select: str
    tx_rf_port_select: str
    rx_common_ctrl_value: int
    rebind_runtime_dds_driver: bool
    rebind_runtime_adc_driver: bool
    runtime_dds_ratecntrl: int | None
    reboot_after: bool
    reboot_timeout_s: float


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def build_default_json_out(run_tag: str) -> Path:
    return DOC_ASSET_DIR / f"{DEFAULT_JSON_STEM}_{run_tag}.json"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_BIT_BIN_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
    parser.add_argument("--rx-decision-mode", type=parse_rx_decision_mode, default=parse_rx_decision_mode(DEFAULT_RX_DECISION_MODE))
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--rx-common-ctrl-value", type=parse_int, default=0x00000003)
    parser.add_argument("--rebind-runtime-dds-driver", action="store_true")
    parser.add_argument("--rebind-runtime-adc-driver", action="store_true")
    parser.add_argument("--runtime-dds-ratecntrl", type=parse_int, default=None)
    parser.add_argument("--reboot-after", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser


def build_summary(payload: dict[str, Any], cfg: SelfTimedBringupConfig) -> dict[str, Any]:
    bringup = payload.get("bringup") or {}
    if not bringup.get("ok"):
        return {
            "mode": "self_timed_bridge_txrx_mux",
            "conclusion": "The self-timed runtime bring-up did not complete successfully.",
        }

    result = bringup.get("result") or {}
    received_bits = int(result.get("received_bits") or 0)
    total_errors = int(result.get("total_errors") or 0)
    payload_errors = int(result.get("payload_errors") or 0)
    timed_out = bool(result.get("timed_out_observed"))

    if received_bits == cfg.frame_bit_count and total_errors == 0 and payload_errors == 0:
        conclusion = "The self-timed runtime path reached a full zero-error frame."
    elif received_bits == cfg.frame_bit_count:
        conclusion = (
            "The self-timed runtime path reached a full frame. Remaining BER is now a tuning problem, "
            "not a missing-frame problem."
        )
    elif timed_out:
        conclusion = (
            "The self-timed runtime path still timed out before a full frame, so start/timing or shell-level "
            "integration is still incomplete."
        )
    else:
        conclusion = (
            "The self-timed runtime path ran but did not yet reach a full frame."
        )

    return {
        "mode": "self_timed_bridge_txrx_mux",
        "received_bits": received_bits,
        "total_errors": total_errors,
        "payload_errors": payload_errors,
        "ber_total": result.get("ber_total"),
        "ber_payload": result.get("ber_payload"),
        "rx_valid_count": result.get("rx_valid_count"),
        "tx_valid_count": result.get("tx_valid_count"),
        "timed_out_observed": timed_out,
        "conclusion": conclusion,
    }


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing runtime payload: {bit_bin_path}")

    run_tag = args.run_tag or default_run_tag()
    json_out = (args.json_out or build_default_json_out(run_tag)).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)

    cfg = SelfTimedBringupConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        bit_bin_path=str(bit_bin_path),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
        rx_decision_mode=args.rx_decision_mode,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        tx_attenuation_db=args.tx_attenuation_db,
        rx_gain_db=args.rx_gain_db,
        settle_ms=args.settle_ms,
        rx_rf_port_select=args.rx_rf_port_select,
        tx_rf_port_select=args.tx_rf_port_select,
        rx_common_ctrl_value=args.rx_common_ctrl_value,
        rebind_runtime_dds_driver=bool(args.rebind_runtime_dds_driver),
        rebind_runtime_adc_driver=bool(args.rebind_runtime_adc_driver),
        runtime_dds_ratecntrl=args.runtime_dds_ratecntrl,
        reboot_after=bool(args.reboot_after),
        reboot_timeout_s=args.reboot_timeout_s,
    )

    reference_cfg = load_reference_config()
    waveform_cfg = make_waveform_config(
        reference_cfg=reference_cfg,
        center_frequency_hz=cfg.center_frequency_hz,
        sample_rate_hz=cfg.sample_rate_hz,
        rf_bandwidth_hz=cfg.rf_bandwidth_hz,
        tx_attenuation_db=cfg.tx_attenuation_db,
        rx_gain_db=cfg.rx_gain_db,
        settle_ms=cfg.settle_ms,
        rx_rf_port_select=cfg.rx_rf_port_select,
        tx_rf_port_select=cfg.tx_rf_port_select,
    )

    probe_cfg = RuntimeBridgeRxHostTxProbeConfig(
        ssh_host=cfg.ssh_host,
        ssh_user=cfg.ssh_user,
        ssh_port=cfg.ssh_port,
        ssh_timeout_s=cfg.ssh_timeout_s,
        iio_uri=cfg.iio_uri,
        raw_bit_path="",
        bit_bin_path=cfg.bit_bin_path,
        tx_reference_path=str(DEFAULT_TX_REFERENCE_PATH),
        remote_firmware_name=cfg.remote_firmware_name,
        gpreg_base_addr=cfg.gpreg_base_addr,
        expected_id=cfg.expected_id,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.start_offset,
        rx_decision_mode=cfg.rx_decision_mode,
        start_hold_ms=cfg.start_hold_ms,
        poll_limit=cfg.poll_limit,
        poll_delay_ms=cfg.poll_delay_ms,
        center_frequency_hz=waveform_cfg.center_frequency_hz,
        sample_rate_hz=waveform_cfg.sample_rate_hz,
        symbol_rate_hz=waveform_cfg.symbol_rate_hz,
        samples_per_symbol=waveform_cfg.samples_per_symbol,
        rf_bandwidth_hz=waveform_cfg.rf_bandwidth_hz,
        tx_attenuation_db=waveform_cfg.tx_attenuation_db,
        rx_gain_db=waveform_cfg.rx_gain_db,
        settle_ms=waveform_cfg.settle_ms,
        tx_settle_ms=0,
        rx_rf_port_select=waveform_cfg.rx_rf_port_select,
        tx_rf_port_select=waveform_cfg.tx_rf_port_select,
        rx_common_reinit=True,
        rx_common_ctrl_value=cfg.rx_common_ctrl_value,
        reboot_after=cfg.reboot_after,
        reboot_timeout_s=cfg.reboot_timeout_s,
        dmesg_line_count=80,
    )

    bit_payload = bit_bin_path.read_bytes()
    runner = ParamikoCommandRunner(
        host=cfg.ssh_host,
        user=cfg.ssh_user,
        password=args.ssh_password,
        port=cfg.ssh_port,
        key_path=None,
        timeout_s=cfg.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(cfg.gpreg_base_addr, command_runner=runner)

    payload: dict[str, Any] = {
        "timestamp_utc": iso_now(),
        "run_tag": run_tag,
        "config": asdict(cfg),
        "waveform_config": asdict(waveform_cfg),
        "bitstream": {
            "path": str(bit_bin_path),
            "size_bytes": len(bit_payload),
            "md5": md5_bytes(bit_payload),
        },
        "stock_context_before": None,
        "upload": None,
        "reload": None,
        "gpreg_after_reload": None,
        "post_reload_context": None,
        "rx_common_reinit": None,
        "rebind_runtime_dds": None,
        "rebind_runtime_adc": None,
        "runtime_dds_ratecntrl_write": None,
        "disable_dds_tones": None,
        "phy_before": None,
        "phy_after_config": None,
        "bringup": None,
        "reboot_after": None,
        "summary": None,
    }

    iio = None
    context = None
    phy = None
    phy_snapshot: dict[str, str | None] = {}

    try:
        payload["stock_context_before"] = safe_probe(
            "probe_iio_context_before",
            lambda: probe_iio_context_summary(cfg.iio_uri),
        )

        remote_path = f"/lib/firmware/{cfg.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_payload, remote_path=remote_path)
        payload["upload"] = read_remote_file_info(runner, remote_path)
        payload["reload"] = trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=cfg.remote_firmware_name,
        )
        payload["gpreg_after_reload"] = probe_gpreg_id(io)
        payload["post_reload_context"] = safe_probe(
            "probe_iio_context_after_reload",
            lambda: probe_iio_context_summary(cfg.iio_uri),
        )
        payload["rx_common_reinit"] = force_rx_common_ctrl_request(
            runner,
            value=cfg.rx_common_ctrl_value,
        )

        if cfg.rebind_runtime_dds_driver:
            payload["rebind_runtime_dds"] = rebind_platform_driver(
                runner,
                driver_name=DEFAULT_DDS_DRIVER_NAME,
                device_name=DEFAULT_DDS_DEVICE_NAME,
            )
        if cfg.rebind_runtime_adc_driver:
            payload["rebind_runtime_adc"] = rebind_platform_driver(
                runner,
                driver_name=DEFAULT_ADC_DRIVER_NAME,
                device_name=DEFAULT_ADC_DEVICE_NAME,
            )
        if cfg.runtime_dds_ratecntrl is not None:
            payload["runtime_dds_ratecntrl_write"] = write_runtime_dds_ratecntrl(
                runner,
                cfg.runtime_dds_ratecntrl,
            )

        iio = load_iio_module()
        context = iio.Context(cfg.iio_uri)
        phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
        if phy is None:
            raise RuntimeError("Expected `ad9361-phy` after runtime reload.")

        dds = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
        if dds is not None:
            disable_dds_tones(dds)
            payload["disable_dds_tones"] = {"status": "ok", "device": "cf-ad9361-dds-core-lpc"}
        else:
            payload["disable_dds_tones"] = {"status": "device_not_found"}

        phy_snapshot = snapshot_ad9361_state(phy)
        payload["phy_before"] = phy_snapshot
        payload["phy_after_config"] = configure_ad9361_bpsk(phy, waveform_cfg)
        payload["bringup"] = attempt_runtime_bringup(io, probe_cfg)
    finally:
        try:
            if phy is not None and phy_snapshot:
                restore_ad9361_state(phy, phy_snapshot)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload.setdefault("cleanup_errors", []).append(
                {"stage": "restore_ad9361_state", "error": str(exc)}
            )
        try:
            if phy_snapshot:
                class Args:
                    ssh_host = cfg.ssh_host
                    ssh_user = cfg.ssh_user
                    ssh_password = args.ssh_password
                    ssh_port = cfg.ssh_port
                    ssh_timeout_s = cfg.ssh_timeout_s

                enforce_safe_tx_restore_over_ssh(phy_snapshot, Args)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload.setdefault("cleanup_errors", []).append(
                {"stage": "enforce_safe_tx_restore_over_ssh", "error": str(exc)}
            )

        if cfg.reboot_after:
            payload["reboot_after"] = safe_probe(
                "try_reboot_to_stock",
                lambda: try_reboot_to_stock(
                    runner,
                    host=cfg.ssh_host,
                    user=cfg.ssh_user,
                    password=args.ssh_password,
                    port=cfg.ssh_port,
                    ssh_timeout_s=cfg.ssh_timeout_s,
                    iio_uri=cfg.iio_uri,
                    timeout_s=cfg.reboot_timeout_s,
                ),
            )
        try:
            runner.close()
        except Exception as exc:  # pragma: no cover - connection may already drop after reboot
            payload.setdefault("cleanup_errors", []).append(
                {"stage": "runner.close", "error": str(exc)}
            )

    payload["summary"] = build_summary(payload, cfg)
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Lab 11.19 - Runtime self-timed bridge_txrx_mux bring-up")
    print(f"JSON: {json_out}")
    summary = payload["summary"] or {}
    print(f"Conclusion: {summary.get('conclusion')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
