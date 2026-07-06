#!/usr/bin/env python3
"""Lab 11.21 - Capture RTL-SDR monitor WAV during stock-shell ZynqSDR BPSK TX."""

from __future__ import annotations

import argparse
import ctypes
import json
import time
import wave
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[3]
BLOCK11_PYTHON_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python"
BLOCK06_PYTHON_DIR = ROOT / "blocks" / "block_06_rf_frontend_and_ad9363" / "python"
import sys

if str(BLOCK11_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK11_PYTHON_DIR))
if str(BLOCK06_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(BLOCK06_PYTHON_DIR))

from lab_11_14_stock_shell_bpsk_ota import (  # noqa: E402
    DEFAULT_CENTER_FREQUENCY_HZ,
    DEFAULT_PAYLOAD_BIT_COUNT,
    DEFAULT_RF_BANDWIDTH_HZ,
    DEFAULT_RRC_SPAN_SYMBOLS,
    DEFAULT_ROLLOFF,
    DEFAULT_SAMPLE_RATE_HZ,
    DEFAULT_SAMPLES_PER_SYMBOL,
    DEFAULT_SETTLE_MS,
    DEFAULT_SYMBOL_RATE_HZ,
    DEFAULT_TX_AMPLITUDE,
    build_waveform_config,
    configure_ad9361_bpsk,
    disable_dds_tones,
    enforce_safe_tx_restore_over_ssh,
    generate_bpsk_burst,
    repo_relative_or_str,
    restore_ad9361_state,
    restore_dds_state,
    snapshot_ad9361_state,
    snapshot_dds_state,
    transmit_cyclic_buffer,
)
from lab_6_3_probe_iio_context import load_iio_module  # noqa: E402
from bench_config import (  # noqa: E402
    DEFAULT_HOST as DEFAULT_SSH_HOST,
    DEFAULT_IIO_URI as DEFAULT_URI,
    DEFAULT_PASSWORD as DEFAULT_SSH_PASSWORD,
    DEFAULT_PORT as DEFAULT_SSH_PORT,
    DEFAULT_TIMEOUT_S as DEFAULT_SSH_TIMEOUT_S,
    DEFAULT_USER as DEFAULT_SSH_USER,
)


DOC_ASSET_DIR = ROOT / "docs" / "assets"
DATASET_DIR = ROOT / "datasets" / "lab11_20_rtl_sdr_ota_bpsk"
TMP_DIR = ROOT / "tmp"
DEFAULT_RTL_SAMPLE_RATE_HZ = 2_400_000
DEFAULT_RTL_CAPTURE_DURATION_S = 1.6
DEFAULT_RTL_TUNER_GAIN_DB10 = 200
DEFAULT_RTL_SYNC_BLOCK_BYTES = 262_144
DEFAULT_RTL_DLL_PATH = (
    Path.home()
    / "AppData"
    / "Local"
    / "Microsoft"
    / "WinGet"
    / "Packages"
    / "AlexandreRouma.SDRPlusPlus_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "sdrpp_windows_x64"
    / "rtlsdr.dll"
)
DEFAULT_REFERENCE_METRICS_JSON = ROOT / "docs" / "assets" / "lab114_stock_shell_bpsk_ota_live_20260623d_metrics.json"


@dataclass(frozen=True)
class CaptureReport:
    timestamp_utc: str
    dataset_id: str
    rtl_device_index: int
    rtl_device_name: str
    rtl_sample_rate_hz: int
    rtl_capture_duration_s: float
    rtl_tuner_gain_db10: int
    center_frequency_hz: int
    tx_attenuation_db: float
    zynq_waveform_sample_rate_hz: int
    bytes_captured: int
    wav_path: str
    manifest_path: str
    raw_u8_mean: float
    raw_u8_std: float
    raw_u8_min: int
    raw_u8_max: int


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag() -> str:
    return f"live_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default=DEFAULT_URI)
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--symbol-rate-hz", type=int, default=DEFAULT_SYMBOL_RATE_HZ)
    parser.add_argument("--samples-per-symbol", type=int, default=DEFAULT_SAMPLES_PER_SYMBOL)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--payload-bit-count", type=int, default=DEFAULT_PAYLOAD_BIT_COUNT)
    parser.add_argument("--rolloff", type=float, default=DEFAULT_ROLLOFF)
    parser.add_argument("--rrc-span-symbols", type=int, default=DEFAULT_RRC_SPAN_SYMBOLS)
    parser.add_argument("--tx-amplitude", type=float, default=DEFAULT_TX_AMPLITUDE)
    parser.add_argument("--capture-sample-count", type=int, default=131_072)
    parser.add_argument("--tx-attenuation-db", type=float, default=-45.0)
    parser.add_argument("--rx-gain-db", type=float, default=35.0)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--seed", type=int, default=20260623)
    parser.add_argument("--rtl-device-index", type=int, default=0)
    parser.add_argument("--rtl-sample-rate-hz", type=int, default=DEFAULT_RTL_SAMPLE_RATE_HZ)
    parser.add_argument("--rtl-capture-duration-s", type=float, default=DEFAULT_RTL_CAPTURE_DURATION_S)
    parser.add_argument("--rtl-tuner-gain-db10", type=int, default=DEFAULT_RTL_TUNER_GAIN_DB10)
    parser.add_argument("--rtl-auto-gain", action="store_true")
    parser.add_argument("--rtl-sync-block-bytes", type=int, default=DEFAULT_RTL_SYNC_BLOCK_BYTES)
    parser.add_argument("--rtl-dll-path", type=Path, default=DEFAULT_RTL_DLL_PATH)
    parser.add_argument("--reference-metrics-json", type=Path, default=DEFAULT_REFERENCE_METRICS_JSON)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--wav-out", type=Path, default=None)
    parser.add_argument("--manifest-out", type=Path, default=None)
    parser.add_argument("--report-out", type=Path, default=None)
    parser.add_argument("--ssh-host", default=DEFAULT_SSH_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_SSH_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_SSH_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_SSH_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_SSH_TIMEOUT_S)
    parser.add_argument("--synthetic-test", action="store_true")
    parser.add_argument("--synthetic-cfo-hz", type=float, default=120.0)
    parser.add_argument("--synthetic-phase-offset-rad", type=float, default=0.18)
    parser.add_argument("--synthetic-timing-offset-samples", type=int, default=5)
    parser.add_argument("--synthetic-noise-rms", type=float, default=0.010)
    return parser.parse_args()


def build_output_paths(args: argparse.Namespace) -> dict[str, Path]:
    run_tag = args.run_tag or default_run_tag()
    wav_out = args.wav_out or (TMP_DIR / f"lab1121_rtl_sdr_monitor_{run_tag}.wav")
    manifest_out = args.manifest_out or (DATASET_DIR / f"manifest_{run_tag}.yaml")
    report_out = args.report_out or (DOC_ASSET_DIR / f"lab1121_rtl_sdr_monitor_{run_tag}.json")
    return {
        "run_tag": Path(run_tag),
        "wav_out": wav_out.resolve(),
        "manifest_out": manifest_out.resolve(),
        "report_out": report_out.resolve(),
    }


def load_rtlsdr_library(dll_path: Path) -> Any:
    if not dll_path.exists():
        raise FileNotFoundError(f"RTL-SDR DLL not found: {dll_path}")
    rtl = ctypes.CDLL(str(dll_path))
    rtl.rtlsdr_get_device_count.restype = ctypes.c_uint32
    rtl.rtlsdr_get_device_name.argtypes = [ctypes.c_uint32]
    rtl.rtlsdr_get_device_name.restype = ctypes.c_char_p
    rtl.rtlsdr_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint32]
    rtl.rtlsdr_open.restype = ctypes.c_int
    rtl.rtlsdr_close.argtypes = [ctypes.c_void_p]
    rtl.rtlsdr_close.restype = ctypes.c_int
    rtl.rtlsdr_set_center_freq.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    rtl.rtlsdr_set_center_freq.restype = ctypes.c_int
    rtl.rtlsdr_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    rtl.rtlsdr_set_sample_rate.restype = ctypes.c_int
    rtl.rtlsdr_set_tuner_gain_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
    rtl.rtlsdr_set_tuner_gain_mode.restype = ctypes.c_int
    rtl.rtlsdr_set_tuner_gain.argtypes = [ctypes.c_void_p, ctypes.c_int]
    rtl.rtlsdr_set_tuner_gain.restype = ctypes.c_int
    rtl.rtlsdr_set_agc_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
    rtl.rtlsdr_set_agc_mode.restype = ctypes.c_int
    rtl.rtlsdr_reset_buffer.argtypes = [ctypes.c_void_p]
    rtl.rtlsdr_reset_buffer.restype = ctypes.c_int
    rtl.rtlsdr_read_sync.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    rtl.rtlsdr_read_sync.restype = ctypes.c_int
    return rtl


def write_wav_iq(path: Path, raw_u8: np.ndarray, sample_rate_hz: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    i = raw_u8[0::2].astype(np.float32)
    q = raw_u8[1::2].astype(np.float32)
    i16 = np.clip(np.round((i - 127.5) / 127.5 * 32767.0), -32768, 32767).astype("<i2")
    q16 = np.clip(np.round((q - 127.5) / 127.5 * 32767.0), -32768, 32767).astype("<i2")
    interleaved = np.empty(i16.size * 2, dtype="<i2")
    interleaved[0::2] = i16
    interleaved[1::2] = q16
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate_hz)
        w.writeframes(interleaved.tobytes())


def write_manifest(
    *,
    manifest_path: Path,
    dataset_id: str,
    wav_path: Path,
    args: argparse.Namespace,
    report_path: Path,
) -> None:
    manifest = {
        "manifest_kind": "capture-session",
        "schema_version": 1,
        "dataset_id": dataset_id,
        "version": 0.1,
        "status": "local-only",
        "title": "RTL-SDR monitor capture for stock-shell ZynqSDR OTA BPSK",
        "description": (
            "Fresh local RTL-SDR stereo WAV IQ capture recorded while the stock-shell AD9361 helper "
            "transmitted the deterministic Lab 11.14 BPSK waveform over the air."
        ),
        "storage": "local-workstation",
        "url": None,
        "local_path_hint_windows": str(wav_path),
        "format": "wav",
        "i_first": True,
        "sample_rate_hz": args.rtl_sample_rate_hz,
        "center_frequency_hz": args.center_frequency_hz,
        "analysis_command": (
            "python blocks/block_11_integrated_sdr_project/python/lab_11_20_read_rtl_wav_ota_bpsk_ber.py "
            f"--manifest {repo_relative_or_str(manifest_path)}"
        ),
        "source": "rtl-sdr-monitor-capture",
        "analysis_targets": ["BPSK frame detection", "BER", "EVM", "spectrum"],
        "quality_checks": {
            "capture_completed": wav_path.is_file() and wav_path.stat().st_size > 0,
            "offline_analysis_completed": False,
        },
        "license": "not-for-publication-until-reviewed",
        "analysis": {
            "reference_metrics_json": repo_relative_or_str(args.reference_metrics_json.resolve()),
            "capture_report_json": repo_relative_or_str(report_path),
        },
        "hardware": {
            "transmitter": "Zynq-7020 + AD9361 board, stock-shell host-driven BPSK TX",
            "monitor_receiver": "RTL-SDR V3 Pro",
            "context_uri": args.uri,
            "tx_attenuation_db": args.tx_attenuation_db,
            "rtl_tuner_gain_db10": args.rtl_tuner_gain_db10,
            "rtl_auto_gain": bool(args.rtl_auto_gain),
        },
        "signal": {
            "modulation": "BPSK",
            "symbol_rate_hz": args.symbol_rate_hz,
            "samples_per_symbol": args.samples_per_symbol,
            "rolloff": args.rolloff,
            "payload_bit_count": args.payload_bit_count,
            "expected_signal_offset_hz": 0.0,
        },
        "notes": [
            "This capture is intended for offline BER validation through the RTL-SDR monitor path.",
            "The deterministic payload matches the Lab 11.14 stock-shell reference when seed=20260623.",
            "Keep the local WAV outside Git or move it into Git LFS before sharing the raw recording.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8")


def main() -> int:
    args = parse_args()
    outputs = build_output_paths(args)
    dataset_id = f"lab11_20_rtl_sdr_ota_bpsk_{outputs['run_tag'].name}"
    rtl = load_rtlsdr_library(args.rtl_dll_path.resolve())
    device_count = int(rtl.rtlsdr_get_device_count())
    if device_count <= args.rtl_device_index:
        raise RuntimeError(
            f"RTL-SDR device index {args.rtl_device_index} is not available; device_count={device_count}."
        )
    device_name = rtl.rtlsdr_get_device_name(args.rtl_device_index).decode("utf-8", errors="replace")

    cfg = build_waveform_config(args)
    tx_waveform = generate_bpsk_burst(cfg)["tx_waveform"]

    iio = load_iio_module()
    context = iio.Context(args.uri)
    phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
    tx_device = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
    if phy is None or tx_device is None:
        raise RuntimeError("Expected ad9361-phy and cf-ad9361-dds-core-lpc in the remote IIO context.")

    total_bytes_target = int(args.rtl_sample_rate_hz * args.rtl_capture_duration_s * 2)
    raw_parts: list[np.ndarray] = []
    rtl_dev = ctypes.c_void_p()
    tx_buffer = None
    ad9361_before = snapshot_ad9361_state(phy)
    dds_before = snapshot_dds_state(tx_device)

    try:
        rc = rtl.rtlsdr_open(ctypes.byref(rtl_dev), args.rtl_device_index)
        if rc != 0:
            raise RuntimeError(f"rtlsdr_open failed with rc={rc}")

        for label, code in [
            ("set_center_freq", rtl.rtlsdr_set_center_freq(rtl_dev, args.center_frequency_hz)),
            ("set_sample_rate", rtl.rtlsdr_set_sample_rate(rtl_dev, args.rtl_sample_rate_hz)),
            ("set_agc_mode", rtl.rtlsdr_set_agc_mode(rtl_dev, 1 if args.rtl_auto_gain else 0)),
            ("set_tuner_gain_mode", rtl.rtlsdr_set_tuner_gain_mode(rtl_dev, 0 if args.rtl_auto_gain else 1)),
            (
                "set_tuner_gain",
                0 if args.rtl_auto_gain else rtl.rtlsdr_set_tuner_gain(rtl_dev, args.rtl_tuner_gain_db10),
            ),
            ("reset_buffer_pre", rtl.rtlsdr_reset_buffer(rtl_dev)),
        ]:
            if code != 0:
                raise RuntimeError(f"{label} failed with rc={code}")

        configure_ad9361_bpsk(phy, cfg)
        disable_dds_tones(tx_device)
        tx_buffer = transmit_cyclic_buffer(iio, tx_device, tx_waveform)
        time.sleep(max(args.settle_ms, 0) / 1000.0 + 0.05)
        rtl.rtlsdr_reset_buffer(rtl_dev)

        bytes_read = 0
        while bytes_read < total_bytes_target:
            block = min(args.rtl_sync_block_bytes, total_bytes_target - bytes_read)
            buf = (ctypes.c_ubyte * block)()
            n_read = ctypes.c_int()
            rc = rtl.rtlsdr_read_sync(rtl_dev, buf, block, ctypes.byref(n_read))
            if rc != 0:
                raise RuntimeError(f"rtlsdr_read_sync failed with rc={rc} after {bytes_read} bytes")
            if n_read.value <= 0:
                raise RuntimeError("rtlsdr_read_sync returned no bytes")
            raw_parts.append(np.ctypeslib.as_array(buf)[: n_read.value].copy())
            bytes_read += n_read.value
    finally:
        if tx_buffer is not None:
            try:
                tx_buffer.cancel()
            except Exception:
                pass
        restore_dds_state(tx_device, dds_before)
        restore_ad9361_state(phy, ad9361_before)
        enforce_safe_tx_restore_over_ssh(ad9361_before, args)
        if rtl_dev.value:
            rtl.rtlsdr_close(rtl_dev)

    raw_u8 = np.concatenate(raw_parts)
    write_wav_iq(outputs["wav_out"], raw_u8, args.rtl_sample_rate_hz)
    write_manifest(
        manifest_path=outputs["manifest_out"],
        dataset_id=dataset_id,
        wav_path=outputs["wav_out"],
        args=args,
        report_path=outputs["report_out"],
    )

    report = CaptureReport(
        timestamp_utc=iso_now(),
        dataset_id=dataset_id,
        rtl_device_index=args.rtl_device_index,
        rtl_device_name=device_name,
        rtl_sample_rate_hz=args.rtl_sample_rate_hz,
        rtl_capture_duration_s=float(args.rtl_capture_duration_s),
        rtl_tuner_gain_db10=args.rtl_tuner_gain_db10,
        center_frequency_hz=args.center_frequency_hz,
        tx_attenuation_db=float(args.tx_attenuation_db),
        zynq_waveform_sample_rate_hz=args.sample_rate_hz,
        bytes_captured=int(raw_u8.size),
        wav_path=str(outputs["wav_out"]),
        manifest_path=str(outputs["manifest_out"]),
        raw_u8_mean=float(raw_u8.mean()),
        raw_u8_std=float(raw_u8.std()),
        raw_u8_min=int(raw_u8.min()),
        raw_u8_max=int(raw_u8.max()),
    )
    outputs["report_out"].parent.mkdir(parents=True, exist_ok=True)
    outputs["report_out"].write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    print("Lab 11.21 - Capture RTL-SDR monitor WAV during stock-shell ZynqSDR BPSK TX")
    print(f"RTL device: {device_name}")
    print(f"Center frequency: {args.center_frequency_hz} Hz")
    print(f"RTL sample rate: {args.rtl_sample_rate_hz} Hz")
    print(f"RTL capture duration: {args.rtl_capture_duration_s:.3f} s")
    print(f"TX attenuation: {args.tx_attenuation_db:.1f} dB")
    print(f"WAV IQ: {outputs['wav_out']}")
    print(f"Manifest: {repo_relative_or_str(outputs['manifest_out'])}")
    print(f"Capture report: {repo_relative_or_str(outputs['report_out'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
