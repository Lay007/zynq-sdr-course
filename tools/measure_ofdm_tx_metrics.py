#!/usr/bin/env python3
"""Measure level, PAPR and spectrum of the OFDM RTL transmitter output (issue #48).

Runs tb_ofdm_tx_metrics.sv (random bits -> ofdm_tx_cp16_path) with Icarus Verilog,
reads the dumped Q1.15 samples and reports:

* RMS and peak level in dBFS. Full scale is 32768 per component, and a complex
  sample is measured by its magnitude, so a full-scale complex tone is 0 dBFS. The
  per-component peak is what a DAC clips on.
* PAPR: the sample-level peak over the mean power, the levels exceeded by 1e-2 and
  1e-3 of the samples (CCDF), and the peak of a 4x interpolated copy, closer to the
  analog peak after the DAC, which the 1x samples underestimate.
* Fixed-point error: the RTL output against a float IFFT of the same subcarrier
  values (recovered from the RTL output and snapped to the exact grid).
* Spectrum at the 1x sample rate: the 99 % occupied bandwidth and the guard-band
  level relative to the in-band level, for the RTL output and for the float copy.
* A DAC back-off sweep in Python on the RTL samples: scale to a target RMS,
  quantize to a 12-bit DAC with saturation (the AD9363 DAC width) and count the
  clipped samples, the in-band EVM it causes, and the guard-band level.

Simulation only. The 1x spectrum stops at +-Fs/2, so "out of band" here means the
guard subcarriers inside the 64-bin grid; the RF spectrum after the AD9363
interpolation filters and the analog chain needs the board.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks/block_08_modulation_and_synchronization"
BENCH = "tb_ofdm_tx_metrics"
N_FFT = 64
N_CP = 16
N_SYM = N_FFT + N_CP
FULL_SCALE = 32768.0
# Used subcarriers: -26..-1 and +1..+26 (48 data + 4 pilots), Lab 8.5 layout.
USED = np.array([k % N_FFT for k in list(range(-26, 0)) + list(range(1, 27))])
GRID = {
    "qpsk": np.array([-23170.0, 23170.0]),
    "qam16": np.array([-31086.0, -10362.0, 10362.0, 31086.0]),
}
PILOT_LEVELS = np.array([-32768.0, 32767.0])
PILOT_BINS = np.array([k % N_FFT for k in (-21, -7, 7, 21)])


def run_bench(modulation: str, symbols: int, seed: int, workdir: Path) -> np.ndarray:
    for tool in ("iverilog", "vvp"):
        if shutil.which(tool) is None:
            raise SystemExit(f"{tool} is required; install Icarus Verilog")
    mod = 1 if modulation == "qam16" else 0
    out = workdir / f"{BENCH}_{modulation}.vvp"
    dump = workdir / f"tx_{modulation}.txt"
    sources = sorted((BLOCK / "rtl").glob("ofdm_*.v"))
    subprocess.run(
        ["iverilog", "-g2012", "-s", BENCH, f"-P{BENCH}.MODULATION={mod}",
         f"-P{BENCH}.SYMBOLS={symbols}", f"-P{BENCH}.SEED={seed}", "-o", str(out),
         *map(str, sources), str(BLOCK / "tb" / f"{BENCH}.sv")],
        cwd=ROOT, check=True, timeout=120,
    )
    run = subprocess.run(["vvp", str(out), f"+DUMP={dump.as_posix()}"], cwd=ROOT,
                         check=True, timeout=600, capture_output=True, text=True)
    if "PASS" not in run.stdout:
        raise SystemExit(run.stdout)
    data = np.loadtxt(dump, dtype=np.int64)
    return data[:, 0].astype(float) + 1j * data[:, 1].astype(float)


def symbols_of(x: np.ndarray) -> np.ndarray:
    """(n_symbols, 64) useful parts, CP dropped."""
    return x.reshape(-1, N_SYM)[:, N_CP:]


def snap(values: np.ndarray, levels: np.ndarray) -> np.ndarray:
    return levels[np.argmin(np.abs(values[..., None] - levels), axis=-1)]


def ideal_copy(x: np.ndarray, modulation: str) -> tuple[np.ndarray, np.ndarray]:
    """Float TX built from the exact subcarrier values the RTL was given."""
    bins = np.fft.fft(symbols_of(x), axis=1)  # the RTL IFFT is ifft() with 1/64
    ideal = np.zeros_like(bins)
    data = snap(bins.real, GRID[modulation]) + 1j * snap(bins.imag, GRID[modulation])
    ideal[:, USED] = data[:, USED]
    ideal[:, PILOT_BINS] = snap(bins[:, PILOT_BINS].real, PILOT_LEVELS)
    body = np.fft.ifft(ideal, axis=1)
    return np.concatenate([body[:, -N_CP:], body], axis=1).reshape(-1), ideal


def db(power_ratio: float) -> float:
    return 10.0 * np.log10(power_ratio)


def levels(x: np.ndarray) -> dict[str, float]:
    p = np.abs(x) ** 2
    mean = p.mean()
    sorted_p = np.sort(p)
    body = symbols_of(x)
    # 4x interpolation of each symbol: zero-pad the spectrum in the middle.
    spec = np.fft.fft(body, axis=1)
    padded = np.zeros((spec.shape[0], 4 * N_FFT), dtype=complex)
    padded[:, : N_FFT // 2] = spec[:, : N_FFT // 2]
    padded[:, -N_FFT // 2:] = spec[:, N_FFT // 2:]
    p4 = (np.abs(np.fft.ifft(padded, axis=1) * 4) ** 2).reshape(-1)
    return {
        "rms_dbfs": db(mean / FULL_SCALE**2),
        "peak_dbfs": db(p.max() / FULL_SCALE**2),
        "peak_component_dbfs": 20 * np.log10(np.max(np.abs(np.r_[x.real, x.imag])) / FULL_SCALE),
        "papr_db": db(p.max() / mean),
        "papr_1e2_db": db(sorted_p[int(len(p) * (1 - 1e-2))] / mean),
        "papr_1e3_db": db(sorted_p[int(len(p) * (1 - 1e-3))] / mean),
        "papr_4x_db": db(p4.max() / p4.mean()),
        "papr_4x_1e3_db": db(np.sort(p4)[int(len(p4) * (1 - 1e-3))] / p4.mean()),
    }


def psd(x: np.ndarray, nfft: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD, Hann window, 50 % overlap; frequency in subcarrier spacings."""
    win = np.hanning(nfft)
    step = nfft // 2
    acc = np.zeros(nfft)
    count = 0
    for start in range(0, len(x) - nfft + 1, step):
        seg = x[start:start + nfft] * win
        acc += np.abs(np.fft.fft(seg)) ** 2
        count += 1
    acc /= count
    freq = np.fft.fftfreq(nfft) * N_FFT
    order = np.argsort(freq)
    return freq[order], acc[order]


def spectrum(x: np.ndarray) -> dict[str, float]:
    f, p = psd(x)
    inband = p[(np.abs(f) <= 26) & (np.abs(f) >= 1)].mean()
    guard = p[np.abs(f) >= 28].mean()
    edge = p[np.abs(f) >= 31].mean()
    cum = np.cumsum(p) / p.sum()
    lo = f[np.searchsorted(cum, 0.005)]
    hi = f[np.searchsorted(cum, 0.995)]
    return {
        "obw99_spacings": hi - lo,
        "guard_dbc": db(guard / inband),
        "edge_dbc": db(edge / inband),
    }


def evm(y: np.ndarray, ref: np.ndarray) -> float:
    by = np.fft.fft(symbols_of(y), axis=1)[:, USED]
    br = np.fft.fft(symbols_of(ref), axis=1)[:, USED]
    return 100.0 * np.sqrt(np.sum(np.abs(by - br) ** 2) / np.sum(np.abs(br) ** 2))


def dac(x: np.ndarray, target_rms_dbfs: float, bits: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Scale to the target RMS, quantize to `bits` with saturation; return (output, ideal scaled, clips)."""
    gain = 10 ** ((target_rms_dbfs - levels(x)["rms_dbfs"]) / 20)
    scaled = x * gain
    lsb = FULL_SCALE / 2 ** (bits - 1)
    top = 2 ** (bits - 1) - 1
    comps = []
    clips = 0
    for c in (scaled.real, scaled.imag):
        code = np.round(c / lsb)
        clips += int(np.sum((code > top) | (code < -top - 1)))
        comps.append(np.clip(code, -top - 1, top) * lsb)
    return comps[0] + 1j * comps[1], scaled, clips


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modulation", choices=("qpsk", "qam16"), nargs="+", default=["qpsk", "qam16"])
    parser.add_argument("--symbols", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--dac-bits", type=int, default=12)
    parser.add_argument("--backoff", type=float, nargs="+", default=[-6, -9, -12, -15, -18],
                        help="target RMS levels at the DAC, dBFS")
    args = parser.parse_args()

    with TemporaryDirectory(prefix="ofdm-tx-metrics-") as tmp:
        for modulation in args.modulation:
            x = run_bench(modulation, args.symbols, args.seed, Path(tmp))
            ref, _ = ideal_copy(x, modulation)
            err = x - ref
            sqnr = db(np.mean(np.abs(ref) ** 2) / np.mean(np.abs(err) ** 2))
            lv, sp, sp_ref = levels(x), spectrum(x), spectrum(ref)
            print(f"\n{modulation.upper()}: {args.symbols} symbols, {len(x)} samples (RTL simulation, seed {args.seed})")
            print(f"  RMS {lv['rms_dbfs']:.2f} dBFS, peak {lv['peak_dbfs']:.2f} dBFS "
                  f"(per component {lv['peak_component_dbfs']:.2f} dBFS)")
            print(f"  PAPR {lv['papr_db']:.2f} dB max, {lv['papr_1e2_db']:.2f} dB at 1e-2, "
                  f"{lv['papr_1e3_db']:.2f} dB at 1e-3; 4x interpolated: max {lv['papr_4x_db']:.2f} dB, "
                  f"{lv['papr_4x_1e3_db']:.2f} dB at 1e-3")
            print(f"  RTL vs float IFFT: SQNR {sqnr:.1f} dB, max error {np.max(np.abs(err)):.2f} LSB")
            print(f"  99 % bandwidth {sp['obw99_spacings']:.1f} subcarrier spacings "
                  f"(float {sp_ref['obw99_spacings']:.1f}); guard band (|f| >= 28) {sp['guard_dbc']:.1f} dBc "
                  f"(float {sp_ref['guard_dbc']:.1f}); band edge (|f| >= 31) {sp['edge_dbc']:.1f} dBc "
                  f"(float {sp_ref['edge_dbc']:.1f})")
            print(f"  {args.dac_bits}-bit DAC back-off sweep:")
            print("    RMS dBFS | clipped samples      | EVM %  | guard dBc")
            for target in args.backoff:
                y, scaled, clips = dac(x, target, args.dac_bits)
                print(f"    {target:8.1f} | {clips:6d} ({100 * clips / (2 * len(x)):6.3f} %) | "
                      f"{evm(y, scaled):6.2f} | {spectrum(y)['guard_dbc']:8.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
