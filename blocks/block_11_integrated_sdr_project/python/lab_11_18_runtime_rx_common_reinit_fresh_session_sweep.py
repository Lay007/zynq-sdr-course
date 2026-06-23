#!/usr/bin/env python3
"""Lab 11.18 - Fresh-session runtime sweep after RX common re-init."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import SshDevMemRegisterIo
from lab_11_12_runtime_fpga_manager_reload import (
    md5_bytes,
    read_remote_file_info,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)
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
from runtime_rx_common import force_rx_common_ctrl_request


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REBOOT_TIMEOUT_S = 120.0
DEFAULT_START_OFFSETS = "32"
DEFAULT_RX_GAINS_DB = "10,15,20,25,30,35"
DEFAULT_TX_ATTENUATIONS_DB = "-50"
DEFAULT_TX_PHASE_DEGS = "0"


@dataclass(frozen=True)
class FreshSessionSweepConfig:
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
    rf_bandwidth_hz: int
    settle_ms: int
    tx_settle_ms: int
    rx_rf_port_select: str
    tx_rf_port_select: str
    rx_common_ctrl_value: int
    start_offsets: list[int]
    rx_gains_db: list[float]
    tx_attenuations_db: list[float]
    tx_phase_degs: list[float]
    reboot_timeout_s: float


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def build_default_json_out(run_tag: str) -> Path:
    return ROOT / "docs" / "assets" / f"lab118_runtime_rx_common_reinit_fresh_session_sweep_{run_tag}.json"


def parse_int_list(value: str) -> list[int]:
    items = [int(chunk.strip(), 0) for chunk in value.split(",") if chunk.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one integer value.")
    return items


def parse_float_list(value: str) -> list[float]:
    items = [float(chunk.strip()) for chunk in value.split(",") if chunk.strip()]
    if not items:
        raise argparse.ArgumentTypeError("Expected at least one float value.")
    return items


def safe_restore_over_ssh(snapshot: dict[str, str | None], cfg: FreshSessionSweepConfig, password: str) -> None:
    class Args:
        ssh_host = cfg.ssh_host
        ssh_user = cfg.ssh_user
        ssh_password = password
        ssh_port = cfg.ssh_port
        ssh_timeout_s = cfg.ssh_timeout_s

    enforce_safe_tx_restore_over_ssh(snapshot, Args)


def score_entry(entry: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(entry.get("received_bits") or 0),
        -int(entry.get("payload_errors") or 10**9),
        -int(entry.get("total_errors") or 10**9),
        int(entry.get("rx_valid_count") or 0),
    )


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    best = max(results, key=score_entry)
    full_frames = [row for row in results if int(row.get("received_bits") or 0) == 281]
    zero_error = [
        row
        for row in full_frames
        if int(row.get("payload_errors") or 10**9) == 0 and int(row.get("total_errors") or 10**9) == 0
    ]
    if zero_error:
        conclusion = "At least one fresh-session runtime point reached a full zero-error frame."
    elif full_frames:
        conclusion = (
            "Fresh-session runtime reloads reproducibly reach full-frame reception on some points, "
            "but BER is still above zero."
        )
    else:
        conclusion = (
            "No fresh-session runtime point reached a full frame in this sweep."
        )
    return {
        "best": best,
        "full_frame_results": full_frames,
        "zero_error_results": zero_error,
        "conclusion": conclusion,
    }


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
    parser.add_argument("--tx-attenuations-db", type=parse_float_list, default=parse_float_list(DEFAULT_TX_ATTENUATIONS_DB))
    parser.add_argument("--tx-phase-degs", type=parse_float_list, default=parse_float_list(DEFAULT_TX_PHASE_DEGS))
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--tx-settle-ms", type=int, default=DEFAULT_TX_SETTLE_MS)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--rx-common-ctrl-value", type=parse_int, default=0x00000003)
    parser.add_argument("--start-offsets", type=parse_int_list, default=parse_int_list(DEFAULT_START_OFFSETS))
    parser.add_argument("--rx-gains-db", type=parse_float_list, default=parse_float_list(DEFAULT_RX_GAINS_DB))
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser


def run_one_point(
    *,
    cfg: FreshSessionSweepConfig,
    password: str,
    bit_payload: bytes,
    tx_waveform: Any,
    reference_cfg: dict[str, Any],
    point_index: int,
    start_offset: int,
    rx_gain_db: float,
    tx_attenuation_db: float,
    tx_phase_deg: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "point_index": point_index,
        "start_offset": start_offset,
        "rx_gain_db": rx_gain_db,
        "tx_attenuation_db": tx_attenuation_db,
        "tx_phase_deg": tx_phase_deg,
        "rx_common_reinit": None,
        "bringup": None,
        "reboot_after": None,
        "cleanup_errors": [],
    }

    runner = ParamikoCommandRunner(
        host=cfg.ssh_host,
        user=cfg.ssh_user,
        password=password,
        port=cfg.ssh_port,
        key_path=None,
        timeout_s=cfg.ssh_timeout_s,
    )
    io = SshDevMemRegisterIo(cfg.gpreg_base_addr, command_runner=runner)
    tx_buffer: Any | None = None
    iio: Any | None = None
    context: Any | None = None
    phy: Any | None = None
    dds: Any | None = None
    phy_snapshot: dict[str, str | None] = {}
    dds_snapshot: dict[str, dict[str, str | None]] = {}

    try:
        waveform_cfg = make_waveform_config(
            reference_cfg=reference_cfg,
            center_frequency_hz=cfg.center_frequency_hz,
            sample_rate_hz=cfg.sample_rate_hz,
            rf_bandwidth_hz=cfg.rf_bandwidth_hz,
            tx_attenuation_db=tx_attenuation_db,
            rx_gain_db=rx_gain_db,
            settle_ms=cfg.settle_ms,
            rx_rf_port_select=cfg.rx_rf_port_select,
            tx_rf_port_select=cfg.tx_rf_port_select,
        )
        tx_phase_rad = np.deg2rad(tx_phase_deg)
        rotated_waveform = tx_waveform * np.exp(1j * tx_phase_rad)
        probe_cfg = RuntimeBridgeRxHostTxProbeConfig(
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
            start_offset=start_offset,
            rx_decision_mode=0,
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
            tx_settle_ms=cfg.tx_settle_ms,
            rx_rf_port_select=waveform_cfg.rx_rf_port_select,
            tx_rf_port_select=waveform_cfg.tx_rf_port_select,
            rx_common_reinit=True,
            rx_common_ctrl_value=cfg.rx_common_ctrl_value,
            reboot_after=True,
            reboot_timeout_s=cfg.reboot_timeout_s,
            dmesg_line_count=80,
        )

        remote_path = f"/lib/firmware/{cfg.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_payload, remote_path=remote_path)
        row["upload"] = read_remote_file_info(runner, remote_path)
        row["reload"] = trigger_fpga_manager_reload(
            runner,
            remote_firmware_name=cfg.remote_firmware_name,
        )
        row["rx_common_reinit"] = force_rx_common_ctrl_request(
            runner,
            value=cfg.rx_common_ctrl_value,
        )

        iio = load_iio_module()
        context = iio.Context(cfg.iio_uri)
        phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
        dds = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
        if phy is None or dds is None:
            raise RuntimeError("Expected `ad9361-phy` and `cf-ad9361-dds-core-lpc` after runtime reload.")

        phy_snapshot = snapshot_ad9361_state(phy)
        dds_snapshot = snapshot_dds_state(dds)
        row["phy_before"] = phy_snapshot
        row["phy_after_config"] = configure_ad9361_bpsk(phy, waveform_cfg)
        disable_dds_tones(dds)
        tx_buffer = transmit_cyclic_buffer(iio, dds, rotated_waveform)
        if cfg.tx_settle_ms > 0:
            time.sleep(cfg.tx_settle_ms / 1000.0)

        bringup = attempt_runtime_bringup(io, probe_cfg)
        row["bringup"] = bringup
        if bringup.get("ok"):
            result = bringup["result"]
            row.update(
                {
                    "ok": True,
                    "received_bits": int(result.get("received_bits", 0)),
                    "payload_errors": int(result.get("payload_errors", 0)),
                    "total_errors": int(result.get("total_errors", 0)),
                    "rx_valid_count": int(result.get("rx_valid_count", 0)),
                    "tx_valid_count": int(result.get("tx_valid_count", 0)),
            "timed_out_observed": bool(result.get("timed_out_observed", False)),
            "final_status": f"0x{int(result.get('final_status', 0)):08X}",
            "capture_peak_abs_max_q14": ((result.get("capture_debug") or {}).get("capture_peak_abs_max_q14")),
            "ber_total": result.get("ber_total"),
            "ber_payload": result.get("ber_payload"),
        }
    )
        else:
            row.update(
                {
                    "ok": False,
                    "error_type": bringup.get("error_type"),
                    "error": bringup.get("error"),
                    "last_status": bringup.get("last_status"),
                }
            )
    except Exception as exc:  # pragma: no cover - hardware dependent
        row["ok"] = False
        row["fatal_error"] = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        try:
            if dds_snapshot:
                restore_dds_state(dds, dds_snapshot)
        except Exception as exc:  # pragma: no cover - hardware dependent
            row["cleanup_errors"].append({"stage": "restore_dds_state", "error": str(exc)})
        try:
            if phy_snapshot:
                restore_ad9361_state(phy, phy_snapshot)
        except Exception as exc:  # pragma: no cover - hardware dependent
            row["cleanup_errors"].append({"stage": "restore_ad9361_state", "error": str(exc)})
        try:
            if phy_snapshot:
                safe_restore_over_ssh(phy_snapshot, cfg, password)
        except Exception as exc:  # pragma: no cover - hardware dependent
            row["cleanup_errors"].append({"stage": "ssh_safe_tx_restore", "error": str(exc)})
        try:
            row["reboot_after"] = try_reboot_to_stock(
                runner,
                host=cfg.ssh_host,
                user=cfg.ssh_user,
                password=password,
                port=cfg.ssh_port,
                ssh_timeout_s=cfg.ssh_timeout_s,
                iio_uri=cfg.iio_uri,
                timeout_s=cfg.reboot_timeout_s,
            )
        finally:
            io.close()
            runner.close()

    return row


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

    cfg = FreshSessionSweepConfig(
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
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        settle_ms=args.settle_ms,
        tx_settle_ms=args.tx_settle_ms,
        rx_rf_port_select=args.rx_rf_port_select,
        tx_rf_port_select=args.tx_rf_port_select,
        rx_common_ctrl_value=args.rx_common_ctrl_value,
        start_offsets=list(args.start_offsets),
        rx_gains_db=list(args.rx_gains_db),
        tx_attenuations_db=list(args.tx_attenuations_db),
        tx_phase_degs=list(args.tx_phase_degs),
        reboot_timeout_s=args.reboot_timeout_s,
    )

    reference_cfg = load_reference_config()
    bit_payload = bit_bin_path.read_bytes()
    tx_waveform = read_ci16_complex(tx_reference_path)
    points = list(itertools.product(cfg.start_offsets, cfg.rx_gains_db, cfg.tx_attenuations_db, cfg.tx_phase_degs))

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
        "point_count": len(points),
        "results": [],
        "summary": None,
    }

    for point_index, (start_offset, rx_gain_db, tx_attenuation_db, tx_phase_deg) in enumerate(points, start=1):
        row = run_one_point(
            cfg=cfg,
            password=args.ssh_password,
            bit_payload=bit_payload,
            tx_waveform=tx_waveform,
            reference_cfg=reference_cfg,
            point_index=point_index,
            start_offset=start_offset,
            rx_gain_db=rx_gain_db,
            tx_attenuation_db=tx_attenuation_db,
            tx_phase_deg=tx_phase_deg,
        )
        payload["results"].append(row)
        payload["summary"] = build_summary(payload["results"])
        json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    payload["summary"] = build_summary(payload["results"])
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {json_out}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
