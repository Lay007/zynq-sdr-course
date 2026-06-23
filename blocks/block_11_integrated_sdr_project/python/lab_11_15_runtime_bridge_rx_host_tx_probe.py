#!/usr/bin/env python3
"""Lab 11.15 - Runtime `bridge_rx_only` witness using stock TX and gpreg RX counters."""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import time
from types import ModuleType
from typing import Any

import numpy as np

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner, parse_int
from lab_11_8_axi_gpreg_bpsk_bringup import (
    BringupConfig,
    BringupTimeoutError,
    SshDevMemRegisterIo,
    register_snapshot,
    run_bringup,
)
from lab_11_9_rf_discovery_sweep import read_ad9361_state
from lab_11_11_iio_gpreg_contention_probe import read_dmesg_tail
from lab_11_12_runtime_fpga_manager_reload import (
    md5_bytes,
    probe_gpreg_id,
    read_remote_file_info,
    run_remote,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)
from lab_11_13_stock_vs_runtime_rx_compare import probe_iio_context_summary, try_reboot_to_stock
from lab_11_14_stock_shell_bpsk_ota import (
    WaveformConfig,
    configure_ad9361_bpsk,
    disable_dds_tones,
    enforce_safe_tx_restore_over_ssh,
    restore_ad9361_state,
    restore_dds_state,
    snapshot_ad9361_state,
    snapshot_dds_state,
    transmit_cyclic_buffer,
)


ROOT = Path(__file__).resolve().parents[3]
DOC_ASSET_DIR = ROOT / "docs" / "assets"
PACKAGE_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference"
DEFAULT_RAW_BIT_PATH = (
    ROOT
    / "hardware"
    / "7020_ad936x_sdr"
    / "hdl"
    / "course_bpsk_fmcomms2_zc702"
    / "build"
    / "course_bpsk_fmcomms2_zc702.runs"
    / "impl_1"
    / "system_top.bit"
)
DEFAULT_BIT_BIN_PATH = ROOT / "tmp" / "bridge_rx_only.wordswap.bit.bin"
DEFAULT_TX_REFERENCE_PATH = PACKAGE_DIR / "end_to_end_bpsk_reference_v1_tx_reference.ci16"
DEFAULT_REMOTE_FIRMWARE_NAME = "course_bpsk_fmcomms2_zc702_runtime.bit.bin"
DEFAULT_IIO_URI = "ip:192.168.40.1"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_TIMEOUT_S = 10.0
DEFAULT_BASE_ADDR = 0x79040000
DEFAULT_EXPECTED_ID = 0x4250534B
DEFAULT_FRAME_BIT_COUNT = 281
DEFAULT_PREAMBLE_COUNT = 25
DEFAULT_START_OFFSET = 62
DEFAULT_START_HOLD_MS = 5
DEFAULT_POLL_LIMIT = 128
DEFAULT_POLL_DELAY_MS = 20
DEFAULT_CENTER_FREQUENCY_HZ = 915_000_000
DEFAULT_SAMPLE_RATE_HZ = 3_840_000
DEFAULT_RF_BANDWIDTH_HZ = 2_000_000
DEFAULT_TX_ATTENUATION_DB = -50.0
DEFAULT_RX_GAIN_DB = 35.0
DEFAULT_SETTLE_MS = 150
DEFAULT_TX_SETTLE_MS = 250
DEFAULT_REBOOT_TIMEOUT_S = 120.0
DEFAULT_DMESG_LINE_COUNT = 80
Q15_SCALE = 32767.0


@dataclass(frozen=True)
class RuntimeBridgeRxHostTxProbeConfig:
    ssh_host: str
    ssh_user: str
    ssh_port: int
    ssh_timeout_s: float
    iio_uri: str
    raw_bit_path: str
    bit_bin_path: str
    tx_reference_path: str
    remote_firmware_name: str
    gpreg_base_addr: int
    expected_id: int
    frame_bit_count: int
    preamble_count: int
    start_offset: int
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
    reboot_after: bool
    reboot_timeout_s: float
    dmesg_line_count: int


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def build_default_json_out(run_tag: str) -> Path:
    return DOC_ASSET_DIR / f"lab115_runtime_bridge_rx_host_tx_probe_{run_tag}.json"


def load_bit_bin_module() -> ModuleType:
    module_path = ROOT / "hardware" / "7020_ad936x_sdr" / "boot" / "build_system_bit_bin.py"
    spec = importlib.util.spec_from_file_location("build_system_bit_bin", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load bitstream converter from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reference_config() -> dict[str, Any]:
    return json.loads((PACKAGE_DIR / "config.json").read_text(encoding="utf-8"))


def read_ci16_complex(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype="<i2")
    if raw.size % 2 != 0:
        raise ValueError(f"Expected even CI16 sample count in {path}")
    return raw[0::2].astype(np.float64) / Q15_SCALE + 1j * raw[1::2].astype(np.float64) / Q15_SCALE


def summarize_complex_waveform(x: np.ndarray) -> dict[str, Any]:
    return {
        "complex_sample_count": int(x.size),
        "peak_abs": float(np.max(np.abs(x), initial=0.0)),
        "rms_abs": float(np.sqrt(np.mean(np.abs(x) ** 2))) if x.size else 0.0,
    }


def make_waveform_config(
    *,
    reference_cfg: dict[str, Any],
    center_frequency_hz: int,
    sample_rate_hz: int,
    rf_bandwidth_hz: int,
    tx_attenuation_db: float,
    rx_gain_db: float,
    settle_ms: int,
    rx_rf_port_select: str,
    tx_rf_port_select: str,
) -> WaveformConfig:
    samples_per_symbol = int(reference_cfg["samples_per_symbol"])
    if sample_rate_hz % samples_per_symbol != 0:
        raise ValueError("sample_rate_hz must be divisible by samples_per_symbol for the runtime witness.")
    preamble_bits = reference_cfg["preamble_bits"]
    payload_bit_count = DEFAULT_FRAME_BIT_COUNT - len(preamble_bits)
    return WaveformConfig(
        center_frequency_hz=center_frequency_hz,
        sample_rate_hz=sample_rate_hz,
        symbol_rate_hz=sample_rate_hz // samples_per_symbol,
        samples_per_symbol=samples_per_symbol,
        rf_bandwidth_hz=rf_bandwidth_hz,
        payload_bit_count=payload_bit_count,
        rolloff=float(reference_cfg["rolloff"]),
        rrc_span_symbols=int(reference_cfg["rrc_span_symbols"]),
        tx_amplitude=float(reference_cfg["tx_amplitude"]),
        leading_silence_samples=int(reference_cfg["leading_silence_samples"]),
        trailing_silence_samples=int(reference_cfg["trailing_silence_samples"]),
        capture_sample_count=0,
        tx_attenuation_db=tx_attenuation_db,
        rx_gain_db=rx_gain_db,
        settle_ms=settle_ms,
        rx_rf_port_select=rx_rf_port_select,
        tx_rf_port_select=tx_rf_port_select,
        synthetic_test=False,
        synthetic_cfo_hz=0.0,
        synthetic_phase_offset_rad=0.0,
        synthetic_timing_offset_samples=0,
        synthetic_noise_rms=0.0,
        seed=int(reference_cfg["seed"]),
    )


def safe_probe(label: str, fn: Any) -> dict[str, Any]:
    try:
        return {"ok": True, "result": fn()}
    except Exception as exc:  # pragma: no cover - hardware dependent
        return {
            "ok": False,
            "label": label,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def attempt_runtime_bringup(io: SshDevMemRegisterIo, cfg: RuntimeBridgeRxHostTxProbeConfig) -> dict[str, Any]:
    bringup_cfg = BringupConfig(
        backend="ssh-devmem",
        base_addr=cfg.gpreg_base_addr,
        frame_bit_count=cfg.frame_bit_count,
        preamble_count=cfg.preamble_count,
        start_offset=cfg.start_offset,
        start_hold_ms=cfg.start_hold_ms,
        poll_limit=cfg.poll_limit,
        poll_delay_ms=cfg.poll_delay_ms,
        expected_id=cfg.expected_id,
        clear_done=True,
        max_total_errors=None,
        max_payload_errors=None,
    )
    try:
        result = asdict(run_bringup(io, bringup_cfg))
        return {"ok": True, "result": result}
    except BringupTimeoutError as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "poll_reads": exc.poll_reads,
            "last_status": f"0x{exc.last_status:08X}",
            "status_trace": [f"0x{value:08X}" for value in exc.status_trace],
            "register_snapshot": register_snapshot(io, cfg.gpreg_base_addr),
        }
    except Exception as exc:  # pragma: no cover - hardware dependent
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "register_snapshot": register_snapshot(io, cfg.gpreg_base_addr),
        }


def build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    idle = payload.get("idle_bringup") or {}
    host_tx = payload.get("host_tx_bringup") or {}

    def result_value(stage: dict[str, Any], key: str) -> int | None:
        if not stage.get("ok"):
            return None
        result = stage.get("result") or {}
        value = result.get(key)
        if value is None:
            return None
        return int(value)

    idle_rx_valid = result_value(idle, "rx_valid_count")
    host_tx_rx_valid = result_value(host_tx, "rx_valid_count")
    host_tx_tx_valid = result_value(host_tx, "tx_valid_count")
    host_tx_received = result_value(host_tx, "received_bits")
    idle_adc_input_debug = ((idle.get("result") or {}).get("adc_input_debug")) if idle.get("ok") else None
    host_tx_adc_input_debug = ((host_tx.get("result") or {}).get("adc_input_debug")) if host_tx.get("ok") else None
    idle_capture_debug = ((idle.get("result") or {}).get("capture_debug")) if idle.get("ok") else None
    host_tx_capture_debug = ((host_tx.get("result") or {}).get("capture_debug")) if host_tx.get("ok") else None
    adc_input_clk_counter_advanced: bool | None = None

    if isinstance(idle_adc_input_debug, dict) and isinstance(host_tx_adc_input_debug, dict):
        idle_counter = idle_adc_input_debug.get("adc_input_clk_counter_lsb16")
        host_counter = host_tx_adc_input_debug.get("adc_input_clk_counter_lsb16")
        if isinstance(idle_counter, int) and isinstance(host_counter, int):
            adc_input_clk_counter_advanced = ((host_counter - idle_counter) & 0xFFFF) != 0

    if host_tx_rx_valid is not None and host_tx_rx_valid > 0:
        conclusion = (
            "`bridge_rx_only` sees non-zero RX-valid traffic during host-driven stock TX, "
            "so the runtime overlay can still observe the RX sample tap in this mode."
        )
    elif (
        isinstance(host_tx_adc_input_debug, dict)
        and bool(host_tx_adc_input_debug.get("adc_input_valid_seen_any"))
        and not (
            isinstance(host_tx_capture_debug, dict)
            and bool(host_tx_capture_debug.get("capture_valid_seen_any"))
        )
    ):
        conclusion = (
            "The runtime overlay still sees raw `axi_ad9361` RX-valid activity before "
            "`util_ad9361_adc_fifo`, but that activity never reaches the FIFO output tap."
        )
    elif (
        isinstance(host_tx_capture_debug, dict)
        and bool(host_tx_capture_debug.get("capture_valid_seen_any"))
        and int(host_tx_capture_debug.get("capture_valid_count_lsb15", 0)) > 0
    ):
        conclusion = (
            "`bridge_rx_only` sees raw capture-valid activity on the RX tap, but the gated "
            "`rx_valid_count` used by the bridge still remains zero."
        )
    elif idle_rx_valid is not None and idle_rx_valid > 0:
        conclusion = (
            "`bridge_rx_only` already sees RX-valid traffic without external host TX, "
            "so the RX-valid path itself is alive after runtime reload."
        )
    elif (
        isinstance(host_tx_adc_input_debug, dict)
        and bool(host_tx_adc_input_debug.get("adc_input_reset_asserted_current"))
    ):
        conclusion = (
            "The raw `axi_ad9361` RX input-side debug still reports reset asserted after "
            "runtime reload, so the blocker sits before the FIFO output domain."
        )
    elif adc_input_clk_counter_advanced is False:
        conclusion = (
            "The raw `axi_ad9361` RX input-side heartbeat did not advance between the idle "
            "and host-TX probes, pointing to an input-clock or persistent-reset problem."
        )
    elif (
        adc_input_clk_counter_advanced
        and isinstance(host_tx_adc_input_debug, dict)
        and not bool(host_tx_adc_input_debug.get("adc_input_valid_seen_any"))
    ):
        conclusion = (
            "The raw `axi_ad9361` RX input-side heartbeat is alive after runtime reload, "
            "but it never asserts `adc_valid_i0`, so the starvation starts upstream of "
            "`util_ad9361_adc_fifo`."
        )
    elif (
        isinstance(host_tx_capture_debug, dict)
        and not bool(host_tx_capture_debug.get("capture_valid_seen_any"))
    ):
        conclusion = (
            "`bridge_rx_only` still sees no raw capture-valid activity at the RX tap even during "
            "host-driven stock TX, so the blocker sits upstream of the BER core counters."
        )
    else:
        conclusion = (
            "`bridge_rx_only` still leaves `rx_valid_count` at zero in this runtime probe, "
            "so the next blocker remains inside the live RX-valid path rather than the stock TX witness."
        )

    return {
        "idle_rx_valid_count": idle_rx_valid,
        "host_tx_rx_valid_count": host_tx_rx_valid,
        "host_tx_tx_valid_count": host_tx_tx_valid,
        "host_tx_received_bits": host_tx_received,
        "idle_adc_input_debug": idle_adc_input_debug,
        "host_tx_adc_input_debug": host_tx_adc_input_debug,
        "adc_input_clk_counter_advanced": adc_input_clk_counter_advanced,
        "idle_capture_debug": idle_capture_debug,
        "host_tx_capture_debug": host_tx_capture_debug,
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
    parser.add_argument("--raw-bit-path", type=Path, default=DEFAULT_RAW_BIT_PATH)
    parser.add_argument("--bit-bin-path", type=Path, default=DEFAULT_BIT_BIN_PATH)
    parser.add_argument("--tx-reference-path", type=Path, default=DEFAULT_TX_REFERENCE_PATH)
    parser.add_argument("--remote-firmware-name", default=DEFAULT_REMOTE_FIRMWARE_NAME)
    parser.add_argument("--gpreg-base-addr", type=parse_int, default=DEFAULT_BASE_ADDR)
    parser.add_argument("--expected-id", type=parse_int, default=DEFAULT_EXPECTED_ID)
    parser.add_argument("--frame-bit-count", type=int, default=DEFAULT_FRAME_BIT_COUNT)
    parser.add_argument("--preamble-count", type=int, default=DEFAULT_PREAMBLE_COUNT)
    parser.add_argument("--start-offset", type=int, default=DEFAULT_START_OFFSET)
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
    parser.add_argument("--dmesg-line-count", type=int, default=DEFAULT_DMESG_LINE_COUNT)
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

    raw_bit_path = args.raw_bit_path.resolve()
    if not raw_bit_path.exists():
        raise SystemExit(f"Missing raw bitstream: {raw_bit_path}")

    tx_reference_path = args.tx_reference_path.resolve()
    if not tx_reference_path.exists():
        raise SystemExit(f"Missing TX reference CI16 waveform: {tx_reference_path}")

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

    cfg = RuntimeBridgeRxHostTxProbeConfig(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_port=args.ssh_port,
        ssh_timeout_s=args.ssh_timeout_s,
        iio_uri=args.iio_uri,
        raw_bit_path=str(raw_bit_path),
        bit_bin_path=str(args.bit_bin_path.resolve()),
        tx_reference_path=str(tx_reference_path),
        remote_firmware_name=args.remote_firmware_name,
        gpreg_base_addr=args.gpreg_base_addr,
        expected_id=args.expected_id,
        frame_bit_count=args.frame_bit_count,
        preamble_count=args.preamble_count,
        start_offset=args.start_offset,
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
        reboot_after=bool(args.reboot_after),
        reboot_timeout_s=args.reboot_timeout_s,
        dmesg_line_count=args.dmesg_line_count,
    )

    converter = load_bit_bin_module()
    bit_bin_path = converter.build_system_bit_bin(
        raw_bit_path,
        output_path=args.bit_bin_path.resolve(),
    )
    bit_bin_payload = bit_bin_path.read_bytes()
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
        "timestamp_utc": iso_now(),
        "run_tag": run_tag,
        "config": asdict(cfg),
        "reference_package": reference_cfg,
        "local_raw_bit": {
            "path": str(raw_bit_path),
            "size_bytes": raw_bit_path.stat().st_size,
        },
        "local_bit_bin": {
            "path": str(bit_bin_path),
            "size_bytes": len(bit_bin_payload),
            "md5": md5_bytes(bit_bin_payload),
        },
        "tx_reference": {
            "path": str(tx_reference_path),
            "metrics": summarize_complex_waveform(tx_waveform),
        },
        "baseline": {},
        "reload": {},
        "post_reload": {},
        "idle_bringup": None,
        "host_tx_stage": None,
        "host_tx_bringup": None,
        "cleanup": {},
        "reboot": None,
        "summary": None,
        "fatal_error": None,
    }

    tx_buffer: Any | None = None
    iio: Any | None = None
    context: Any | None = None
    phy: Any | None = None
    dds: Any | None = None
    dds_snapshot: dict[str, dict[str, str | None]] = {}
    phy_snapshot: dict[str, str | None] = {}
    fatal_error: Exception | None = None

    try:
        payload["baseline"] = {
            "board_state": safe_probe("baseline_board_state", lambda: read_ad9361_state(runner)),
            "fpga_manager_state": safe_probe(
                "baseline_fpga_manager_state",
                lambda: run_remote(
                    runner,
                    "cat /sys/class/fpga_manager/fpga0/state",
                    context="read baseline fpga_manager state",
                ),
            ),
            "iio_context": safe_probe(
                "baseline_iio_context",
                lambda: probe_iio_context_summary(args.iio_uri),
            ),
        }

        remote_path = f"/lib/firmware/{args.remote_firmware_name}"
        upload_bytes_via_ssh_cat(runner, payload=bit_bin_payload, remote_path=remote_path)
        payload["reload"] = {
            "remote_file": read_remote_file_info(runner, remote_path),
            "reload": trigger_fpga_manager_reload(
                runner,
                remote_firmware_name=args.remote_firmware_name,
            ),
            "dmesg_tail": safe_probe(
                "post_reload_dmesg",
                lambda: read_dmesg_tail(runner, line_count=args.dmesg_line_count),
            ),
        }

        payload["post_reload"] = {
            "board_state": safe_probe("post_reload_board_state", lambda: read_ad9361_state(runner)),
            "fpga_manager_state": safe_probe(
                "post_reload_fpga_manager_state",
                lambda: run_remote(
                    runner,
                    "cat /sys/class/fpga_manager/fpga0/state",
                    context="read post-reload fpga_manager state",
                ),
            ),
            "iio_context": safe_probe(
                "post_reload_iio_context",
                lambda: probe_iio_context_summary(args.iio_uri),
            ),
            "gpreg_id": safe_probe("post_reload_gpreg_id", lambda: probe_gpreg_id(io)),
            "gpreg_snapshot": safe_probe(
                "post_reload_gpreg_snapshot",
                lambda: register_snapshot(io, args.gpreg_base_addr),
            ),
        }

        payload["idle_bringup"] = attempt_runtime_bringup(io, cfg)

        payload["host_tx_stage"] = {
            "last_step": "open_iio_context",
            "tx_waveform_metrics": summarize_complex_waveform(tx_waveform),
        }
        iio = load_iio_module()
        context = iio.Context(args.iio_uri)
        payload["host_tx_stage"]["last_step"] = "locate_iio_devices"
        phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
        dds = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
        if phy is None or dds is None:
            raise RuntimeError(
                "Expected both `ad9361-phy` and `cf-ad9361-dds-core-lpc` after the runtime reload."
            )

        payload["host_tx_stage"]["last_step"] = "snapshot_devices"
        phy_snapshot = snapshot_ad9361_state(phy)
        dds_snapshot = snapshot_dds_state(dds)
        payload["host_tx_stage"]["last_step"] = "configure_ad9361"
        configured_state = configure_ad9361_bpsk(phy, waveform_cfg)
        payload["host_tx_stage"]["last_step"] = "disable_dds_tones"
        disable_dds_tones(dds)
        payload["host_tx_stage"]["last_step"] = "push_tx_buffer"
        tx_buffer = transmit_cyclic_buffer(iio, dds, tx_waveform)
        payload["host_tx_stage"]["last_step"] = "tx_settle"
        if args.tx_settle_ms > 0:
            time.sleep(args.tx_settle_ms / 1000.0)
        payload["host_tx_stage"]["last_step"] = "run_host_tx_bringup"

        payload["host_tx_stage"]["phy_before"] = phy_snapshot
        payload["host_tx_stage"]["dds_before"] = dds_snapshot
        payload["host_tx_stage"]["phy_after_config"] = configured_state
        payload["host_tx_bringup"] = attempt_runtime_bringup(io, cfg)
        payload["host_tx_stage"]["last_step"] = "host_tx_bringup_complete"
    except Exception as exc:  # pragma: no cover - hardware dependent
        fatal_error = exc
        payload["fatal_error"] = {
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        if isinstance(payload.get("host_tx_stage"), dict):
            payload["fatal_error"]["host_tx_last_step"] = payload["host_tx_stage"].get("last_step")
    finally:
        cleanup_errors: list[dict[str, str]] = []
        try:
            if dds_snapshot:
                restore_dds_state(dds, dds_snapshot)  # type: ignore[name-defined]
        except Exception as exc:  # pragma: no cover - hardware dependent
            cleanup_errors.append({"stage": "restore_dds_state", "error": str(exc)})
        try:
            if phy_snapshot:
                restore_ad9361_state(phy, phy_snapshot)  # type: ignore[name-defined]
        except Exception as exc:  # pragma: no cover - hardware dependent
            cleanup_errors.append({"stage": "restore_ad9361_state", "error": str(exc)})
        try:
            if phy_snapshot:
                enforce_safe_tx_restore_over_ssh(phy_snapshot, args)
        except Exception as exc:  # pragma: no cover - hardware dependent
            cleanup_errors.append({"stage": "ssh_safe_tx_restore", "error": str(exc)})

        payload["cleanup"] = {
            "errors": cleanup_errors,
            "final_board_state": safe_probe("final_board_state", lambda: read_ad9361_state(runner)),
            "final_fpga_manager_state": safe_probe(
                "final_fpga_manager_state",
                lambda: run_remote(
                    runner,
                    "cat /sys/class/fpga_manager/fpga0/state",
                    context="read final fpga_manager state",
                ),
            ),
        }

        tx_buffer = None
        dds = None
        phy = None
        context = None
        iio = None

        if args.reboot_after:
            payload["reboot"] = try_reboot_to_stock(
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

    payload["summary"] = build_summary(payload)
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {json_out}")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    if fatal_error is not None:
        raise SystemExit(f"{type(fatal_error).__name__}: {fatal_error}")


def load_iio_module() -> Any:
    module_path = ROOT / "blocks" / "block_06_rf_frontend_and_ad9363" / "python" / "lab_6_3_probe_iio_context.py"
    spec = importlib.util.spec_from_file_location("lab_6_3_probe_iio_context", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load IIO helpers from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_iio_module()


if __name__ == "__main__":
    main()
