#!/usr/bin/env python3
"""Lab 11.14 - Host-driven stock-shell BPSK OTA fallback on AD9361."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any

import matplotlib.pyplot as plt
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

from end_to_end_bpsk_reference import (  # noqa: E402
    bits_to_bpsk,
    evm_percent,
    rrc_taps,
    scalar_align,
    upsample,
    write_ci16,
)
from lab_6_3_probe_iio_context import find_channel, load_iio_module  # noqa: E402
from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner  # noqa: E402


DATASET_DIR = ROOT / "datasets" / "lab11_14_stock_shell_bpsk_ota"
DOC_ASSET_DIR = ROOT / "docs" / "assets"
DEFAULT_CENTER_FREQUENCY_HZ = 915_000_000
DEFAULT_SAMPLE_RATE_HZ = 3_840_000
DEFAULT_SYMBOL_RATE_HZ = 240_000
DEFAULT_SAMPLES_PER_SYMBOL = 16
DEFAULT_RF_BANDWIDTH_HZ = 2_000_000
DEFAULT_PAYLOAD_BIT_COUNT = 256
DEFAULT_RRC_SPAN_SYMBOLS = 8
DEFAULT_ROLLOFF = 0.35
DEFAULT_TX_AMPLITUDE = 0.40
DEFAULT_CAPTURE_SAMPLE_COUNT = 131_072
DEFAULT_TX_ATTENUATION_DB = -50.0
DEFAULT_RX_GAIN_DB = 35.0
DEFAULT_SETTLE_MS = 150
DEFAULT_SYNTHETIC_CFO_HZ = 120.0
DEFAULT_SYNTHETIC_PHASE_OFFSET_RAD = 0.18
DEFAULT_SYNTHETIC_TIMING_OFFSET_SAMPLES = 5
DEFAULT_SYNTHETIC_NOISE_RMS = 0.010
DEFAULT_CANDIDATE_COUNT = 10
DEFAULT_SSH_HOST = "192.168.40.1"
DEFAULT_SSH_USER = "root"
DEFAULT_SSH_PASSWORD = "analog"
DEFAULT_SSH_PORT = 22
DEFAULT_SSH_TIMEOUT_S = 10.0
Q15_SCALE = 32767.0


PREAMBLE_BITS: tuple[int, ...] = (
    0,
    0,
    0,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    0,
    1,
    0,
)


@dataclass(frozen=True)
class WaveformConfig:
    center_frequency_hz: int
    sample_rate_hz: int
    symbol_rate_hz: int
    samples_per_symbol: int
    rf_bandwidth_hz: int
    payload_bit_count: int
    rolloff: float
    rrc_span_symbols: int
    tx_amplitude: float
    leading_silence_samples: int
    trailing_silence_samples: int
    capture_sample_count: int
    tx_attenuation_db: float
    rx_gain_db: float
    settle_ms: int
    rx_rf_port_select: str
    tx_rf_port_select: str
    synthetic_test: bool
    synthetic_cfo_hz: float
    synthetic_phase_offset_rad: float
    synthetic_timing_offset_samples: int
    synthetic_noise_rms: float
    seed: int


@dataclass(frozen=True)
class DetectionResult:
    matched_filter_start_sample: int
    sample_phase: int
    symbol_index: int
    correlation_abs: float
    bit_errors_total: int
    bit_errors_payload: int
    ber_total: float
    ber_payload: float
    evm_percent: float


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_tag(synthetic_test: bool) -> str:
    prefix = "synthetic" if synthetic_test else "live"
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uri", default="ip:192.168.40.1")
    parser.add_argument("--center-frequency-hz", type=int, default=DEFAULT_CENTER_FREQUENCY_HZ)
    parser.add_argument("--sample-rate-hz", type=int, default=DEFAULT_SAMPLE_RATE_HZ)
    parser.add_argument("--symbol-rate-hz", type=int, default=DEFAULT_SYMBOL_RATE_HZ)
    parser.add_argument("--samples-per-symbol", type=int, default=DEFAULT_SAMPLES_PER_SYMBOL)
    parser.add_argument("--rf-bandwidth-hz", type=int, default=DEFAULT_RF_BANDWIDTH_HZ)
    parser.add_argument("--payload-bit-count", type=int, default=DEFAULT_PAYLOAD_BIT_COUNT)
    parser.add_argument("--rolloff", type=float, default=DEFAULT_ROLLOFF)
    parser.add_argument("--rrc-span-symbols", type=int, default=DEFAULT_RRC_SPAN_SYMBOLS)
    parser.add_argument("--tx-amplitude", type=float, default=DEFAULT_TX_AMPLITUDE)
    parser.add_argument("--capture-sample-count", type=int, default=DEFAULT_CAPTURE_SAMPLE_COUNT)
    parser.add_argument("--tx-attenuation-db", type=float, default=DEFAULT_TX_ATTENUATION_DB)
    parser.add_argument("--rx-gain-db", type=float, default=DEFAULT_RX_GAIN_DB)
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    parser.add_argument("--rx-rf-port-select", default="A_BALANCED")
    parser.add_argument("--tx-rf-port-select", default="A")
    parser.add_argument("--seed", type=int, default=20260623)
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--ssh-host", default=DEFAULT_SSH_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_SSH_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_SSH_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_SSH_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=DEFAULT_SSH_TIMEOUT_S)
    parser.add_argument("--synthetic-test", action="store_true")
    parser.add_argument("--synthetic-cfo-hz", type=float, default=DEFAULT_SYNTHETIC_CFO_HZ)
    parser.add_argument("--synthetic-phase-offset-rad", type=float, default=DEFAULT_SYNTHETIC_PHASE_OFFSET_RAD)
    parser.add_argument("--synthetic-timing-offset-samples", type=int, default=DEFAULT_SYNTHETIC_TIMING_OFFSET_SAMPLES)
    parser.add_argument("--synthetic-noise-rms", type=float, default=DEFAULT_SYNTHETIC_NOISE_RMS)
    parser.add_argument("--run-tag", default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--manifest-out", type=Path, default=None)
    parser.add_argument("--capture-out", type=Path, default=None)
    parser.add_argument("--tx-reference-out", type=Path, default=None)
    parser.add_argument("--spectrum-out", type=Path, default=None)
    parser.add_argument("--constellation-out", type=Path, default=None)
    parser.add_argument("--matched-filter-out", type=Path, default=None)
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
        attr.value = str(value)
    except OSError:
        if strict:
            raise


def write_attr_with_readback(
    channel: Any | None,
    attr_name: str,
    value: str | int | float | None,
    *,
    strict: bool = True,
    retries: int = 3,
    settle_s: float = 0.05,
) -> None:
    if channel is None or value is None:
        return
    target = str(value)
    last_value = None
    for attempt in range(max(retries, 1)):
        write_attr_value(channel, attr_name, target, strict=strict and attempt == 0)
        time.sleep(max(settle_s, 0.0))
        last_value = read_attr_value(channel, attr_name)
        if last_value == target:
            return
    if strict:
        raise RuntimeError(
            f"Unable to restore `{attr_name}` to `{target}`; last readback was `{last_value}`."
        )


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

    def restore_rx(channel: Any | None, prefix: str) -> None:
        write_attr_value(channel, "sampling_frequency", snapshot[f"{prefix}_sampling_frequency_hz"], strict=False)
        write_attr_value(channel, "rf_bandwidth", snapshot[f"{prefix}_rf_bandwidth_hz"], strict=False)
        write_attr_value(channel, "rf_port_select", snapshot[f"{prefix}_rf_port_select"], strict=False)
        gain_mode = snapshot[f"{prefix}_gain_control_mode"]
        hardware_gain = snapshot[f"{prefix}_hardwaregain_db"]
        if gain_mode == "manual":
            write_attr_value(channel, "hardwaregain", hardware_gain, strict=False)
            write_attr_value(channel, "gain_control_mode", gain_mode, strict=False)
        else:
            write_attr_value(channel, "gain_control_mode", gain_mode, strict=False)
            write_attr_value(channel, "hardwaregain", hardware_gain, strict=False)

    def restore_tx(channel: Any | None, prefix: str) -> None:
        write_attr_value(channel, "sampling_frequency", snapshot[f"{prefix}_sampling_frequency_hz"], strict=False)
        write_attr_value(channel, "rf_bandwidth", snapshot[f"{prefix}_rf_bandwidth_hz"], strict=False)
        write_attr_value(channel, "rf_port_select", snapshot[f"{prefix}_rf_port_select"], strict=False)
        write_attr_with_readback(channel, "hardwaregain", snapshot[f"{prefix}_hardwaregain_db"], strict=False)

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
        write_attr_value(channel, "scale", "0.0", strict=False)
    for channel in dds_tone_channels(dds):
        state = snapshot.get(str(channel.id))
        if state is None:
            continue
        write_attr_value(channel, "frequency", state.get("frequency"), strict=False)
        write_attr_value(channel, "phase", state.get("phase"), strict=False)
        write_attr_value(channel, "scale", state.get("scale"), strict=False)
        write_attr_value(channel, "raw", state.get("raw"), strict=False)


def configure_ad9361_bpsk(phy: Any, cfg: WaveformConfig) -> dict[str, str | None]:
    rx_lo = find_channel(phy, "altvoltage0", output=True)
    tx_lo = find_channel(phy, "altvoltage1", output=True)
    rx0 = find_channel(phy, "voltage0", output=False)
    rx1 = find_channel(phy, "voltage1", output=False)
    tx0 = find_channel(phy, "voltage0", output=True)
    tx1 = find_channel(phy, "voltage1", output=True)
    if None in (rx_lo, tx_lo, rx0, rx1, tx0, tx1):
        raise RuntimeError("Unable to locate required AD9361 channels in the remote IIO context.")

    write_attr_value(rx_lo, "frequency", cfg.center_frequency_hz)
    write_attr_value(tx_lo, "frequency", cfg.center_frequency_hz)
    write_attr_value(tx_lo, "powerdown", 0)

    for channel in (rx0, rx1):
        write_attr_value(channel, "sampling_frequency", cfg.sample_rate_hz)
        write_attr_value(channel, "rf_bandwidth", cfg.rf_bandwidth_hz)
        write_attr_value(channel, "gain_control_mode", "manual")
        write_attr_value(channel, "hardwaregain", f"{cfg.rx_gain_db:.1f}")
        write_attr_value(channel, "rf_port_select", cfg.rx_rf_port_select)

    for channel in (tx0, tx1):
        write_attr_value(channel, "sampling_frequency", cfg.sample_rate_hz)
        write_attr_value(channel, "rf_bandwidth", cfg.rf_bandwidth_hz)
        write_attr_value(channel, "hardwaregain", f"{cfg.tx_attenuation_db:.1f}")
        write_attr_value(channel, "rf_port_select", cfg.tx_rf_port_select)

    return snapshot_ad9361_state(phy)


def scan_output_channels(device: Any) -> list[Any]:
    channels = [
        channel
        for channel in getattr(device, "channels", [])
        if bool(getattr(channel, "output", False)) and bool(getattr(channel, "scan_element", False))
    ]
    if len(channels) < 2:
        raise RuntimeError("Expected at least two output scan channels on cf-ad9361-dds-core-lpc.")
    channels.sort(key=lambda channel: int(str(channel.id).replace("voltage", "")))
    return channels


def scan_input_channels(device: Any) -> list[Any]:
    channels = [
        channel
        for channel in getattr(device, "channels", [])
        if (not bool(getattr(channel, "output", False))) and bool(getattr(channel, "scan_element", False))
    ]
    if len(channels) < 2:
        raise RuntimeError("Expected at least two input scan channels on cf-ad9361-lpc.")
    channels.sort(key=lambda channel: int(str(channel.id).replace("voltage", "")))
    return channels


def build_waveform_config(args: argparse.Namespace) -> WaveformConfig:
    if args.sample_rate_hz != args.symbol_rate_hz * args.samples_per_symbol:
        raise SystemExit("sample-rate-hz must equal symbol-rate-hz * samples-per-symbol for the stock-shell helper.")
    leading_silence_samples = 4096
    trailing_silence_samples = 4096
    return WaveformConfig(
        center_frequency_hz=args.center_frequency_hz,
        sample_rate_hz=args.sample_rate_hz,
        symbol_rate_hz=args.symbol_rate_hz,
        samples_per_symbol=args.samples_per_symbol,
        rf_bandwidth_hz=args.rf_bandwidth_hz,
        payload_bit_count=args.payload_bit_count,
        rolloff=args.rolloff,
        rrc_span_symbols=args.rrc_span_symbols,
        tx_amplitude=args.tx_amplitude,
        leading_silence_samples=leading_silence_samples,
        trailing_silence_samples=trailing_silence_samples,
        capture_sample_count=args.capture_sample_count,
        tx_attenuation_db=args.tx_attenuation_db,
        rx_gain_db=args.rx_gain_db,
        settle_ms=args.settle_ms,
        rx_rf_port_select=args.rx_rf_port_select,
        tx_rf_port_select=args.tx_rf_port_select,
        synthetic_test=bool(args.synthetic_test),
        synthetic_cfo_hz=args.synthetic_cfo_hz,
        synthetic_phase_offset_rad=args.synthetic_phase_offset_rad,
        synthetic_timing_offset_samples=args.synthetic_timing_offset_samples,
        synthetic_noise_rms=args.synthetic_noise_rms,
        seed=args.seed,
    )


def generate_bpsk_burst(cfg: WaveformConfig) -> dict[str, Any]:
    rng = np.random.default_rng(cfg.seed)
    preamble_bits = np.asarray(PREAMBLE_BITS, dtype=np.uint8)
    payload_bits = rng.integers(0, 2, size=cfg.payload_bit_count, dtype=np.uint8)
    tx_bits = np.concatenate([preamble_bits, payload_bits])
    tx_symbols = bits_to_bpsk(tx_bits)
    taps = rrc_taps(cfg.rolloff, cfg.rrc_span_symbols, cfg.samples_per_symbol)
    upsampled = upsample(tx_symbols, cfg.samples_per_symbol)
    tx_shaped = np.convolve(upsampled, taps, mode="full")
    tx_shaped *= cfg.tx_amplitude / max(np.max(np.abs(tx_shaped)), 1e-15)
    tx_waveform = np.concatenate(
        [
            np.zeros(cfg.leading_silence_samples, dtype=np.complex128),
            tx_shaped,
            np.zeros(cfg.trailing_silence_samples, dtype=np.complex128),
        ]
    )
    return {
        "preamble_bits": preamble_bits,
        "payload_bits": payload_bits,
        "tx_bits": tx_bits,
        "tx_symbols": tx_symbols,
        "rrc_taps": taps,
        "tx_waveform": tx_waveform,
    }


def apply_synthetic_channel(cfg: WaveformConfig, tx_waveform: np.ndarray) -> np.ndarray:
    repeated = np.tile(tx_waveform.astype(np.complex128), 3)
    delayed = np.concatenate(
        [np.zeros(cfg.synthetic_timing_offset_samples, dtype=np.complex128), repeated]
    )[: len(repeated)]
    t = np.arange(len(delayed), dtype=np.float64) / cfg.sample_rate_hz
    rotated = delayed * np.exp(1j * (2.0 * np.pi * cfg.synthetic_cfo_hz * t + cfg.synthetic_phase_offset_rad))
    rng = np.random.default_rng(cfg.seed + 1)
    noise = cfg.synthetic_noise_rms * (
        rng.standard_normal(len(rotated)) + 1j * rng.standard_normal(len(rotated))
    )
    return rotated + noise


def complex_to_ci16_capture(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    i_samples = np.clip(np.round(np.real(x) * Q15_SCALE), -32768, 32767).astype(np.int16)
    q_samples = np.clip(np.round(np.imag(x) * Q15_SCALE), -32768, 32767).astype(np.int16)
    return i_samples, q_samples


def ci16_to_complex(i_samples: np.ndarray, q_samples: np.ndarray) -> np.ndarray:
    return i_samples.astype(np.float64) / Q15_SCALE + 1j * q_samples.astype(np.float64) / Q15_SCALE


def capture_rx_iq(iio: Any, rx_device: Any, sample_count: int) -> tuple[np.ndarray, np.ndarray]:
    for channel in getattr(rx_device, "channels", []):
        channel.enabled = False

    rx_channels = scan_input_channels(rx_device)
    i_channel = rx_channels[0]
    q_channel = rx_channels[1]
    i_channel.enabled = True
    q_channel.enabled = True

    buf = iio.Buffer(rx_device, sample_count, False)
    buf.refill()
    i_samples = np.frombuffer(i_channel.read(buf), dtype=np.int16).copy()
    q_samples = np.frombuffer(q_channel.read(buf), dtype=np.int16).copy()
    return i_samples, q_samples


def disable_dds_tones(dds: Any) -> None:
    for channel in dds_tone_channels(dds):
        write_attr_value(channel, "raw", 0, strict=False)
        write_attr_value(channel, "scale", "0.0", strict=False)


def transmit_cyclic_buffer(iio: Any, tx_device: Any, tx_waveform: np.ndarray) -> Any:
    tx_channels = scan_output_channels(tx_device)
    for channel in getattr(tx_device, "channels", []):
        channel.enabled = False

    enabled = tx_channels[: min(4, len(tx_channels))]
    while len(enabled) < 4:
        enabled.append(None)

    for channel in enabled:
        if channel is not None:
            channel.enabled = True

    tx_i = np.clip(np.round(np.real(tx_waveform) * Q15_SCALE), -32768, 32767).astype("<i2")
    tx_q = np.clip(np.round(np.imag(tx_waveform) * Q15_SCALE), -32768, 32767).astype("<i2")
    zero = np.zeros(len(tx_waveform), dtype="<i2")

    buf = iio.Buffer(tx_device, len(tx_waveform), cyclic=True)
    payloads = [tx_i, tx_q, zero, zero]
    for channel, samples in zip(enabled, payloads):
        if channel is None:
            continue
        channel.write(buf, bytearray(samples.tobytes()), raw=True)
    buf.push()
    return buf


def detect_frame(
    *,
    capture: np.ndarray,
    taps: np.ndarray,
    preamble_bits: np.ndarray,
    tx_bits: np.ndarray,
    tx_symbols: np.ndarray,
    sps: int,
    candidate_count: int,
) -> dict[str, Any]:
    preamble_symbols = bits_to_bpsk(preamble_bits).astype(np.complex128)
    matched = np.convolve(capture, taps, mode="full")
    best: dict[str, Any] | None = None

    for phase in range(sps):
        sampled = matched[phase::sps]
        if len(sampled) < len(tx_symbols):
            continue
        corr = np.correlate(sampled, preamble_symbols, mode="valid")
        if corr.size == 0:
            continue
        order = np.argsort(np.abs(corr))[-max(candidate_count, 1) :]
        for symbol_index in order.tolist():
            frame = sampled[symbol_index : symbol_index + len(tx_symbols)]
            if len(frame) < len(tx_symbols):
                continue
            aligned = scalar_align(tx_symbols, frame)
            rx_bits = np.where(np.real(aligned) >= 0.0, 0, 1).astype(np.uint8)
            total_errors = int(np.sum(rx_bits != tx_bits))
            payload_errors = int(np.sum(rx_bits[len(preamble_bits) :] != tx_bits[len(preamble_bits) :]))
            candidate = {
                "matched_filter_start_sample": int(phase + symbol_index * sps),
                "sample_phase": int(phase),
                "symbol_index": int(symbol_index),
                "correlation_abs": float(abs(corr[symbol_index])),
                "rx_bits": rx_bits,
                "rx_symbols": aligned,
                "matched": matched,
                "bit_errors_total": total_errors,
                "bit_errors_payload": payload_errors,
                "ber_total": float(total_errors / max(len(tx_bits), 1)),
                "ber_payload": float(payload_errors / max(len(tx_bits) - len(preamble_bits), 1)),
                "evm_percent": float(evm_percent(tx_symbols, aligned)),
            }
            if best is None:
                best = candidate
                continue
            if candidate["bit_errors_total"] < best["bit_errors_total"]:
                best = candidate
                continue
            if (
                candidate["bit_errors_total"] == best["bit_errors_total"]
                and candidate["correlation_abs"] > best["correlation_abs"]
            ):
                best = candidate

    if best is None:
        raise RuntimeError("Unable to find a full BPSK frame in the capture.")
    return best


def save_spectrum(path: Path, x: np.ndarray, sample_rate_hz: float, title: str) -> None:
    n = min(len(x), 65536)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / max(n, 1)
    spec = np.fft.fftshift(np.fft.fft(x[:n] * window, n=n)) / max(n * coherent_gain, 1e-15)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate_hz))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 4.3))
    plt.plot(freq / 1e3, mag_db)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Baseband frequency, kHz")
    plt.ylabel("Magnitude, dBFS")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_constellation(path: Path, symbols: np.ndarray, title: str) -> None:
    shown = symbols[: min(512, len(symbols))]
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(5.0, 5.0))
    plt.scatter(np.real(shown), np.imag(shown), s=12, alpha=0.7)
    plt.grid(True, alpha=0.35)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.axis("equal")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_matched_filter_trace(
    path: Path,
    matched: np.ndarray,
    sample_start: int,
    sps: int,
    symbol_count: int,
    title: str,
) -> None:
    shown_symbols = min(24, symbol_count)
    start = max(sample_start - 2 * sps, 0)
    stop = min(sample_start + shown_symbols * sps, len(matched))
    t = np.arange(start, stop)
    sample_positions = sample_start + np.arange(shown_symbols) * sps
    in_range = sample_positions[(sample_positions >= start) & (sample_positions < stop)]
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.4, 4.3))
    plt.plot(t, np.real(matched[start:stop]), label="matched filter real")
    plt.scatter(in_range, np.real(matched[in_range]), color="tab:red", s=18, label="symbol samples")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Amplitude")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def repo_relative_or_str(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def write_manifest(
    *,
    manifest_path: Path,
    dataset_id: str,
    capture_path: Path,
    tx_reference_path: Path,
    metrics_path: Path,
    cfg: WaveformConfig,
    board_state: dict[str, Any],
    detection: DetectionResult,
) -> None:
    manifest = {
        "dataset_id": dataset_id,
        "version": 0.1,
        "status": "review-before-lfs",
        "title": "Stock-shell host-driven AD9361 BPSK OTA fallback capture",
        "description": (
            "Deterministic BPSK burst transmitted and received through the stock AD9361 Linux shell. "
            "Intended as the first host-driven RF fallback path while the integrated PL BPSK overlay "
            "is still blocked on runtime RX bring-up."
        ),
        "storage": "repo-generated",
        "url": None,
        "file_name": repo_relative_or_str(capture_path),
        "format": "ci16",
        "endianness": "little",
        "i_first": True,
        "sample_rate_hz": cfg.sample_rate_hz,
        "center_frequency_hz": cfg.center_frequency_hz,
        "bandwidth_hz": cfg.rf_bandwidth_hz,
        "analysis_command": (
            "python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py "
            f"--iq {repo_relative_or_str(capture_path)} --sample-rate-hz {cfg.sample_rate_hz}"
        ),
        "handoff": {
            "tx_reference_ci16": repo_relative_or_str(tx_reference_path),
            "metrics_json": repo_relative_or_str(metrics_path),
        },
        "hardware": {
            "transceiver": "Zynq-7020 + AD9361 board",
            "software": "stock Pluto-like Linux 5.15.0 + host libiio",
            "rf_path": "short OTA TX1 to RX1 using separate antennas",
            "context_uri": "synthetic-test" if cfg.synthetic_test else "ip:192.168.40.1",
            "rx_gain_db": board_state.get("rx0_hardwaregain_db"),
            "tx_attenuation_db": board_state.get("tx0_hardwaregain_db"),
            "rx_rf_port_select": board_state.get("rx0_rf_port_select"),
            "tx_rf_port_select": board_state.get("tx0_rf_port_select"),
        },
        "signal": {
            "modulation": "BPSK",
            "symbol_rate_hz": cfg.symbol_rate_hz,
            "samples_per_symbol": cfg.samples_per_symbol,
            "rolloff": cfg.rolloff,
            "payload_bit_count": cfg.payload_bit_count,
            "preamble_bit_count": len(PREAMBLE_BITS),
        },
        "quality_checks": {
            "frame_detected": True,
            "ber_total": detection.ber_total,
            "ber_payload": detection.ber_payload,
            "evm_percent": detection.evm_percent,
        },
        "notes": [
            "This path is a stock-shell RF fallback and does not exercise the PL BPSK overlay.",
            "Use conservative TX attenuation first and increase only if the preamble does not lock.",
            "For the integrated course route, keep Zynq RX as the primary BER path and RTL-SDR as a monitor receiver.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8")


def strip_db_units(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace(" dB", "").strip()


def enforce_safe_tx_restore_over_ssh(snapshot: dict[str, str | None], args: argparse.Namespace) -> None:
    runner = ParamikoCommandRunner(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        key_path=None,
        timeout_s=args.ssh_timeout_s,
    )
    try:
        commands = [
            (
                "/sys/bus/iio/devices/iio:device0/out_voltage0_hardwaregain",
                strip_db_units(snapshot.get("tx0_hardwaregain_db")),
            ),
            (
                "/sys/bus/iio/devices/iio:device0/out_voltage1_hardwaregain",
                strip_db_units(snapshot.get("tx1_hardwaregain_db")),
            ),
            (
                "/sys/bus/iio/devices/iio:device0/out_altvoltage1_TX_LO_powerdown",
                snapshot.get("tx_lo_powerdown"),
            ),
        ]
        for path, value in commands:
            if value is None:
                continue
            rc, stdout, stderr = runner(f"echo '{value}' > {path}")
            if rc != 0:
                details = stderr.strip() or stdout.strip() or f"exit code {rc}"
                raise RuntimeError(f"SSH restore write failed for {path}: {details}")
    finally:
        runner.close()


def build_output_paths(args: argparse.Namespace) -> dict[str, Path]:
    run_tag = args.run_tag or default_run_tag(bool(args.synthetic_test))
    capture_out = args.capture_out or (DATASET_DIR / "raw" / f"lab11_14_stock_shell_bpsk_ota_{run_tag}.ci16")
    tx_reference_out = args.tx_reference_out or (
        DATASET_DIR / "raw" / f"lab11_14_stock_shell_bpsk_ota_{run_tag}_tx_reference.ci16"
    )
    manifest_out = args.manifest_out or (DATASET_DIR / f"manifest_{run_tag}.yaml")
    json_out = args.json_out or (DOC_ASSET_DIR / f"lab114_stock_shell_bpsk_ota_{run_tag}_metrics.json")
    spectrum_out = args.spectrum_out or (DOC_ASSET_DIR / f"lab114_stock_shell_bpsk_ota_{run_tag}_spectrum.png")
    constellation_out = args.constellation_out or (
        DOC_ASSET_DIR / f"lab114_stock_shell_bpsk_ota_{run_tag}_constellation.png"
    )
    matched_filter_out = args.matched_filter_out or (
        DOC_ASSET_DIR / f"lab114_stock_shell_bpsk_ota_{run_tag}_matched_filter.png"
    )
    return {
        "run_tag": Path(run_tag),
        "capture_out": capture_out.resolve(),
        "tx_reference_out": tx_reference_out.resolve(),
        "manifest_out": manifest_out.resolve(),
        "json_out": json_out.resolve(),
        "spectrum_out": spectrum_out.resolve(),
        "constellation_out": constellation_out.resolve(),
        "matched_filter_out": matched_filter_out.resolve(),
    }


def main() -> int:
    args = parse_args()
    cfg = build_waveform_config(args)
    outputs = build_output_paths(args)
    dataset_id = f"lab11_14_stock_shell_bpsk_ota_{outputs['run_tag'].name}"
    burst = generate_bpsk_burst(cfg)
    tx_waveform = burst["tx_waveform"]

    write_ci16(outputs["tx_reference_out"], tx_waveform)

    board_before: dict[str, Any] = {}
    board_after_config: dict[str, Any] = {}
    capture_complex: np.ndarray
    iio_context_name = "synthetic"
    iio_context_description = "synthetic local impairment path"

    if cfg.synthetic_test:
        capture_complex = apply_synthetic_channel(cfg, tx_waveform)[: cfg.capture_sample_count]
        i_samples, q_samples = complex_to_ci16_capture(capture_complex)
        board_after_config = {
            "rx0_hardwaregain_db": f"{cfg.rx_gain_db:.1f}",
            "tx0_hardwaregain_db": f"{cfg.tx_attenuation_db:.1f}",
            "rx0_rf_port_select": cfg.rx_rf_port_select,
            "tx0_rf_port_select": cfg.tx_rf_port_select,
        }
    else:
        iio = load_iio_module()
        context = iio.Context(args.uri)
        iio_context_name = getattr(context, "name", "")
        iio_context_description = getattr(context, "description", "")
        phy = next((device for device in context.devices if device.name == "ad9361-phy"), None)
        tx_device = next((device for device in context.devices if device.name == "cf-ad9361-dds-core-lpc"), None)
        rx_device = next((device for device in context.devices if device.name == "cf-ad9361-lpc"), None)
        if phy is None or tx_device is None or rx_device is None:
            raise RuntimeError("Expected ad9361-phy, cf-ad9361-dds-core-lpc and cf-ad9361-lpc in the remote context.")

        tx_buffer = None
        ad9361_before = snapshot_ad9361_state(phy)
        dds_before = snapshot_dds_state(tx_device)
        board_before = ad9361_before
        try:
            board_after_config = configure_ad9361_bpsk(phy, cfg)
            disable_dds_tones(tx_device)
            tx_buffer = transmit_cyclic_buffer(iio, tx_device, tx_waveform)
            time.sleep(max(cfg.settle_ms, 0) / 1000.0)
            i_samples, q_samples = capture_rx_iq(iio, rx_device, cfg.capture_sample_count)
        finally:
            if tx_buffer is not None:
                try:
                    tx_buffer.cancel()
                except Exception:
                    pass
            restore_dds_state(tx_device, dds_before)
            restore_ad9361_state(phy, ad9361_before)
            enforce_safe_tx_restore_over_ssh(ad9361_before, args)

        capture_complex = ci16_to_complex(i_samples, q_samples)

    write_ci16(outputs["capture_out"], capture_complex)

    detection_payload = detect_frame(
        capture=capture_complex,
        taps=burst["rrc_taps"],
        preamble_bits=burst["preamble_bits"],
        tx_bits=burst["tx_bits"],
        tx_symbols=burst["tx_symbols"],
        sps=cfg.samples_per_symbol,
        candidate_count=args.candidate_count,
    )
    detection = DetectionResult(
        matched_filter_start_sample=detection_payload["matched_filter_start_sample"],
        sample_phase=detection_payload["sample_phase"],
        symbol_index=detection_payload["symbol_index"],
        correlation_abs=detection_payload["correlation_abs"],
        bit_errors_total=detection_payload["bit_errors_total"],
        bit_errors_payload=detection_payload["bit_errors_payload"],
        ber_total=detection_payload["ber_total"],
        ber_payload=detection_payload["ber_payload"],
        evm_percent=detection_payload["evm_percent"],
    )

    peak_level_dbfs = float(20.0 * np.log10(max(np.max(np.abs(capture_complex)), 1e-15)))
    rms_level_dbfs = float(20.0 * np.log10(max(np.sqrt(np.mean(np.abs(capture_complex) ** 2)), 1e-15)))
    metrics = {
        "timestamp_utc": iso_now(),
        "dataset_id": dataset_id,
        "synthetic_test": cfg.synthetic_test,
        "uri": args.uri,
        "iio_context_name": iio_context_name,
        "iio_context_description": iio_context_description,
        "waveform_config": asdict(cfg),
        "board_before": board_before,
        "board_after_config": board_after_config,
        "detection": asdict(detection),
        "capture_metrics": {
            "complex_sample_count": int(len(capture_complex)),
            "peak_level_dbfs": peak_level_dbfs,
            "rms_level_dbfs": rms_level_dbfs,
            "i_abs_max": int(np.max(np.abs(np.round(np.real(capture_complex) * Q15_SCALE).astype(np.int16)), initial=0)),
            "q_abs_max": int(np.max(np.abs(np.round(np.imag(capture_complex) * Q15_SCALE).astype(np.int16)), initial=0)),
        },
        "analysis_command": (
            f"python {repo_relative_or_str(Path(__file__))} "
            f"--uri {args.uri} --run-tag {outputs['run_tag'].name}"
        ),
    }

    outputs["json_out"].parent.mkdir(parents=True, exist_ok=True)
    outputs["json_out"].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_manifest(
        manifest_path=outputs["manifest_out"],
        dataset_id=dataset_id,
        capture_path=outputs["capture_out"],
        tx_reference_path=outputs["tx_reference_out"],
        metrics_path=outputs["json_out"],
        cfg=cfg,
        board_state=board_after_config,
        detection=detection,
    )
    save_spectrum(
        outputs["spectrum_out"],
        capture_complex,
        cfg.sample_rate_hz,
        "Stock-shell host BPSK OTA capture spectrum",
    )
    save_constellation(
        outputs["constellation_out"],
        detection_payload["rx_symbols"],
        "Stock-shell host BPSK OTA matched-filter constellation",
    )
    save_matched_filter_trace(
        outputs["matched_filter_out"],
        detection_payload["matched"],
        detection.matched_filter_start_sample,
        cfg.samples_per_symbol,
        len(burst["tx_symbols"]),
        "Stock-shell host BPSK OTA matched-filter trace",
    )

    print("Lab 11.14 - Stock-shell host BPSK OTA fallback")
    print(f"Dataset id: {dataset_id}")
    print(f"Synthetic test: {cfg.synthetic_test}")
    print(f"Capture IQ: {outputs['capture_out']}")
    print(f"TX reference IQ: {outputs['tx_reference_out']}")
    print(f"Manifest: {outputs['manifest_out']}")
    print(f"Metrics JSON: {outputs['json_out']}")
    print(f"BER total: {detection.ber_total:.6f}")
    print(f"BER payload: {detection.ber_payload:.6f}")
    print(f"EVM: {detection.evm_percent:.3f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
