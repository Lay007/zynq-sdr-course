#!/usr/bin/env python3
"""Lab 11.17 - Sweep start_offset after runtime RX common re-init under stock host TX."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lab_11_7_axi_lite_bpsk_bringup import parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import SshDevMemRegisterIo
from lab_11_12_runtime_fpga_manager_reload import md5_bytes, read_remote_file_info, trigger_fpga_manager_reload, upload_bytes_via_ssh_cat
from lab_11_13_stock_vs_runtime_rx_compare import try_reboot_to_stock
from lab_11_14_stock_shell_bpsk_ota import (
    configure_ad9361_bpsk,
    disable_dds_tones,
    enforce_safe_tx_restore_over_ssh,
    load_iio_module,
    restore_ad9361_state,
    restore_dds_state,
    snapshot_ad9361_state,
    snapshot_dds_state,
    transmit_cyclic_buffer,
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
    DEFAULT_TIMEOUT_S,
    DEFAULT_TX_ATTENUATION_DB,
    DEFAULT_TX_REFERENCE_PATH,
    DEFAULT_TX_SETTLE_MS,
    DEFAULT_USER,
    RuntimeBridgeRxHostTxProbeConfig,
    attempt_runtime_bringup,
    load_reference_config,
    make_waveform_config,
    read_ci16_complex,
)
from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner
from runtime_rx_common import force_rx_common_ctrl_request


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OFFSETS = "32,40,48,56,60,62,64,68,72,76,80,84,88,92,96"
DEFAULT_REBOOT_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class StartOffsetSweepConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    iio_uri: str
    bit_bin_path: str
    tx_reference_path: str
    remote_firmware_name: str
    gpreg_base_addr: int
    expected_id: int
    frame_bit_count: int
    preamble_count: int
    start_hold_ms: int
    poll_limit: int
    poll_delay_ms: int
    center_frequency_hz: int
    sample_rate_hz: int
    symbol_rate_hz: int
    samples_per_symbol: int
    rf_bandwidth_hz: int
    tx_attenuation_db: float
    rx_gain_db: float
    settle_ms: int
    tx_settle_ms: int
    rx_rf_port_select: str
    tx_rf_port_select: str
    rx_common_ctrl_value: int
    offsets: list[int]
    reboot_after: bool
    reboot_timeout_s: float


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def build_default_json_out(run_tag: str) -> Path:
    return ROOT / "docs" / "assets" / f"lab117_runtime_rx_common_reinit_start_offset_sweep_{run_tag}.json"


def parse_offsets(value: str) -> list[int]:
    offsets = [int(chunk.strip(), 0) for chunk in value.split(",") if chunk.strip()]
    if not offsets:
        raise argparse.ArgumentTypeError("Expected at least one start_offset value.")
    return offsets


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    best = max(
        results,
        key=lambda row: (
            int(row.get("received_bits") or 0),
            -int(row.get("payload_errors") or 10**9),
            -int(row.get("total_errors") or 10**9),
            int(row.get("rx_valid_count") or 0),
        ),
    )
    completed = [row for row in results if int(row.get("received_bits") or 0) > 0]
    first = results[0] if results else None
    if completed and first is not None and completed == [first]:
        conclusion = (
            "Only the first post-TX attempt completed a frame in this single-session sweep, "
            "so the remaining blocker is timing/phase repeatability rather than dead RX plumbing."
        )
    elif completed:
        conclusion = (
            "Multiple start_offset windows completed full-frame receives, so the runtime path is now alive and tunable."
        )
    else:
        conclusion = (
            "No start_offset value completed a full-frame receive in this sweep, even after the RX common re-init."
        )
    return {"best": best, "completed_results": completed, "conclusion": conclusion}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--iio-uri", default=DEFAULT_IIO_URI)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_BIT_BIN_PATH)
    parser.add_argument("--tx-reference-path", type=Path, default=DEFAULT_TX_REFERENCE_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-hold-ms", type=int, default=DEFAULT_START_HOLD_MS)
    parser.add_argument("--poll-limit", type=int, default=DEFAULT_POLL_LIMIT)
    parser.add_argument("--poll-delay-ms", type=int, default=DEFAULT_POLL_DELAY_MS)
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--tx-settle-ms", type=int, default=DEFAULT_TX_SETTLE_MS)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--rx-common-ctrl-value", type=parse_int, default=0x00000003)
    parser.add_argument("--offsets", type=parse_offsets, default=parse_offsets(DEFAULT_OFFSETS))
    parser.add_argument("--reboot-after", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    run_tag = args.run_tag or default_run_tag()
    json_out = (args.json_out or build_default_json_out(run_tag)).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)

    bit_bin_path = args.bit_bin_path.resolve()
    tx_reference_path = args.tx_reference_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing bitstream payload: {bit_bin_path}")
    if not tx_reference_path.exists():
        raise SystemExit(f"Missing TX reference waveform: {tx_reference_path}")

    reference_cfg = load_reference_config()
    waveform_cfg = make_waveform_config(
        reference_cfg=reference_cfg,
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        tx_attenuation_db=args.tx_attenuation_db,
        rx_gain_db=args.rx_gain_db,
        settle_ms=args.settle_ms,
        rx_rf_port_select=args.rx_rf_port_select,
        tx_rf_port_select=args.tx_rf_port_select,
    )
    cfg = StartOffsetSweepConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        bit_bin_path=str(bit_bin_path),
        tx_reference_path=str(tx_reference_path),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_hold_ms=args.start_hold_ms,
        poll_limit=args.poll_limit,
        poll_delay_ms=args.poll_delay_ms,
        center_frequency_hz=waveform_cfg.center_frequency_hz,
        sample_rate_hz=waveform_cfg.sample_rate_hz,
        symbol_rate_hz=waveform_cfg.symbol_rate_hz,
        samples_per_symbol=waveform_cfg.samples_per_symbol,
        rf_bandwidth_hz=waveform_cfg.rf_bandwidth_hz,
        tx_attenuation_db=waveform_cfg.tx_attenuation_db,
        rx_gain_db=waveform_cfg.rx_gain_db,
        settle_ms=waveform_cfg.settle_ms,
        tx_settle_ms=args.tx_settle_ms,
        rx_rf_port_select=waveform_cfg.rx_rf_port_select,
        tx_rf_port_select=waveform_cfg.tx_rf_port_select,
        rx_common_ctrl_value=args.rx_common_ctrl_value,
        offsets=list(args.offsets),
        reboot_after=bool(args.reboot_after),
        reboot_timeout_s=args.reboot_timeout_s,
    )

    base_probe_cfg = RuntimeBridgeRxHostTxProbeConfig(
        ssh_host=cfg.ssh_host,
        ssh_user=cfg.ssh_user,
        ssh_port=cfg.ssh_port,
        ssh_timeout_s=cfg.ssh_timeout_s,
        iio_uri=cfg.iio_uri,
        raw_bit_path="",
        bit_bin_path=cfg.bit_bin_path,
        tx_reference_path=cfg.tx_reference_path,
        remote_firmware_name=cfg.remote_firmware_name,
        gpreg_base_addr=cfg.gpreg_base_addr,
        expected_id=cfg.expected_id,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.offsets[0],
        rx_decision_mode=0,
        start_hold_ms=cfg.start_hold_ms,
        poll_limit=cfg.poll_limit,
        poll_delay_ms=cfg.poll_delay_ms,
        center_frequency_hz=cfg.center_frequency_hz,
        sample_rate_hz=cfg.sample_rate_hz,
        symbol_rate_hz=cfg.symbol_rate_hz,
        samples_per_symbol=cfg.samples_per_symbol,
        rf_bandwidth_hz=cfg.rf_bandwidth_hz,
        tx_attenuation_db=cfg.tx_attenuation_db,
        rx_gain_db=cfg.rx_gain_db,
        settle_ms=cfg.settle_ms,
        tx_settle_ms=cfg.tx_settle_ms,
        rx_rf_port_select=cfg.rx_rf_port_select,
        tx_rf_port_select=cfg.tx_rf_port_select,
        rx_common_reinit=True,
        rx_common_ctrl_value=cfg.rx_common_ctrl_value,
        reboot_after=cfg.reboot_after,
        reboot_timeout_s=cfg.reboot_timeout_s,
        dmesg_line_count=80,
    )

    bit_payload = bit_bin_path.read_bytes()
    tx_waveform = read_ci16_complex(tx_reference_path)
    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(args.gpreg_base_addr, command_runner=runner)

    payload: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_tag": run_tag,
        "config": asdict(cfg),
        "local_bit_bin": {
            "path": str(bit_bin_path),
            "md5": md5_bytes(bit_payload),
            "size_bytes": len(bit_payload),
        },
        "tx_reference_path": str(tx_reference_path),
        "upload": None,
        "reload": None,
        "rx_common_reinit": None,
        "phy_before": None,
        "phy_after_config": None,
        "results": [],
        "summary": None,
        "cleanup_errors": [],
        "reboot_after": None,
    }

    tx_buffer: Any | None = None
    iio: Any | None = None
    context: Any | None = None
    phy: Any | None = None
    dds: Any | None = None
    phy_snapshot: dict[str, str | None] = {}
    dds_snapshot: dict[str, dict[str, str | None]] = {}

    try:
        remote_path = f"/lib/firmware/{cfg.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_payload, remote_path=remote_path)
        payload["upload"] = read_remote_file_info(runner, remote_path)
        payload["reload"] = trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=cfg.remote_firmware_name,
        )
        payload["rx_common_reinit"] = force_rx_common_ctrl_request(
            runner,
            value=cfg.rx_common_ctrl_value,
        )

        iio = load_iio_module()
        context = iio.Context(cfg.iio_uri)
        phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
        dds = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
        if phy is None or dds is None:
            raise RuntimeError("Expected both `ad9361-phy` and `cf-ad9361-dds-core-lpc` after the runtime reload.")

        phy_snapshot = snapshot_ad9361_state(phy)
        dds_snapshot = snapshot_dds_state(dds)
        payload["phy_before"] = phy_snapshot
        payload["phy_after_config"] = configure_ad9361_bpsk(phy, waveform_cfg)
        disable_dds_tones(dds)
        tx_buffer = transmit_cyclic_buffer(iio, dds, tx_waveform)
        if cfg.tx_settle_ms > 0:
            time.sleep(cfg.tx_settle_ms / 1000.0)

        for offset in cfg.offsets:
            sweep_cfg = replace(base_probe_cfg, start_offset=offset)
            result = attempt_runtime_bringup(io, sweep_cfg)
            row: dict[str, Any] = {"start_offset": offset, "ok": bool(result.get("ok"))}
            if result.get("ok"):
                probe = result["result"]
                row.update(
                    {
                        "received_bits": int(probe.get("received_bits", 0)),
                        "payload_errors": int(probe.get("payload_errors", 0)),
                        "total_errors": int(probe.get("total_errors", 0)),
                        "rx_valid_count": int(probe.get("rx_valid_count", 0)),
                        "tx_valid_count": int(probe.get("tx_valid_count", 0)),
                        "final_status": f"0x{int(probe.get('final_status', 0)):08X}",
                        "timed_out_observed": bool(probe.get("timed_out_observed", False)),
                        "done_observed": bool(probe.get("done_observed", False)),
                        "busy_observed": bool(probe.get("busy_observed", False)),
                    }
                )
            else:
                row.update(
                    {
                        "error_type": result.get("error_type"),
                        "error": result.get("error"),
                        "final_status": result.get("last_status"),
                    }
                )
            payload["results"].append(row)

        payload["summary"] = build_summary(payload["results"])
    finally:
        try:
            if dds_snapshot:
                restore_dds_state(dds, dds_snapshot)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload["cleanup_errors"].append({"stage": "restore_dds_state", "error": str(exc)})
        try:
            if phy_snapshot:
                restore_ad9361_state(phy, phy_snapshot)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload["cleanup_errors"].append({"stage": "restore_ad9361_state", "error": str(exc)})
        try:
            if phy_snapshot:
                enforce_safe_tx_restore_over_ssh(phy_snapshot, args)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload["cleanup_errors"].append({"stage": "ssh_safe_tx_restore", "error": str(exc)})

        if cfg.reboot_after:
            payload["reboot_after"] = try_reboot_to_stock(
                runner,
                host=args.ssh_host,
                user=args.ssh_user,
                password=args.ssh_password,
                port=args.ssh_port,
                ssh_timeout_s=args.ssh_timeout_s,
                iio_uri=args.iio_uri,
                timeout_s=args.reboot_timeout_s,
            )
        io.close()
        runner.close()

    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {json_out}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
