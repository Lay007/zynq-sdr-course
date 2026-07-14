#!/usr/bin/env python3
"""Lab 11.29 - Cold-boot BER reliability campaign for the PL BPSK/QPSK modem.

Answers "does the synthesized modem come up decoding on EVERY cold boot, and how sure are
we?" with a confidence interval, not "10/10 once". Each run reboots the board to a clean
state, reloads our bitstream, verifies the gpreg core id (a load-failure detector), then
sprays many frames through the PL FABRIC LOOPBACK -- TX looped into RX inside the fabric
(gp_ctrl[6]), no AD9361, no RF, bit-deterministic -- for both BPSK (281 bits/frame) and QPSK
(280 bits/frame) and counts.

Fabric loopback is the PL-CORRECTNESS metric: it exercises the whole synthesized
mapper/upsampler/RRC/sampler/decision/frame-sync/BER-counter through the real gpreg/CDC plane,
and because it is error-free every clean frame adds to a large deterministic bit count -- so a
run of 0 errors is not "BER=0" but a tight BER UPPER BOUND (rule of three: < ~3/bits).

"Cold boot" is a SOFT reboot by default (Linux + AD9361 re-init + overlay reload from stock),
which is what can be scripted without switchable power. If you have a controllable supply, pass
--power-cycle-cmd "<shell command that cycles the board's power>" for a true power cycle; the
command runs in place of the soft reboot and the campaign then waits for the board to return.

Statistics with no third-party dependency: Wilson score interval for proportions (load-success
and all-clean run rates, FER), rule-of-three / Jeffreys upper bound for BER when zero errors,
and Clopper-Pearson too when scipy is importable. The JSON summary is rewritten after EVERY run
so a stopped or killed campaign still leaves a complete, honest partial result.

RF-SAFETY: fabric loopback never configures or raises TX -- the board stays at the stock
-89.75 dB throughout, and the campaign reboots to stock at the end.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
import traceback
from collections import Counter
from pathlib import Path

from lab_11_7_axi_lite_bpsk_bringup import ParamikoCommandRunner
from lab_11_8_axi_gpreg_bpsk_bringup import SshDevMemRegisterIo
from lab_11_12_runtime_fpga_manager_reload import (
    probe_gpreg_id,
    trigger_fpga_manager_reload,
    upload_bytes_via_ssh_cat,
)
from lab_11_13_stock_vs_runtime_rx_compare import try_reboot_to_stock
from lab_11_15_runtime_bridge_rx_host_tx_probe import (
    DEFAULT_BASE_ADDR,
    DEFAULT_HOST,
    DEFAULT_IIO_URI,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_REMOTE_FIRMWARE_NAME,
    DEFAULT_TIMEOUT_S,
    DEFAULT_USER,
)
from runtime_rx_common import force_rx_common_ctrl_request

DEFAULT_BIT = Path(__file__).resolve().parents[3] / "tmp" / "bridge_txrx_mux.qpsk.wordswap.bit.bin"
GPREG_ID = 0x4250534B
SSH_TIMEOUT = 60.0  # a freshly cold-booted board is slow; the ~2.5 MB bitstream upload needs headroom

# gp_ctrl bit map
QPSK, FABRIC = 0x10, 0x40
# fabric-loop configs: (name, ctrl, frame_len_symbols, preamble_bits, start_offset, bits_per_frame)
FABRIC_MODES = [
    ("bpsk_fabric", FABRIC, 281, 24, 62, 281),
    ("qpsk_fabric", FABRIC | QPSK, 140, 24, 62, 280),
]


def reg(base):
    return {k: f"0x{base + v:X}" for k, v in dict(ctrl=0x404, frame=0x444, pre=0x484, off=0x4C4,
                                                  st=0x408, rc=0x448, ec=0x488).items()}


def burst(runner, A, ctrl, frame, pre, offset, poll=800):
    dm = "/sbin/devmem"
    cmd = (f"{dm} {A['frame']} 32 {frame}; {dm} {A['pre']} 32 {pre}; {dm} {A['off']} 32 {offset}; "
           f"{dm} {A['ctrl']} 32 {ctrl}; {dm} {A['ctrl']} 32 $(({ctrl}|1)); {dm} {A['ctrl']} 32 {ctrl}; "
           f"i=0;while [ $i -lt {poll} ]; do s=$({dm} {A['st']} 32); "
           f"if [ $((s&4)) -ne 0 ] || [ $((s&8)) -ne 0 ]; then break; fi; i=$((i+1)); done; "
           f"r=$({dm} {A['rc']} 32); e=$({dm} {A['ec']} 32); "
           f"{dm} {A['ctrl']} 32 $(({ctrl}|2)); {dm} {A['ctrl']} 32 {ctrl}; echo RESULT recv=$r err=$e")
    _, out, _ = runner(cmd)
    ln = next((x for x in out.splitlines() if x.startswith("RESULT")), "")
    f = dict(t.split("=", 1) for t in ln.split()[1:] if "=" in t)

    def h(k):
        return int(f.get(k, "0"), 16)

    return h("recv"), (h("err") >> 16) & 0xFFFF


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def ber_upper_zero(m, conf=0.95):
    return 1.0 - (1.0 - conf) ** (1.0 / m) if m > 0 else 1.0


def clopper_pearson(k, n, conf=0.95):
    try:
        from scipy.stats import beta
    except Exception:
        return None
    a = (1 - conf) / 2
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return (lo, hi)


def ping_up(host, timeout_s=180):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if subprocess.run(["ping", "-n", "1", "-w", "1500", host], capture_output=True).returncode == 0:
            return True
        time.sleep(3)
    return False


def new_runner():
    return ParamikoCommandRunner(host=DEFAULT_HOST, user=DEFAULT_USER, password=DEFAULT_PASSWORD,
                                port=DEFAULT_PORT, key_path=None, timeout_s=SSH_TIMEOUT)


def load_bitstream(runner, bit_path):
    upload_bytes_via_ssh_cat(runner, payload=bit_path.read_bytes(),
                             remote_path=f"/lib/firmware/{DEFAULT_REMOTE_FIRMWARE_NAME}")
    trigger_fpga_manager_reload(runner, remote_firmware_name=DEFAULT_REMOTE_FIRMWARE_NAME)
    ident = probe_gpreg_id(SshDevMemRegisterIo(DEFAULT_BASE_ADDR, command_runner=runner))
    force_rx_common_ctrl_request(runner, value=0x3)
    return ident


def dmesg_tail(runner, n=8):
    try:
        _, out, err = runner(f"dmesg | tail -n {n}")
        return (out or err or "").strip().splitlines()
    except Exception as e:
        return [f"<dmesg failed: {e}>"]


def reboot_to_stock():
    try:
        r = new_runner()
        try:
            try_reboot_to_stock(r, host=DEFAULT_HOST, user=DEFAULT_USER, password=DEFAULT_PASSWORD,
                                port=DEFAULT_PORT, ssh_timeout_s=DEFAULT_TIMEOUT_S,
                                iio_uri=DEFAULT_IIO_URI, timeout_s=120.0)
        finally:
            r.close()
    except Exception:
        pass


def cold_boot(power_cycle_cmd):
    """Return the board to a clean state: a user power-cycle command if given, else soft reboot."""
    if power_cycle_cmd:
        subprocess.run(power_cycle_cmd, shell=True, check=False)
    else:
        reboot_to_stock()
    if not ping_up(DEFAULT_HOST, 180):
        return False
    time.sleep(4)
    return True


def summarise(agg, runs_attempted, runs_loaded, runs_all_clean, load_failures, args):
    runs_completed = len(next(iter(agg.values()))["per_run"]) if agg else 0
    summary = dict(
        runs_attempted=runs_attempted, runs_completed=runs_completed,
        runs_loaded=runs_loaded, runs_all_clean=runs_all_clean,
        frames_per_run_per_mode=args.frames, cold_boot=not args.no_cold_boot,
        power_cycle=bool(args.power_cycle_cmd), bitstream=str(args.bit), modes={},
    )
    rc_lo, rc_hi = wilson(runs_all_clean, runs_attempted)
    ld_lo, ld_hi = wilson(runs_loaded, runs_attempted)
    summary["run_clean_rate"] = runs_all_clean / runs_attempted if runs_attempted else None
    summary["run_clean_wilson_95"] = [rc_lo, rc_hi]
    summary["run_clean_clopper_pearson_95"] = clopper_pearson(runs_all_clean, runs_attempted)
    summary["load_success_rate"] = runs_loaded / runs_attempted if runs_attempted else None
    summary["load_wilson_95"] = [ld_lo, ld_hi]
    for name, ctrl, frame, pre, off, bpf in FABRIC_MODES:
        m = agg[name]
        returned = m["frames"] - m["recv_bad"]
        bits = returned * bpf
        be = m["bit_errors"]
        fer_k = returned - m["clean"]
        rte = dict(frames=m["frames"], returned_full=returned, no_frame=m["recv_bad"],
                   clean_frames=m["clean"], bits_checked=bits, bit_errors=be,
                   error_hist={str(k): v for k, v in sorted(m["err_hist"].items(), key=lambda x: str(x[0]))})
        if bits and be == 0:
            rte["ber_point"] = 0.0
            rte["ber_upper_95"] = ber_upper_zero(bits)
            rte["ber_statement"] = f"BER < {ber_upper_zero(bits):.2e} (95% one-sided, {bits} bits, 0 errors)"
        elif bits:
            rte["ber_point"] = be / bits
            rte["ber_clopper_pearson_95"] = clopper_pearson(be, bits)
            rte["ber_statement"] = f"BER = {be / bits:.2e} ({be}/{bits})"
        rte["fer_point"] = (fer_k / returned) if returned else None
        rte["fer_wilson_95"] = list(wilson(fer_k, returned)) if returned else [0.0, 1.0]
        summary["modes"][name] = rte
    summary["load_failures"] = load_failures
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--frames", type=int, default=200, help="frames per mode per run")
    ap.add_argument("--no-cold-boot", action="store_true", help="load once, do not reboot between runs")
    ap.add_argument("--power-cycle-cmd", default=None,
                    help="shell command that cycles the board's power (true cold boot); default is a soft reboot")
    ap.add_argument("--bit", type=Path, default=DEFAULT_BIT)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("cold_boot_ber_campaign.json"))
    args = ap.parse_args()
    A = reg(DEFAULT_BASE_ADDR)

    agg = {name: dict(frames=0, clean=0, bit_errors=0, recv_bad=0, err_hist=Counter(), per_run=[])
           for (name, *_) in FABRIC_MODES}
    runs_loaded = runs_all_clean = 0
    load_failures = []

    def save(done):
        args.out.write_text(json.dumps(summarise(agg, args.runs, runs_loaded, runs_all_clean,
                                                 load_failures, args), indent=2), encoding="utf-8")

    for r in range(args.runs):
        try:
            if not args.no_cold_boot:
                if not cold_boot(args.power_cycle_cmd):
                    load_failures.append(dict(index=r, note="board did not return after cold boot"))
                    print(f"[run {r:3d}] BOARD DOWN after cold boot")
                    save(False)
                    continue
            runner = new_runner()
            try:
                ident = load_bitstream(runner, args.bit)
                ok = isinstance(ident, dict) and int(str(ident.get("core_id", "0")), 16) == GPREG_ID
                if not ok:
                    load_failures.append(dict(index=r, note="gpreg id mismatch", gpreg=ident,
                                              dmesg=dmesg_tail(runner)))
                    print(f"[run {r:3d}] LOAD FAIL gpreg={ident}")
                    save(False)
                    continue
                runs_loaded += 1
                run_clean = True
                for (name, ctrl, frame, pre, off, bpf) in FABRIC_MODES:
                    cl = be = rb = 0
                    hist = Counter()
                    for _ in range(args.frames):
                        recv, err = burst(runner, A, ctrl, frame, pre, off)
                        if recv != frame:
                            rb += 1
                            run_clean = False
                            hist["recv_bad"] += 1
                            continue
                        be += err
                        hist[err] += 1
                        if err == 0:
                            cl += 1
                        else:
                            run_clean = False
                    m = agg[name]
                    m["frames"] += args.frames
                    m["clean"] += cl
                    m["bit_errors"] += be
                    m["recv_bad"] += rb
                    m["err_hist"] += hist
                    m["per_run"].append(dict(clean=cl, bit_errors=be, recv_bad=rb))
                if run_clean:
                    runs_all_clean += 1
                tags = " ".join(f"{n}:{agg[n]['per_run'][-1]['clean']}/{args.frames}"
                                f"({agg[n]['per_run'][-1]['bit_errors']}e,{agg[n]['per_run'][-1]['recv_bad']}nf)"
                                for n, *_ in FABRIC_MODES)
                print(f"[run {r:3d}] loaded {ident.get('core_id')}  {tags}  {'CLEAN' if run_clean else 'DIRTY'}")
            finally:
                try:
                    runner.close()
                except Exception:
                    pass
        except Exception as e:
            load_failures.append(dict(index=r, note=f"exception: {e}", trace=traceback.format_exc()))
            print(f"[run {r:3d}] EXCEPTION {e}")
        save(False)

    save(True)
    reboot_to_stock()

    s = json.loads(args.out.read_text(encoding="utf-8"))
    print("\n" + "=" * 72)
    print(f"COLD-BOOT CAMPAIGN  ({args.runs} runs, "
          f"{'power-cycle' if args.power_cycle_cmd else ('single load' if args.no_cold_boot else 'soft-reboot each')})")
    lo, hi = s["load_wilson_95"]
    print(f"  loaded ok        {runs_loaded}/{args.runs}   Wilson95 [{lo:.3f}, {hi:.3f}]")
    lo, hi = s["run_clean_wilson_95"]
    print(f"  all-clean runs   {runs_all_clean}/{args.runs}   Wilson95 [{lo:.3f}, {hi:.3f}]")
    for name, rte in s["modes"].items():
        print(f"  --- {name} ---  bits {rte['bits_checked']}, errors {rte['bit_errors']}")
        print(f"      {rte.get('ber_statement', 'n/a')}")
        print(f"      FER {rte['fer_point']}  Wilson95 [{rte['fer_wilson_95'][0]:.2e}, {rte['fer_wilson_95'][1]:.2e}]")
    if load_failures:
        print(f"  LOAD/BOOT FAILURES: {len(load_failures)} (see JSON)")
    print(f"\nsaved -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
