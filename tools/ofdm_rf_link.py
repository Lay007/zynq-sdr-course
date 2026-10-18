#!/usr/bin/env python3
"""Issue #48, stage 4: the OFDM link through a radio channel, with frame synchronization.

The OFDM modem of the board (ofdm_axi_modem) receives symbols that are already cut: 80 samples per
symbol, the cyclic prefix first. On a radio the receiver sees a continuous stream and has to find
the frame first. This script builds a frame, sends it through a channel, finds it again and runs the
received symbols through the RTL receiver (Icarus Verilog, tb_ofdm_modem_file.sv):

    silence | sync preamble (CP + two equal 32-sample halves) | training symbol(s) | data | silence

* The training and data symbols are the RTL transmitter's own output (tb_ofdm_modem_file MODE=0).
* The preamble (Schmidl & Cox) puts energy only on even subcarriers, so its 64-sample body is two
  equal halves; it is only for finding the frame and never reaches the modem.
* Frame synchronization: the Schmidl & Cox metric M(d) = |P(d)|^2 / R(d)^2 over the two halves has
  a plateau as long as the cyclic prefix; the centre of the region above 90 % of its peak marks the
  start of the preamble body. The first training symbol starts 64 samples later; the receiver window
  is placed BACKOFF samples earlier, inside the cyclic prefix, because an early window only turns
  into a phase slope that the channel equalizer removes, while a late one mixes two symbols.
* Channel (simulation): an integer and a fractional delay, a carrier frequency offset, a phase,
  white noise at a given SNR (over the occupied band), a DC offset, an I/Q gain and phase imbalance,
  and 12-bit quantization, as on the AD9361's receiver.

Three ways to run it:

    python tools/ofdm_rf_link.py --frames 5 --snr-db 25 --cfo-hz 3000          # simulated channel
    python tools/ofdm_rf_link.py --save-tx frame_dir                             # a frame to transmit
    python tools/ofdm_rf_link.py --rx-capture rx.bin --tx-dir frame_dir          # a real recording

--save-tx writes tx_frame.bin (int16 I, Q interleaved, the RTL's Q1.15 samples moved by
--tx-scale-db, for iio_writedev at the modem rate), tx_data.npy (the data bit pairs) and meta.json.
--rx-capture reads an iio_readdev recording of the AD9361 receiver (int16 I, Q interleaved, 12 bits
sign-extended), scales it to Q1.15 at --rx-rms (the level the RTL receiver expects; on the board an
AGC or a fixed gain would set it), finds the first complete frame and decodes it with the RTL
receiver. Requires iverilog and vvp.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BLOCK = ROOT / "blocks" / "block_08_modulation_and_synchronization"
sys.path.insert(0, str(ROOT / "tools"))
from ofdm_channel_equalizer_fixed import train_bits  # noqa: E402

BENCH = "tb_ofdm_modem_file"
N, CP, SYM = 64, 16, 80
USED = [b for b in range(1, 27)] + [b for b in range(38, 64)]   # data and pilot bins (natural order)


def build_bench(work: Path, mode: int, train_symbols: int) -> Path:
    out = work / f"modem_mode{mode}.vvp"
    if not out.exists():
        subprocess.run(["iverilog", "-g2012", "-s", BENCH, f"-P{BENCH}.MODE={mode}",
                        f"-P{BENCH}.CE_TRAIN_SYMBOLS={train_symbols}", "-o", str(out),
                        *map(str, sorted((BLOCK / "rtl").glob("ofdm_*.v"))), str(BLOCK / "tb" / f"{BENCH}.sv")],
                       check=True, capture_output=True, text=True)
    return out


def run_bench(vvp: Path, args: list[str]) -> str:
    p = subprocess.run(["vvp", "-n", str(vvp), *args], capture_output=True, text=True, timeout=600)
    line = [x for x in p.stdout.splitlines() if x.startswith("RESULT") or x.startswith("FAIL")]
    if p.returncode != 0 or not line or line[-1].startswith("FAIL"):
        raise RuntimeError(f"bench failed: {p.stdout[-500:]} {p.stderr[-300:]}")
    return line[-1]


def frame_bits(n_data: int, train_symbols: int, rng: np.random.Generator) -> tuple[list[int], np.ndarray]:
    """Bit groups for the TX (QPSK: {i, q}); the data part is returned for the BER."""
    train = [(train_bits(d)[0] << 1) | train_bits(d)[1] for d in range(48)] * train_symbols
    data = rng.integers(0, 4, size=48 * n_data)
    return train + [int(v) for v in data], data


def rtl_tx(work: Path, groups: list[int], train_symbols: int) -> np.ndarray:
    bits = work / "tx_bits.txt"
    bits.write_text("".join(f"{g:x}\n" for g in groups))
    out = work / "tx_iq.txt"
    run_bench(build_bench(work, 0, train_symbols), [f"+BITS={bits}", f"+OUT={out}"])
    iq = np.loadtxt(out, dtype=np.int64).reshape(-1, 2)
    return iq[:, 0] + 1j * iq[:, 1]


def rtl_rx(work: Path, samples: np.ndarray, train_symbols: int) -> tuple[np.ndarray, str]:
    """Run aligned samples (Q1.15 complex ints, multiple of 80) through the RTL receiver."""
    iq = work / "rx_iq.txt"
    np.savetxt(iq, np.column_stack([samples.real, samples.imag]).astype(np.int64), fmt="%d")
    out = work / "rx_bits.txt"
    result = run_bench(build_bench(work, 1, train_symbols), [f"+IQ={iq}", f"+OUT={out}"])
    txt = out.read_text().split()
    pairs = np.array(txt, dtype=np.int64).reshape(-1, 2) if txt else np.zeros((0, 2), dtype=np.int64)
    return pairs, result


def preamble(rms: float, seed: int = 7) -> np.ndarray:
    """Schmidl & Cox symbol: random QPSK on the even used bins only, so the body is two equal halves."""
    rng = np.random.default_rng(seed)
    spec = np.zeros(N, complex)
    for b in USED:
        if b % 2 == 0:
            spec[b] = (rng.choice([-1, 1]) + 1j * rng.choice([-1, 1])) / np.sqrt(2)
    body = np.fft.ifft(spec)
    body *= rms / np.sqrt(np.mean(np.abs(body) ** 2))
    return np.concatenate([body[-CP:], body])


def channel(x: np.ndarray, rng: np.random.Generator, snr_db: float, cfo_hz: float, fs: float,
            frac: float, dc: complex, iq_gain_db: float, iq_phase_deg: float, rx_rms: float) -> np.ndarray:
    n = np.arange(len(x))
    # fractional delay: linear phase in frequency, applied to the whole (zero-padded) burst
    X = np.fft.fft(x)
    f = np.fft.fftfreq(len(x))
    y = np.fft.ifft(X * np.exp(-2j * np.pi * f * frac))
    y = y * np.exp(1j * (2 * np.pi * cfo_hz / fs * n + rng.uniform(0, 2 * np.pi)))
    # level: the occupied band carries the signal power; scale the noise accordingly
    sig_p = np.mean(np.abs(y[np.abs(y) > 0]) ** 2) if np.any(np.abs(y) > 0) else 1.0
    occupied = len(USED) / N
    noise_p = sig_p / 10 ** (snr_db / 10) / occupied
    y = y + np.sqrt(noise_p / 2) * (rng.standard_normal(len(y)) + 1j * rng.standard_normal(len(y)))
    # I/Q imbalance and DC on the receiver
    g = 10 ** (iq_gain_db / 20)
    ph = np.deg2rad(iq_phase_deg)
    yi, yq = y.real, y.imag
    y = yi + 1j * g * (np.sin(ph) * yi + np.cos(ph) * yq)
    y = y + dc * np.sqrt(sig_p)
    # receiver level and 12-bit converter (Q1.15 container: steps of 16)
    y = y * rx_rms / np.sqrt(sig_p)
    q = lambda v: np.clip(np.round(v / 16) * 16, -32768, 32752)  # noqa: E731
    return q(y.real) + 1j * q(y.imag)


def find_frame(r: np.ndarray) -> tuple[int, float, float]:
    """Start of the preamble body (Schmidl & Cox), the metric peak, and the CFO estimate (cycles/sample)."""
    h = N // 2
    prod = np.conj(r[:-h]) * r[h:]
    P = np.convolve(prod, np.ones(h), "valid")
    # Normalize by the mean energy of BOTH halves (|P| <= R then, M <= 1). Normalizing by the
    # second half alone, as in the textbook form, blows up where the second half falls into the
    # silence after the burst: there the metric reached 594 on the first simulated frame.
    e = np.convolve(np.abs(r) ** 2, np.ones(h), "valid")
    R = 0.5 * (e[:-h] + e[h:])
    M = np.abs(P) ** 2 / np.maximum(R, 1e-9) ** 2
    peak = M.max()
    above = np.flatnonzero(M > 0.9 * peak)
    # the first contiguous region above 90 %: the plateau of the preamble
    split = np.flatnonzero(np.diff(above) > 1)
    region = above[: split[0] + 1] if split.size else above
    d = int(round(region.mean()))
    # the plateau spans CP samples of possible starts: its centre is CP/2 into the cyclic prefix
    start = d + CP // 2
    cfo = np.angle(P[d]) / (2 * np.pi * h)
    return start, float(peak), float(cfo)


def make_frame(work: Path, rng: np.random.Generator, args) -> tuple[np.ndarray, np.ndarray, int]:
    """One burst: silence, preamble, the RTL's training and data symbols, silence."""
    groups, data = frame_bits(args.data_symbols, args.train_symbols, rng)
    tx = rtl_tx(work, groups, args.train_symbols)
    rms = float(np.sqrt(np.mean(np.abs(tx) ** 2)))
    lead = int(rng.integers(300, 900))
    burst = np.concatenate([np.zeros(lead), preamble(rms), tx, np.zeros(400)])
    return burst, data, lead + CP        # preamble body starts at lead + CP


def decode(work: Path, rx: np.ndarray, data: np.ndarray, args, true_start: int | None = None) -> dict:
    """Find the frame in rx (Q1.15 complex), run it through the RTL receiver, count bit errors."""
    start, peak, cfo_est = find_frame(rx)
    first = start + N - args.backoff                 # first training symbol, window BACKOFF early
    n_sym = args.train_symbols + args.data_symbols
    row = {"frame_start": start, "metric_peak": round(peak, 3), "cfo_est_hz": round(cfo_est * args.fs, 1)}
    if true_start is not None:
        row["sync_error"] = start - true_start
    aligned = rx[first: first + SYM * n_sym]
    if first < 0 or len(aligned) < SYM * n_sym:
        row["lost"] = True
        return row
    pairs, result = rtl_rx(work, aligned, args.train_symbols)
    got = np.full(48 * args.data_symbols, -1)
    for k, (idx, bits) in enumerate(pairs[: 48 * args.data_symbols]):
        got[(k // 48) * 48 + idx] = bits
    row.update({"bits": 2 * len(data),
                "bit_errors": int(sum(bin(int(a) ^ int(b)).count("1") if b >= 0 else 2 for a, b in zip(data, got))),
                "rx_result": result})
    return row


def run_frame(work: Path, rng: np.random.Generator, args) -> dict:
    burst, data, true_start = make_frame(work, rng, args)
    frac = rng.uniform(0, 1) if args.fractional else 0.0
    dc = args.dc * np.exp(1j * rng.uniform(0, 2 * np.pi))
    rx = channel(burst, rng, args.snr_db, args.cfo_hz, args.fs, frac, dc, args.iq_gain_db, args.iq_phase_deg,
                 args.rx_rms)
    return decode(work, rx, data, args, true_start)


def save_tx(work: Path, rng: np.random.Generator, args) -> dict:
    burst, data, start = make_frame(work, rng, args)
    y = burst * 10 ** (args.tx_scale_db / 20)
    clipped = float(np.mean((np.abs(y.real) > 32767) | (np.abs(y.imag) > 32767)))
    iq = np.zeros(2 * len(y), dtype=np.int16)
    iq[0::2] = np.clip(np.round(y.real), -32768, 32767)
    iq[1::2] = np.clip(np.round(y.imag), -32768, 32767)
    d = args.save_tx
    d.mkdir(parents=True, exist_ok=True)
    iq.tofile(d / "tx_frame.bin")
    np.save(d / "tx_data.npy", data)
    meta = {"samples": len(y), "preamble_body_start": start, "data_symbols": args.data_symbols,
            "train_symbols": args.train_symbols, "tx_scale_db": args.tx_scale_db, "clipped_fraction": clipped,
            "rms_dbfs": round(20 * np.log10(np.sqrt(np.mean(np.abs(y) ** 2)) / 32768), 2), "seed": args.seed}
    (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def rx_capture(work: Path, args) -> dict:
    meta = json.loads((args.tx_dir / "meta.json").read_text())
    args.data_symbols, args.train_symbols = meta["data_symbols"], meta["train_symbols"]
    data = np.load(args.tx_dir / "tx_data.npy")
    raw = np.fromfile(args.rx_capture, dtype="<i2").astype(np.float64)
    x = raw[0::2] + 1j * raw[1::2]
    x = x - np.mean(x)                                   # the AD9361's DC, before the level is set
    sig = np.abs(x) ** 2
    # level: the RMS over the loudest samples of a frame (the capture also holds silence)
    loud = np.sort(sig)[-meta["samples"] // 2:]
    x = x * args.rx_rms / np.sqrt(np.mean(loud))
    x = np.clip(np.round(x.real), -32768, 32767) + 1j * np.clip(np.round(x.imag), -32768, 32767)
    row = decode(work, x, data, args)
    row["capture_samples"] = len(x)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--data-symbols", type=int, default=10)
    ap.add_argument("--train-symbols", type=int, default=1)
    ap.add_argument("--fs", type=float, default=2.083e6, help="modem sample rate (Hz), for the CFO in Hz")
    ap.add_argument("--snr-db", type=float, default=30.0)
    ap.add_argument("--cfo-hz", type=float, default=0.0)
    ap.add_argument("--fractional", action="store_true", help="random fractional delay per frame")
    ap.add_argument("--dc", type=float, default=0.0, help="DC offset, relative to the signal RMS")
    ap.add_argument("--iq-gain-db", type=float, default=0.0)
    ap.add_argument("--iq-phase-deg", type=float, default=0.0)
    ap.add_argument("--rx-rms", type=float, default=3700.0, help="received RMS in Q1.15 units (-19 dBFS = 3680)")
    ap.add_argument("--backoff", type=int, default=4, help="window this many samples early, inside the CP")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--save-tx", type=Path, default=None, help="write one frame to transmit into this directory")
    ap.add_argument("--tx-scale-db", type=float, default=7.0,
                    help="--save-tx: level above the RTL output (-19 dBFS RMS); +7 dB = -12 dBFS, the clip-free optimum")
    ap.add_argument("--rx-capture", type=Path, default=None, help="decode this iio_readdev recording")
    ap.add_argument("--tx-dir", type=Path, default=None, help="--rx-capture: the --save-tx directory of the frame sent")
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        if args.save_tx:
            print(json.dumps(save_tx(work, rng, args)))
            return 0
        if args.rx_capture:
            row = rx_capture(work, args)
            print(json.dumps(row))
            if args.json_out:
                args.json_out.write_text(json.dumps(row, indent=1) + "\n")
            return 0
        for k in range(args.frames):
            row = run_frame(work, rng, args)
            rows.append(row)
            print(json.dumps(row), flush=True)
    bits = sum(r.get("bits", 0) for r in rows)
    errs = sum(r.get("bit_errors", 0) for r in rows)
    summary = {"frames": len(rows), "bits": bits, "bit_errors": errs, "ber": errs / bits if bits else None,
               "sync_errors": [r["sync_error"] for r in rows], "args": {k: str(v) for k, v in vars(args).items()}}
    print(json.dumps({k: v for k, v in summary.items() if k != "args"}))
    if args.json_out:
        args.json_out.write_text(json.dumps({"summary": summary, "frames": rows}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
