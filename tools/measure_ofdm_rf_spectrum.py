#!/usr/bin/env python3
"""Issue #48: the OFDM RTL transmitter's spectrum after a real AD9361 TX, seen by an RTL-SDR.

Board A replays, through its DDS/DMA core, the exact samples that the RTL transmitter produces
(tb_ofdm_tx_metrics, random QPSK, CP 16), at the lowest AD9361 rate that needs no FIR
(2.083 MS/s). The RTL-SDR runs at 2.4 MS/s (3.2 MS/s returned empty samples on this unit) tuned
450 kHz above the carrier, so the upper half of the spectrum, from the centre to 1.3 times the
digital Nyquist frequency, sits in the middle of its passband, away from its own DC spur and its
filter roll-off. All metrics use that upper half (positive subcarriers). The digital scaling is stepped (the RTL's native
level and two higher levels, the last one clipped in the 16-bit domain), the RTL-SDR records
each, and the script compares:

* the guard-band level on RF with the same metric on the digital samples (-17.6 dBc predicted
  for the RTL output, tools/measure_ofdm_tx_metrics.py);
* the level just beyond the digital Nyquist frequency, where the AD9361 interpolation filters
  must suppress the images.

The RTL-SDR's own noise (board A silent) is measured first and subtracted from every PSD.
Levels are relative (dBc against the in-band average); the RTL-SDR is a witness, not a
calibrated analyser. Board A is quieted and every streaming process stopped (by PID) on exit.

    python tools/measure_ofdm_rf_spectrum.py --json-out reports/hardware/ofdm-rf-spectrum-YYYYMMDD.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "blocks/block_11_integrated_sdr_project/python"))
sys.path.insert(0, str(ROOT / "tools"))

import lab_11_30_two_board_cfo_validation as L  # noqa: E402
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat  # noqa: E402
from measure_ofdm_tx_metrics import run_bench  # noqa: E402

PHY = L.PHY
CARRIER = 915_000_000
TX_RATE = 2_083_334     # the driver rejects 2083333 (below its 2083333.33 minimum) and keeps the old rate
RTL_RATE = 2_400_000
RTL_CENTER = CARRIER + 450_000          # upper half of the band mid-passband, DC spur at +14 subcarriers
SPACING = TX_RATE / 64  # replaced by the read-back rate at run time


def rtl_psd(gain: str, tmp: Path, nfft: int = 2048):
    out = tmp / "rtl.npy"
    r = subprocess.run([sys.executable, str(ROOT / "tools/rtl_sdr_capture.py"), str(RTL_CENTER), str(RTL_RATE),
                        gain, str(4 * 1048576), str(out)], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    iq = np.load(out).astype(np.complex128)
    iq -= iq.mean()
    win = np.hanning(nfft)
    segs = iq[: iq.size // nfft * nfft].reshape(-1, nfft) * win
    psd = np.fft.fftshift((np.abs(np.fft.fft(segs, axis=1)) ** 2).mean(0))
    freq = np.fft.fftshift(np.fft.fftfreq(nfft, 1 / RTL_RATE)) + (RTL_CENTER - CARRIER)
    clipped = float(np.mean((np.abs(iq.real) > 0.98) | (np.abs(iq.imag) > 0.98)) * 100)
    return freq, psd, clipped, float(10 * np.log10(np.mean(np.abs(iq) ** 2)))


def band_metrics(freq, psd, dc_hz=None, spacing=None):
    """Levels on the positive-subcarrier half, against its in-band average (subcarriers 1-26)."""
    sc = freq / (spacing or SPACING)
    keep = np.ones_like(sc, dtype=bool) if dc_hz is None else np.abs(freq - dc_hz) > 15e3
    ref = np.mean(psd[(sc >= 1) & (sc <= 26) & keep])

    def lvl(lo, hi):
        sel = (sc >= lo) & (sc <= hi) & keep
        return float(10 * np.log10(max(np.mean(psd[sel]), 1e-30) / ref))

    return {"guard_28_32_dbc": round(lvl(28, 32), 1), "edge_31_32_dbc": round(lvl(31, 32), 1),
            "beyond_nyquist_33_40_dbc": round(lvl(33, 40), 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbols", type=int, default=400)
    ap.add_argument("--tx-gain", type=float, default=-8.0,
                    help="TX gain at the native level; each digital step up lowers it by the same amount, "
                         "so the RTL-SDR always sees the same RF level")
    ap.add_argument("--scales-db", type=float, nargs="+", default=[0.0, 7.0, 13.0],
                    help="digital gain over the RTL's native level (about -19 dBFS RMS)")
    ap.add_argument("--rtl-gain", default="297", help="RTL-SDR tuner gain, tenths of a dB")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()

    res = {"issue": 48, "bench": args.bench, "carrier_hz": CARRIER, "tx_rate": TX_RATE, "rtl_rate": RTL_RATE,
           "rtl_center_hz": RTL_CENTER, "tx_gain_db": args.tx_gain, "rtl_gain_tenths_db": args.rtl_gain,
           "subcarrier_spacing_hz": SPACING, "symbols": args.symbols, "points": []}
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 30.0)
    sh = L.sh
    with TemporaryDirectory(prefix="ofdm-rf-") as tmpdir:
        tmp = Path(tmpdir)
        x = run_bench("qpsk", args.symbols, 1, tmp)          # complex, Q1.15 units
        try:
            L.quiet_board(ra)
            L.reset_tx_dma(ra)
            sh(ra, f"echo {TX_RATE} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
            sh(ra, f"echo {CARRIER} > {PHY}/out_altvoltage1_TX_LO_frequency")
            res["tx_rate_readback"] = sh(ra, f"cat {PHY}/out_voltage_sampling_frequency").strip()
            rate = float(res["tx_rate_readback"])
            if abs(rate - TX_RATE) > 0.01 * TX_RATE:
                raise RuntimeError(f"TX rate not applied: {rate} instead of {TX_RATE}")
            spacing = rate / 64
            res["subcarrier_spacing_hz"] = spacing
            f0, noise, nclip, npow = rtl_psd(args.rtl_gain, tmp)
            res["rtl_noise_power_dbfs"] = round(npow, 2)
            # The same metrics on the digital samples (no DAC, no AD9361), for comparison.
            nd = 4096
            seg = x[: x.size // nd * nd].reshape(-1, nd) * np.hanning(nd)
            dpsd = np.fft.fftshift((np.abs(np.fft.fft(seg, axis=1)) ** 2).mean(0))
            dfreq = np.fft.fftshift(np.fft.fftfreq(nd, 1 / rate))
            res["digital_reference"] = band_metrics(dfreq, dpsd, spacing=spacing)
            print("digital:", res["digital_reference"])
            for scale_db in args.scales_db:
                y = x * 10 ** (scale_db / 20)
                re = np.clip(np.round(y.real), -32768, 32767)
                im = np.clip(np.round(y.imag), -32768, 32767)
                digital_clip = float(np.mean((np.abs(re) >= 32767) | (np.abs(im) >= 32767)) * 100)
                iq = np.zeros(2 * x.size, dtype=np.int16)
                iq[0::2], iq[1::2] = re.astype(np.int16), im.astype(np.int16)
                L.quiet_board(ra)
                L.reset_tx_dma(ra)
                upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/ofdm.bin")
                tx_gain = args.tx_gain - scale_db
                sh(ra, f"echo {tx_gain:.2f} > {PHY}/out_voltage0_hardwaregain")
                sh(ra, f"echo 0 > {PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
                L.start_detached(ra, f"nohup iio_writedev -c -b {x.size} -s {x.size} cf-ad9361-dds-core-lpc "
                                     "voltage0 voltage1 < /tmp/ofdm.bin > /tmp/ofdm.log 2>&1 &")
                time.sleep(3.0)
                freq, psd, clip, pw = rtl_psd(args.rtl_gain, tmp)
                sig = np.maximum(psd - noise, 1e-30)
                rms_dbfs = float(10 * np.log10(np.mean(re ** 2 + im ** 2) / 32768 ** 2))
                point = {"scale_db": scale_db, "tx_gain_db": tx_gain, "dac_rms_dbfs": round(rms_dbfs, 2), "digital_clip_pct": round(digital_clip, 3),
                         "rtl_power_dbfs": round(pw, 2), "rtl_clip_pct": round(clip, 4),
                         "snr_inband_db": round(float(10 * np.log10(np.mean(psd[(freq / spacing >= 1) & (freq / spacing <= 26)]) /
                                                              np.mean(noise[(freq / spacing >= 1) & (freq / spacing <= 26)]))), 1),
                         **band_metrics(freq, sig, dc_hz=RTL_CENTER - CARRIER, spacing=spacing)}
                res["points"].append(point)
                sel = (freq / spacing >= -2) & (freq / spacing <= 44)
                point["psd_upper_half"] = {
                    "subcarrier": [round(float(v), 3) for v in freq[sel] / spacing],
                    "signal_minus_noise_db": [round(float(v), 2) for v in 10 * np.log10(sig[sel])],
                    "noise_db": [round(float(v), 2) for v in 10 * np.log10(noise[sel])],
                }
                print(json.dumps({k: v for k, v in point.items() if k != "psd_upper_half"}))
        finally:
            try:
                L.quiet_board(ra)
                sh(ra, f"echo {int(L.SAMPLE_RATE)} > {PHY}/out_voltage_sampling_frequency 2>/dev/null")
                print("board A quiet (-89.75 dB, writers stopped), sample rate restored")
            except Exception as exc:  # noqa: BLE001
                print("cleanup warning:", exc)
            ra.client.close()
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
            print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
