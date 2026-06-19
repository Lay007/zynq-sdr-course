#!/usr/bin/env python3
"""Lab 4.3 - Fixed-point BPSK TX/RX chain.

This lab turns the shared Block 11 BPSK reference package into a fixed-point
bridge for Simulink and future HDL work:

symbol mapper -> RRC TX filter -> known channel correction -> matched filter

The script automatically regenerates the Block 11 package if the handoff files
are missing, then compares float and Q1.15 implementations for the pulse
shaping and matched-filter stages.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"
BPSK_SCRIPT = ROOT / "blocks" / "block_11_integrated_sdr_project" / "python" / "end_to_end_bpsk_reference.py"
PACKAGE_DIR = ROOT / "blocks" / "block_11_integrated_sdr_project" / "assets" / "end_to_end_bpsk_reference"
Q15_SCALE = 32767.0
FRAC_BITS = 15


@dataclass(frozen=True)
class Lab43Metrics:
    tx_float_rebuild_rmse_vs_export: float
    tx_fixed_rms_error: float
    tx_fixed_evm_percent: float
    tx_filter_saturation_count: int
    tx_gain_saturation_count: int
    matched_filter_rms_error: float
    rx_float_evm_percent: float
    rx_fixed_evm_percent: float
    ber_total_float: float
    ber_payload_float: float
    ber_total_fixed: float
    ber_payload_fixed: float
    rx_filter_saturation_count: int
    rrc_tap_count: int
    fir_guard_bits: int
    fir_accumulator_width_bits: int
    tx_gain_q15: int


def ensure_bpsk_package() -> None:
    required = [
        PACKAGE_DIR / "config.json",
        PACKAGE_DIR / "tx_bits.txt",
        PACKAGE_DIR / "tx_symbols_float.txt",
        PACKAGE_DIR / "tx_symbols_q15.txt",
        PACKAGE_DIR / "rrc_taps_float.txt",
        PACKAGE_DIR / "rrc_taps_q15.txt",
        PACKAGE_DIR / "sample_plan.json",
        PACKAGE_DIR / "end_to_end_bpsk_reference_v1_tx_reference.ci16",
        PACKAGE_DIR / "end_to_end_bpsk_reference_v1.ci16",
    ]
    if all(path.is_file() for path in required):
        return
    subprocess.run([sys.executable, str(BPSK_SCRIPT)], cwd=ROOT, check=True)


def read_ci16(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype="<i2")
    if len(raw) % 2 != 0:
        raise ValueError(f"Invalid CI16 IQ length: {path}")
    i = raw[0::2].astype(np.float64) / 32768.0
    q = raw[1::2].astype(np.float64) / 32768.0
    return i + 1j * q


def q15(values: np.ndarray) -> np.ndarray:
    return np.clip(np.round(values * Q15_SCALE), -32768, 32767).astype(np.int16)


def round_shift(value: int, frac_bits: int = FRAC_BITS) -> int:
    return (value + (1 << (frac_bits - 1))) >> frac_bits


def upsample(symbols: np.ndarray, sps: int) -> np.ndarray:
    y = np.zeros(len(symbols) * sps, dtype=np.complex128)
    y[::sps] = symbols.astype(np.complex128)
    return y


def scalar_align(ref: np.ndarray, rx: np.ndarray) -> np.ndarray:
    n = min(len(ref), len(rx))
    ref_n = ref[:n]
    rx_n = rx[:n]
    gain = np.vdot(ref_n, rx_n) / max(np.vdot(ref_n, ref_n), 1e-15)
    return rx_n / gain


def evm_percent(ref: np.ndarray, rx: np.ndarray) -> float:
    n = min(len(ref), len(rx))
    ref_n = ref[:n]
    rx_n = rx[:n]
    err = rx_n - ref_n
    ref_rms = max(np.sqrt(np.mean(np.abs(ref_n) ** 2)), 1e-15)
    return float(100.0 * np.sqrt(np.mean(np.abs(err) ** 2)) / ref_rms)


def ber(bits: np.ndarray, rx_symbols: np.ndarray, payload_offset: int) -> tuple[float, float]:
    decisions = np.where(np.real(rx_symbols[: len(bits)]) >= 0.0, 0, 1).astype(np.uint8)
    total_errors = int(np.sum(decisions != bits))
    payload_errors = int(np.sum(decisions[payload_offset:] != bits[payload_offset:]))
    return float(total_errors / len(bits)), float(payload_errors / max(len(bits) - payload_offset, 1))


def fixed_point_complex_fir_q15(x: np.ndarray, taps_q15: np.ndarray) -> tuple[np.ndarray, int]:
    xi = q15(np.real(x))
    xq = q15(np.imag(x))
    hq = np.asarray(taps_q15, dtype=np.int16).reshape(-1)

    out_len = len(x) + len(hq) - 1
    yi = np.zeros(out_len, dtype=np.int16)
    yq = np.zeros(out_len, dtype=np.int16)
    saturation_count = 0

    for n in range(out_len):
        acc_i = 0
        acc_q = 0
        k_lo = max(0, n - len(xi) + 1)
        k_hi = min(len(hq), n + 1)
        for k in range(k_lo, k_hi):
            idx = n - k
            coeff = int(hq[k])
            acc_i += int(xi[idx]) * coeff
            acc_q += int(xq[idx]) * coeff

        ri = round_shift(acc_i)
        rq = round_shift(acc_q)
        ri_sat = int(np.clip(ri, -32768, 32767))
        rq_sat = int(np.clip(rq, -32768, 32767))
        saturation_count += int(ri != ri_sat) + int(rq != rq_sat)
        yi[n] = ri_sat
        yq[n] = rq_sat

    y = (yi.astype(np.float64) + 1j * yq.astype(np.float64)) / (2**FRAC_BITS)
    return y, saturation_count


def fixed_point_real_gain_q15(x: np.ndarray, gain_q15: int) -> tuple[np.ndarray, int]:
    xi = q15(np.real(x))
    xq = q15(np.imag(x))
    yi = np.zeros(len(xi), dtype=np.int16)
    yq = np.zeros(len(xq), dtype=np.int16)
    saturation_count = 0

    for idx in range(len(xi)):
        acc_i = int(xi[idx]) * int(gain_q15)
        acc_q = int(xq[idx]) * int(gain_q15)
        ri = round_shift(acc_i)
        rq = round_shift(acc_q)
        ri_sat = int(np.clip(ri, -32768, 32767))
        rq_sat = int(np.clip(rq, -32768, 32767))
        saturation_count += int(ri != ri_sat) + int(rq != rq_sat)
        yi[idx] = ri_sat
        yq[idx] = rq_sat

    y = (yi.astype(np.float64) + 1j * yq.astype(np.float64)) / (2**FRAC_BITS)
    return y, saturation_count


def spectrum_db(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    n = len(x)
    window = np.hanning(n)
    coherent_gain = np.sum(window) / n
    spec = np.fft.fftshift(np.fft.fft(x * window)) / (n * coherent_gain)
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / fs))
    mag_db = 20.0 * np.log10(np.maximum(np.abs(spec), 1e-15))
    return freq, mag_db


def save_tx_overlay(path: Path, ref: np.ndarray, fixed: np.ndarray) -> None:
    shown = min(260, len(ref), len(fixed))
    t = np.arange(shown)
    plt.figure(figsize=(7.3, 4.2))
    plt.plot(t, np.real(ref[:shown]), label="float TX real")
    plt.plot(t, np.real(fixed[:shown]), "--", label="fixed TX real")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Sample index")
    plt.ylabel("Amplitude")
    plt.title("Lab 4.3 - BPSK pulse shaping, float vs fixed")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_error_spectrum(path: Path, err: np.ndarray, fs: float) -> None:
    freq, mag_db = spectrum_db(err, fs)
    plt.figure(figsize=(7.3, 4.2))
    plt.plot(freq / 1e3, mag_db)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Frequency, kHz")
    plt.ylabel("Error magnitude, dBFS")
    plt.title("Lab 4.3 - Matched-filter float vs fixed error spectrum")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_constellation(path: Path, rx_float: np.ndarray, rx_fixed: np.ndarray) -> None:
    shown = min(240, len(rx_float), len(rx_fixed))
    plt.figure(figsize=(5.3, 5.0))
    plt.scatter(np.real(rx_float[:shown]), np.imag(rx_float[:shown]), s=10, alpha=0.55, label="float RX")
    plt.scatter(np.real(rx_fixed[:shown]), np.imag(rx_fixed[:shown]), s=10, alpha=0.55, label="fixed RX")
    plt.grid(True, alpha=0.35)
    plt.xlabel("In-phase")
    plt.ylabel("Quadrature")
    plt.axis("equal")
    plt.title("Lab 4.3 - BPSK matched-filter symbol recovery")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def save_format_table(path: Path, tap_count: int, gain_q15: int) -> None:
    guard_bits = int(np.ceil(np.log2(tap_count)))
    acc_width = 16 + 16 + guard_bits
    content = f"""# Lab 4.3 fixed-point format table

| Node | Format | Notes |
|---|---|---|
| input bits | `uint1` | deterministic frame from Block 11 package |
| BPSK symbol mapper output | `Q1.15` | `0 -> +32767`, `1 -> -32767` |
| upsampled symbol stream | `Q1.15` | zeros inserted between symbols |
| RRC taps | `Q1.15` | imported from Block 11 handoff |
| FIR product | `Q2.30` | `Q1.15 * Q1.15` |
| FIR accumulator | `{acc_width} bits`, approx `Q{2 + guard_bits}.30` | includes `guard_bits = ceil(log2({tap_count})) = {guard_bits}` |
| TX post-filter gain | `Q1.15` | quantized gain coefficient `{gain_q15}` |
| TX waveform output | `Q1.15` | after rounding and saturation |
| RX matched-filter input | `Q1.15` | corrected synthetic capture |
| RX sampled symbols | `Q1.15` | before scalar alignment in analysis |

## Simulink import route

1. Import `tx_symbols_q15.txt` as the symbol stream source.
2. Import `rrc_taps_q15.txt` into the TX and RX FIR blocks.
3. Reuse `sample_plan.json` for the symbol-sampling offset after matched filtering.
4. Keep the HDL-facing stream width at signed 16-bit unless the measured saturation count forces extra headroom.
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    ensure_bpsk_package()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    cfg = json.loads((PACKAGE_DIR / "config.json").read_text(encoding="utf-8"))
    sample_plan = json.loads((PACKAGE_DIR / "sample_plan.json").read_text(encoding="utf-8"))

    bits = np.loadtxt(PACKAGE_DIR / "tx_bits.txt", dtype=np.uint8)
    symbol_pairs_float = np.loadtxt(PACKAGE_DIR / "tx_symbols_float.txt")
    symbol_pairs_q15 = np.loadtxt(PACKAGE_DIR / "tx_symbols_q15.txt", dtype=np.int16)
    taps_float = np.loadtxt(PACKAGE_DIR / "rrc_taps_float.txt", dtype=np.float64)
    taps_q15 = np.loadtxt(PACKAGE_DIR / "rrc_taps_q15.txt", dtype=np.int16)
    tx_reference_export = read_ci16(PACKAGE_DIR / f"{cfg['dataset_id']}_tx_reference.ci16")
    capture = read_ci16(PACKAGE_DIR / f"{cfg['dataset_id']}.ci16")

    tx_symbols_float = symbol_pairs_float[:, 0] + 1j * symbol_pairs_float[:, 1]
    tx_symbols_q15 = symbol_pairs_q15[:, 0].astype(np.float64) / Q15_SCALE
    tx_symbols_q15 = tx_symbols_q15 + 1j * (symbol_pairs_q15[:, 1].astype(np.float64) / Q15_SCALE)

    sps = int(cfg["samples_per_symbol"])
    upsampled_float = upsample(tx_symbols_float, sps)
    tx_filter_float = np.convolve(upsampled_float, taps_float, mode="full")
    tx_gain = cfg["tx_amplitude"] / max(np.max(np.abs(tx_filter_float)), 1e-15)
    tx_gain_q15 = int(q15(np.array([tx_gain]))[0])
    tx_waveform_float = tx_filter_float * tx_gain
    tx_capture_float = np.concatenate(
        [
            np.zeros(int(cfg["leading_silence_samples"]), dtype=np.complex128),
            tx_waveform_float,
            np.zeros(int(cfg["trailing_silence_samples"]), dtype=np.complex128),
        ]
    )

    tx_filter_fixed, tx_filter_sat = fixed_point_complex_fir_q15(upsample(tx_symbols_q15, sps), taps_q15)
    tx_waveform_fixed, tx_gain_sat = fixed_point_real_gain_q15(tx_filter_fixed, tx_gain_q15)

    tx_export_rmse = float(np.sqrt(np.mean(np.abs(tx_capture_float - tx_reference_export[: len(tx_capture_float)]) ** 2)))
    tx_aligned = scalar_align(tx_waveform_float, tx_waveform_fixed)
    tx_rms_error = float(np.sqrt(np.mean(np.abs(tx_waveform_float - tx_aligned) ** 2)))
    tx_evm = evm_percent(tx_waveform_float, tx_aligned)

    t = np.arange(len(capture), dtype=np.float64) / float(cfg["sample_rate_hz"])
    rx_corrected = capture * np.exp(
        -1j * (2.0 * np.pi * float(cfg["cfo_hz"]) * t + float(cfg["phase_offset_rad"]))
    )
    matched_float = np.convolve(rx_corrected, taps_float, mode="full")
    matched_fixed, rx_filter_sat = fixed_point_complex_fir_q15(rx_corrected, taps_q15)

    sample_start = int(sample_plan["matched_filter_sample_start"])
    symbol_count = len(tx_symbols_float)
    rx_symbols_float = matched_float[sample_start::sps][:symbol_count]
    rx_symbols_fixed = matched_fixed[sample_start::sps][:symbol_count]
    rx_symbols_float_aligned = scalar_align(tx_symbols_float, rx_symbols_float)
    rx_symbols_fixed_aligned = scalar_align(tx_symbols_float, rx_symbols_fixed)

    payload_offset = len(cfg["preamble_bits"])
    ber_total_float, ber_payload_float = ber(bits, rx_symbols_float_aligned, payload_offset)
    ber_total_fixed, ber_payload_fixed = ber(bits, rx_symbols_fixed_aligned, payload_offset)
    shared_len = min(len(matched_float), len(matched_fixed))
    matched_filter_rms_error = float(
        np.sqrt(np.mean(np.abs(matched_float[:shared_len] - matched_fixed[:shared_len]) ** 2))
    )

    metrics = Lab43Metrics(
        tx_float_rebuild_rmse_vs_export=tx_export_rmse,
        tx_fixed_rms_error=tx_rms_error,
        tx_fixed_evm_percent=tx_evm,
        tx_filter_saturation_count=tx_filter_sat,
        tx_gain_saturation_count=tx_gain_sat,
        matched_filter_rms_error=matched_filter_rms_error,
        rx_float_evm_percent=evm_percent(tx_symbols_float, rx_symbols_float_aligned),
        rx_fixed_evm_percent=evm_percent(tx_symbols_float, rx_symbols_fixed_aligned),
        ber_total_float=ber_total_float,
        ber_payload_float=ber_payload_float,
        ber_total_fixed=ber_total_fixed,
        ber_payload_fixed=ber_payload_fixed,
        rx_filter_saturation_count=rx_filter_sat,
        rrc_tap_count=len(taps_q15),
        fir_guard_bits=int(np.ceil(np.log2(len(taps_q15)))),
        fir_accumulator_width_bits=16 + 16 + int(np.ceil(np.log2(len(taps_q15)))),
        tx_gain_q15=tx_gain_q15,
    )

    save_tx_overlay(ASSET_DIR / "lab43_bpsk_fixed_point_tx_waveform.png", tx_waveform_float, tx_aligned)
    save_error_spectrum(ASSET_DIR / "lab43_bpsk_fixed_point_error.png", matched_float[:shared_len] - matched_fixed[:shared_len], float(cfg["sample_rate_hz"]))
    save_constellation(
        ASSET_DIR / "lab43_bpsk_fixed_point_constellation.png",
        rx_symbols_float_aligned,
        rx_symbols_fixed_aligned,
    )
    (ASSET_DIR / "lab43_bpsk_fixed_point_metrics.json").write_text(
        json.dumps(asdict(metrics), indent=2),
        encoding="utf-8",
    )
    save_format_table(
        ASSET_DIR / "lab43_bpsk_fixed_point_format_table.md",
        len(taps_q15),
        tx_gain_q15,
    )

    print("Lab 4.3 - BPSK fixed-point chain")
    print(f"TX rebuild RMSE vs exported CI16: {metrics.tx_float_rebuild_rmse_vs_export:.6e}")
    print(f"TX fixed RMS error: {metrics.tx_fixed_rms_error:.6e}")
    print(f"TX fixed EVM: {metrics.tx_fixed_evm_percent:.4f} %")
    print(f"RX float/fixed payload BER: {metrics.ber_payload_float:.6e} / {metrics.ber_payload_fixed:.6e}")
    print(f"RX float/fixed EVM: {metrics.rx_float_evm_percent:.4f} / {metrics.rx_fixed_evm_percent:.4f} %")
    print(f"FIR guard bits: {metrics.fir_guard_bits}")
    print(f"Figures and metrics saved to: {ASSET_DIR}")


if __name__ == "__main__":
    main()
