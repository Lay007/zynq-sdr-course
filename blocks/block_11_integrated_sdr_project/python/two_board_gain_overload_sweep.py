#!/usr/bin/env python3
"""Issue #29 on the two-board bench: an RX-gain x TX-level grid with the modem's own signal.

    board A TX1 -> variable attenuator -> 30 dB fixed -> 3-way splitter -> board B RX1
                                                                       -> RTL-SDR (level witness)
                                                                       -> 50 ohm

Board A (vendor image with the DDS/DMA core) streams the Lab 11.45 frame continuously. For every
(RX gain, TX gain) point board B (course image) reports its RSSI, a raw IQ capture through
`iio_readdev` (peak and RMS in dBFS of the 12-bit ADC, clipped fraction), and N on-chip BER frames
in the Lab 11.45 mode. The RTL-SDR records the level once per TX step. Both boards are quieted
(TX -89.75 dB) on exit.

Why a raw capture: in this mode the fabric capture-debug register carries other telemetry, so its
"peak" field is not a peak. Why RSSI is not enough: in overload the AD9361 RSSI stops tracking
(it sat at 80 dB for 10 dB of extra signal on 2026-10-13).

All levels are relative: the passive path has not been calibrated (S21) yet.
Measured 2026-10-13 at 915 MHz: reports/hardware/ad9361-two-board-overload-20261013.md.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

import lab_11_30_two_board_cfo_validation as L
import lab_11_32_two_board_fabric_coarse_cfo as B
from lab_11_12_runtime_fpga_manager_reload import upload_bytes_via_ssh_cat
from lab_11_27_runtime_qpsk_digital_loopback import QPSK_PAYLOAD_POSITION_BITS as POS, qpsk_ber_once

ROOT = Path(__file__).resolve().parents[3]
RTL_CAPTURE = ROOT / "tools" / "rtl_sdr_capture.py"
BASE = 0x79040000
MODE = 0x10 | 0x20 | 0x200 | 0x400 | 0x1000 | POS | 0x4000 | 0x20000   # Lab 11.45: diff QPSK + Gardner
GROSS = 8
ADC_FULL_SCALE = 2048.0          # 12-bit samples, sign-extended into 16 bits


def capture_b(client, n: int = 65536) -> dict:
    """Raw RX IQ from board B's cf-ad9361-lpc through iio_readdev, returned over the SSH channel."""
    _, out, _ = client.exec_command(
        f"iio_readdev -b {n} -s {n} cf-ad9361-lpc voltage0 voltage1 > /tmp/rx.bin 2>/tmp/rx.err; echo rc=$?",
        timeout=30)
    status = out.read().decode(errors="replace").strip()
    _, out, _ = client.exec_command("cat /tmp/rx.bin", timeout=30)
    data = out.read()
    x = np.frombuffer(data[: len(data) // 4 * 4], dtype="<i2").astype(np.float64)
    i, q = x[0::2], x[1::2]
    if i.size == 0:
        return {"ok": False, "status": status}
    return {
        "ok": True,
        "samples": int(i.size),
        "peak_dbfs": round(float(20 * np.log10(max(np.max(np.abs(x)), 1.0) / ADC_FULL_SCALE)), 2),
        # Complex RMS against a per-component full scale: it can exceed 0 dBFS when both rails clip.
        "rms_dbfs": round(float(10 * np.log10(np.mean(i ** 2 + q ** 2) / ADC_FULL_SCALE ** 2)), 2),
        "clipped_pct": round(float(np.mean((np.abs(i) >= 2047) | (np.abs(q) >= 2047)) * 100), 4),
    }


def rtl_level(carrier_hz: float, gain_tenths: str, out: Path) -> dict:
    subprocess.run([sys.executable, str(RTL_CAPTURE), str(carrier_hz), "2.4e6", gain_tenths, "524288", str(out)],
                   capture_output=True, text=True, timeout=60, check=True)
    iq = np.load(out)
    return {"power_dbfs": round(float(10 * np.log10(np.mean(np.abs(iq) ** 2))), 2),
            "clipped_pct": round(float(np.mean((np.abs(iq.real) > 0.99) | (np.abs(iq.imag) > 0.99)) * 100), 4)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--frames", type=int, default=30, help="on-chip BER frames per point")
    ap.add_argument("--carrier", type=float, default=915e6)
    ap.add_argument("--rx-gains", type=int, nargs="+", default=[71, 60, 50, 40, 30, 20, 10, 0])
    ap.add_argument("--tx-gains", type=int, nargs="+", default=[-40, -30, -20, -10, -5, 0])
    ap.add_argument("--bench", required=True, help="describe the passive path, e.g. 'A TX1 -> 0 dB var -> ...'")
    ap.add_argument("--rtl-gain", default="0", help="RTL-SDR tuner gain in tenths of a dB, or 'none' to skip")
    ap.add_argument("--json-out", type=Path, required=True)
    args = ap.parse_args()
    if max(args.tx_gains) > 0:
        raise SystemExit("TX gain above 0 dB is not a valid AD9361 setting")

    iq = B.make_long_preamble_frame(29, differential=True)
    n = len(iq) // 2
    ra = L.runner_for("192.168.40.1", "root", "analog", 22, 25.0)
    rb = L.runner_for("192.168.20.1", "root", "analog", 22, 40.0)
    sh = L.sh
    res = {"issue": 29, "bench": args.bench, "carrier_hz": args.carrier, "sample_rate": L.SAMPLE_RATE,
           "signal": "Lab 11.45 differential QPSK frame, RRC, SPS 8", "mode": hex(MODE),
           "frames_per_point": args.frames, "adc_full_scale": int(ADC_FULL_SCALE) - 1, "rows": [], "rtl": {}}
    rtl_tmp = args.json_out.with_suffix(".rtl.npy")
    try:
        L.quiet_board(rb)
        sh(rb, f"echo {int(args.carrier)} > {B.PHY}/out_altvoltage0_RX_LO_frequency")
        sh(rb, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/in_voltage_sampling_frequency 2>/dev/null")
        sh(rb, f"echo manual > {B.PHY}/in_voltage0_gain_control_mode 2>/dev/null")
        res["b_rf_bandwidth"] = sh(rb, f"cat {B.PHY}/in_voltage_rf_bandwidth").strip()
        L.quiet_board(ra)
        if args.rtl_gain != "none":
            res["rtl"]["silent"] = rtl_level(args.carrier, args.rtl_gain, rtl_tmp)
        L.reset_tx_dma(ra)
        upload_bytes_via_ssh_cat(ra, payload=iq.tobytes(), remote_path="/tmp/lp.bin")
        sh(ra, f"echo {int(L.SAMPLE_RATE)} > {B.PHY}/out_voltage_sampling_frequency 2>/dev/null")
        sh(ra, f"echo {int(args.carrier)} > {B.PHY}/out_altvoltage1_TX_LO_frequency")
        sh(ra, f"echo {min(args.tx_gains):.2f} > {B.PHY}/out_voltage0_hardwaregain")
        sh(ra, f"echo 0 > {B.PHY}/out_altvoltage1_TX_LO_powerdown 2>/dev/null")
        res["a_tx_rf_bandwidth"] = sh(ra, f"cat {B.PHY}/out_voltage_rf_bandwidth").strip()
        L.start_detached(ra, f"nohup iio_writedev -c -b {n} -s {n} cf-ad9361-dds-core-lpc "
                             "voltage0 voltage1 < /tmp/lp.bin > /tmp/lp.log 2>&1 &")
        time.sleep(3.0)
        if sh(ra, f"devmem {L.DAC_CHAN_CNTRL_7_CH0}").strip() not in ("0x00000002", "0x2"):
            raise RuntimeError("transmitter not on DMA")
        if args.rtl_gain != "none":
            for tx in args.tx_gains:
                sh(ra, f"echo {tx:.2f} > {B.PHY}/out_voltage0_hardwaregain")
                time.sleep(0.5)
                res["rtl"][str(tx)] = rtl_level(args.carrier, args.rtl_gain, rtl_tmp)
                print(f"TX {tx} dB: RTL-SDR {res['rtl'][str(tx)]}")
        print("\n RX  TX     RSSI   ADC peak/RMS dBFS  clip %  lock clean  bit errors")
        for rx in args.rx_gains:
            sh(rb, f"echo {rx} > {B.PHY}/in_voltage0_hardwaregain")
            for tx in args.tx_gains:
                sh(ra, f"echo {tx:.2f} > {B.PHY}/out_voltage0_hardwaregain")
                time.sleep(0.5)
                rssi = sh(rb, f"cat {B.PHY}/in_voltage0_rssi").strip()
                adc = capture_b(rb.client)
                clean = single = gross = err = bits = 0
                for k in range(args.frames):
                    row = qpsk_ber_once(rb, BASE, B.LONG_FRAME_SYMBOLS, k % 8, mode_bits=MODE,
                                        preamble_bits=B.LONG_PREAMBLE_BITS)
                    if row.get("received_symbols") != B.LONG_FRAME_SYMBOLS:
                        continue
                    pe = row.get("payload_errors") or 0
                    err, bits = err + pe, bits + 256
                    clean += pe == 0
                    single += 0 < pe <= GROSS
                    gross += pe > GROSS
                lk = clean + single + gross
                res["rows"].append({"rx_gain_db": rx, "tx_gain_db": tx, "rssi": rssi, "adc": adc,
                                    "frames": args.frames, "locked": lk, "clean": clean, "single_bit": single,
                                    "gross": gross, "payload_bit_errors": err, "payload_bits": bits})
                print(f"{rx:3d} {tx:4d} {rssi:>10s} {adc.get('peak_dbfs')!s:>8}/{adc.get('rms_dbfs')!s:<8}"
                      f" {adc.get('clipped_pct')!s:>6} {lk:4d} {clean:5d}  {err}/{bits}")
    finally:
        try:
            sh(ra, "pkill -9 -f iio_writedev 2>/dev/null")
            L.quiet_board(ra)
            L.quiet_board(rb)
            print("both boards quiet (-89.75 dB)")
        except Exception as exc:  # noqa: BLE001
            print("cleanup warning:", exc)
        ra.client.close()
        rb.client.close()
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
        print("wrote", args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
