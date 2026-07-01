#!/usr/bin/env python3
"""Lab 11.27 - Runtime QPSK digital-loopback BER on the dual-modem bridge.

Same runtime plane as the BPSK bring-up of Lab 11.19 (upload the overlay, reload
via the FPGA manager, configure the AD9361, run the self-timed BER core through
the DAC->ADC digital loopback, reboot to stock), but flips gp_ctrl[4]=1 to select
the QPSK core added to the course bridge. gp_frame_bit_count is reinterpreted as
the QPSK *symbol* count (2 bits/symbol) and gp_start_offset is swept until a full
frame decodes at BER=0 — exactly the host-retry strategy the BPSK path uses.

The AD9361 setup is modulation-agnostic (it only shuttles I/Q), so the BPSK
configuration is reused unchanged; only the bridge's mode bit and the frame
semantics differ.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
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
    DEFAULT_HOST,
    DEFAULT_IIO_URI,
    DEFAULT_PASSWORD,
    DEFAULT_POLL_DELAY_MS,
    DEFAULT_POLL_LIMIT,
    DEFAULT_PORT,
    DEFAULT_RF_BANDWIDTH_HZ,
    DEFAULT_RX_GAIN_DB,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_REMOTE_FIRMWARE_NAME,
    DEFAULT_SETTLE_MS,
    DEFAULT_START_HOLD_MS,
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
from lab_11_8_axi_gpreg_bpsk_bringup import SshDevMemRegisterIo
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
DEFAULT_JSON_STEM = "lab1127_runtime_qpsk_digital_loopback"
DEFAULT_REBOOT_TIMEOUT_S = 120.0

QPSK_MODE_BITS = 0x10          # gp_ctrl[4] selects the QPSK core
DEFAULT_SYMBOL_COUNT = 140     # QPSK symbols == the loopback frame the sim proved
# The QPSK BER counter uses fixed alignment (no preamble sync), so the working
# sampling phase is found by sweeping start_offset like the BPSK host retry.
DEFAULT_START_OFFSETS = list(range(96, 132))


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def parse_offsets(value: str) -> list[int]:
    offsets = [int(chunk.strip(), 0) for chunk in value.split(",") if chunk.strip()]
    if not offsets:
        raise argparse.ArgumentTypeError("Expected at least one start_offset value.")
    return offsets


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
    parser.add_argument("--symbol-count", type=int, default=DEFAULT_SYMBOL_COUNT)
    parser.add_argument("--start-offsets", type=parse_offsets,
                        default=DEFAULT_START_OFFSETS,
                        help="comma-separated start_offset values to sweep")
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
    # Rebinding the runtime DDS/ADC platform drivers is REQUIRED for the digital
    # loopback: without it the fabric ADC capture tap reads stale/railed data
    # (gp_capture_debug pinned at full-scale 0x3FFF) and nothing decodes. Default on.
    parser.add_argument("--rebind-runtime-dds-driver", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--rebind-runtime-adc-driver", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--runtime-dds-ratecntrl", type=parse_int, default=None)
    parser.add_argument("--reboot-after", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--reboot-timeout-s", type=float, default=DEFAULT_REBOOT_TIMEOUT_S)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser


def qpsk_ber_once(runner, base_addr: int, symbol_count: int, offset: int,
                  poll: int = 300) -> dict[str, Any]:
    """Run ONE QPSK BER burst entirely on the device with a single SSH command.

    Batching the whole gpreg sequence (frame/offset writes, start pulse, on-device
    status poll, counter read-back, clear_done) into one remote `sh` invocation
    keeps the sweep from opening hundreds of SSH channels — the failure mode that
    exhausted dropbear when each devmem op was its own exec_command.
    """
    a_ctrl = f"0x{base_addr + 0x404:X}"
    a_frame = f"0x{base_addr + 0x444:X}"
    a_pre = f"0x{base_addr + 0x484:X}"
    a_off = f"0x{base_addr + 0x4C4:X}"
    a_stat = f"0x{base_addr + 0x408:X}"
    a_recv = f"0x{base_addr + 0x448:X}"
    a_errc = f"0x{base_addr + 0x488:X}"
    dm = "/sbin/devmem"
    # gp_ctrl[4]=0x10 selects QPSK; start=0x11 (mode+start), release=0x10,
    # clear_done=0x12. Status bit2=done, bit3=timeout.
    cmd = (
        f"{dm} {a_frame} 32 {symbol_count}; {dm} {a_pre} 32 0; {dm} {a_off} 32 {offset}; "
        f"{dm} {a_ctrl} 32 0x10; {dm} {a_ctrl} 32 0x11; {dm} {a_ctrl} 32 0x10; "
        f"i=0; s=0; while [ $i -lt {poll} ]; do s=$({dm} {a_stat} 32); d=$((s)); "
        f"if [ $((d & 4)) -ne 0 ]; then break; fi; if [ $((d & 8)) -ne 0 ]; then break; fi; "
        f"i=$((i+1)); done; r=$({dm} {a_recv} 32); e=$({dm} {a_errc} 32); "
        f"{dm} {a_ctrl} 32 0x12; {dm} {a_ctrl} 32 0x10; "
        f"echo RESULT off={offset} recv=$r err=$e status=$s polls=$i"
    )
    rc, out, err = runner(cmd)
    row: dict[str, Any] = {"start_offset": offset, "ok": rc == 0}
    if rc != 0:
        row["error"] = (err or out or "").strip()[:200]
        return row
    line = next((ln for ln in out.splitlines() if ln.startswith("RESULT")), "")
    fields = dict(tok.split("=", 1) for tok in line.split()[1:] if "=" in tok)
    recv = int(fields.get("recv", "0"), 16)
    errc = int(fields.get("err", "0"), 16)
    status = int(fields.get("status", "0"), 16)
    row["received_symbols"] = recv
    row["total_bit_errors"] = (errc >> 16) & 0xFFFF
    row["payload_errors"] = errc & 0xFFFF
    row["timed_out"] = bool(status & 0x8)
    row["status"] = f"0x{status:08X}"
    row["polls"] = int(fields.get("polls", "0"))
    return row


def summarize_sweep(sweep: list[dict[str, Any]], symbol_count: int) -> dict[str, Any]:
    full = [r for r in sweep if int(r.get("received_symbols") or 0) == symbol_count]
    zero = [r for r in full if int(r.get("total_bit_errors") or 0) == 0]
    best = None
    if zero:
        best = min(zero, key=lambda r: int(r["start_offset"]))
    elif full:
        best = min(full, key=lambda r: int(r["total_bit_errors"]))

    if zero:
        conclusion = (
            f"QPSK digital loopback reached BER=0: {symbol_count} symbols / "
            f"{2 * symbol_count} bits recovered with 0 errors at start_offset="
            f"{best['start_offset']}."
        )
    elif full:
        conclusion = (
            "QPSK digital loopback recovered a full frame but with residual bit errors; "
            "sampling phase is aligned, remaining errors are a tuning problem."
        )
    else:
        conclusion = "QPSK digital loopback did not reach a full frame at any swept start_offset."

    return {
        "mode": "qpsk_digital_loopback",
        "symbol_count": symbol_count,
        "bit_count": 2 * symbol_count,
        "full_frame_offsets": [int(r["start_offset"]) for r in full],
        "zero_error_offsets": [int(r["start_offset"]) for r in zero],
        "best": best,
        "conclusion": conclusion,
    }


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    bit_bin_path = args.bit_bin_path.resolve()
    if not bit_bin_path.exists():
        raise SystemExit(f"Missing runtime payload: {bit_bin_path}")

    run_tag = args.run_tag or default_run_tag()
    json_out = (args.json_out or (DOC_ASSET_DIR / f"{DEFAULT_JSON_STEM}_{run_tag}.json")).resolve()
    json_out.parent.mkdir(parents=True, exist_ok=True)

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

    # One shared probe config; start_offset is replaced per sweep step. QPSK mode
    # bit set, preamble_count=0 (the QPSK counter has no preamble sync), and
    # frame_bit_count carries the QPSK symbol count.
    base_probe_cfg = RuntimeBridgeRxHostTxProbeConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        raw_bit_path="",
        bit_bin_path=str(bit_bin_path),
        tx_reference_path=str(DEFAULT_TX_REFERENCE_PATH),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.symbol_count,
        preamble_count=0,
        start_offset=args.start_offsets[0],
        rx_decision_mode=0,
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
        tx_settle_ms=0,
        rx_rf_port_select=waveform_cfg.rx_rf_port_select,
        tx_rf_port_select=waveform_cfg.tx_rf_port_select,
        rx_common_reinit=True,
        rx_common_ctrl_value=args.rx_common_ctrl_value,
        reboot_after=bool(args.reboot_after),
        reboot_timeout_s=args.reboot_timeout_s,
        dmesg_line_count=80,
        mod_select_bits=QPSK_MODE_BITS,
    )

    bit_payload = bit_bin_path.read_bytes()
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
        "timestamp_utc": iso_now(),
        "run_tag": run_tag,
        "waveform_config": asdict(waveform_cfg),
        "bitstream": {
            "path": str(bit_bin_path),
            "size_bytes": len(bit_payload),
            "md5": md5_bytes(bit_payload),
        },
        "symbol_count": args.symbol_count,
        "start_offsets": args.start_offsets,
        "stock_context_before": None,
        "upload": None,
        "reload": None,
        "gpreg_after_reload": None,
        "sweep": [],
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
            lambda: probe_iio_context_summary(args.iio_uri),
        )

        remote_path = f"/lib/firmware/{args.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_payload, remote_path=remote_path)
        payload["upload"] = read_remote_file_info(runner, remote_path)
        payload["reload"] = trigger_fpga_manager_reload(
            runner, remote_firmware_name=args.remote_firmware_name,
        )
        payload["gpreg_after_reload"] = probe_gpreg_id(io)
        force_rx_common_ctrl_request(runner, value=args.rx_common_ctrl_value)

        if args.rebind_runtime_dds_driver:
            rebind_platform_driver(runner, driver_name=DEFAULT_DDS_DRIVER_NAME,
                                   device_name=DEFAULT_DDS_DEVICE_NAME)
        if args.rebind_runtime_adc_driver:
            rebind_platform_driver(runner, driver_name=DEFAULT_ADC_DRIVER_NAME,
                                   device_name=DEFAULT_ADC_DEVICE_NAME)
        if args.runtime_dds_ratecntrl is not None:
            write_runtime_dds_ratecntrl(runner, args.runtime_dds_ratecntrl)

        iio = load_iio_module()
        context = iio.Context(args.iio_uri)
        phy = next((d for d in context.devices if d.name == "ad9361-phy"), None)
        if phy is None:
            raise RuntimeError("Expected `ad9361-phy` after runtime reload.")

        phy_snapshot = snapshot_ad9361_state(phy)
        configure_ad9361_bpsk(phy, waveform_cfg)   # modulation-agnostic I/Q setup
        dds = next((d for d in context.devices if d.name == "cf-ad9361-dds-core-lpc"), None)
        if dds is not None:
            disable_dds_tones(dds)

        sig = io.read32(0x508)   # gp_signature_in; bridge keeps the BPSK identity
        payload["bridge_signature"] = f"0x{sig:08X}"
        if sig != args.expected_id:
            raise RuntimeError(
                f"Unexpected bridge signature 0x{sig:08X}; expected 0x{args.expected_id:08X}.")

        for offset in args.start_offsets:
            try:
                row = qpsk_ber_once(io.runner, args.gpreg_base_addr, args.symbol_count, offset)
            except Exception as exc:  # pragma: no cover - keep sweeping / reach the reboot
                row = {"start_offset": offset, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
            payload["sweep"].append(row)
            if row.get("received_symbols") == args.symbol_count and row.get("total_bit_errors") == 0:
                break   # BER=0 found; no need to sweep further
    finally:
        try:
            if phy is not None and phy_snapshot:
                restore_ad9361_state(phy, phy_snapshot)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload.setdefault("cleanup_errors", []).append(
                {"stage": "restore_ad9361_state", "error": str(exc)})
        try:
            if phy_snapshot:
                class _Args:
                    ssh_host = args.ssh_host
                    ssh_user = args.ssh_user
                    ssh_password = args.ssh_password
                    ssh_port = args.ssh_port
                    ssh_timeout_s = args.ssh_timeout_s
                enforce_safe_tx_restore_over_ssh(phy_snapshot, _Args)
        except Exception as exc:  # pragma: no cover - hardware dependent
            payload.setdefault("cleanup_errors", []).append(
                {"stage": "enforce_safe_tx_restore_over_ssh", "error": str(exc)})

        if args.reboot_after:
            payload["reboot_after"] = safe_probe(
                "try_reboot_to_stock",
                lambda: try_reboot_to_stock(
                    runner, host=args.ssh_host, user=args.ssh_user,
                    password=args.ssh_password, port=args.ssh_port,
                    ssh_timeout_s=args.ssh_timeout_s, iio_uri=args.iio_uri,
                    timeout_s=args.reboot_timeout_s,
                ),
            )
        try:
            runner.close()
        except Exception as exc:  # pragma: no cover - connection may drop after reboot
            payload.setdefault("cleanup_errors", []).append(
                {"stage": "runner.close", "error": str(exc)})

    payload["summary"] = summarize_sweep(payload["sweep"], args.symbol_count)
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Lab 11.27 - Runtime QPSK digital-loopback BER")
    print(f"JSON: {json_out}")
    print(f"Conclusion: {payload['summary'].get('conclusion')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
