# Lab 11.29 — Cold-boot BER reliability campaign

## Objective

Turn "the modem decodes" into a number with a confidence interval. A single `10/10` says
nothing about the tails; this reboots the board many times, reloads the bitstream from a clean
state each time, and counts frames through the deterministic PL fabric loopback so that a run
of zero errors becomes a **bounded** BER rather than an unsupported "BER = 0".

## What it measures

Each run:

1. cold-boots the board (soft reboot by default: Linux + AD9361 re-init + overlay reload from
   stock; or a true power cycle, see below);
2. reloads our bitstream and checks the gpreg core id `0x4250534B` — a load-failure detector;
3. sprays `--frames` frames through the **fabric loopback** (`gp_ctrl[6]`: TX looped into RX
   inside the PL, no AD9361, no RF, bit-deterministic) for BPSK (281 bits/frame) and QPSK
   (280 bits/frame), counting received frames, clean frames, and bit errors.

Fabric loopback is the PL-correctness metric: it exercises the whole synthesized
mapper → upsampler → RRC → sampler → decision → frame-sync → BER-counter through the real
gpreg/CDC plane. Because it is error-free, every clean frame adds to a large deterministic bit
count.

## Statistics (no third-party dependency)

- **Run rates** (loaded, all-clean) — Wilson score interval, plus Clopper–Pearson when `scipy`
  is importable.
- **BER with zero errors in `m` bits** — one-sided upper bound `1 − 0.05^(1/m) ≈ 3/m` (rule of
  three). Reported as `BER < X`, never `BER = 0`.
- **FER** (frames with ≥1 error / returned frames) — Wilson interval.

The JSON summary is rewritten **after every run**, so a stopped or killed campaign still leaves
a complete, honest partial result.

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_29_cold_boot_ber_campaign.py \
  --runs 50 --frames 200
```

`--runs` 30–100 gives a useful interval width. The default `--bit` is
`tmp/bridge_txrx_mux.qpsk.wordswap.bit.bin`. The board is rebooted to stock at the end.

### True power cycle

The default "cold boot" is a soft reboot — what can be scripted without switchable power. With
a controllable supply, pass a command that cycles the board's power and the campaign runs it in
place of the soft reboot, then waits for the board to return:

```bash
python .../lab_11_29_cold_boot_ber_campaign.py --runs 50 \
  --power-cycle-cmd "your-smart-plug-cli --off && sleep 3 && your-smart-plug-cli --on"
```

## Result (2026-07-11, 50 soft cold boots, 200 frames/mode)

| | loaded | all-clean | bits | errors | BER (95% upper) |
|---|---|---|---|---|---|
| BPSK fabric | — | — | 2,810,000 | 0 | < 1.07 × 10⁻⁶ |
| QPSK fabric | — | — | 2,800,000 | 0 | < 1.07 × 10⁻⁶ |
| **combined** | **50/50** | **50/50** | **5,610,000** | **0** | **< 5.34 × 10⁻⁷** |

- Run-clean rate 50/50, Wilson 95% **[0.929, 1.0]**; zero load/boot failures.
- FER 0 on both modulations, Wilson 95% [0, 3.84 × 10⁻⁴]; error histogram `{0: 10000}` each.

So the synthesized PL modem comes up decoding on **every** cold boot, with a sub-microsecond
BER bound over 5.6 M deterministic bits.

## Timing-closure robustness

Companion tool `tools/timing_directive_sweep.tcl` checks whether the shipped timing closure is
a property of the design or of one lucky placement. Vivado 2021.1 has no numeric placement
seed, so it sweeps the placement *directive* (a stronger test — it swaps the algorithm):

```bash
/g/Xilinx/Vivado/2021.1/bin/vivado.bat -mode batch -notrace -source tools/timing_directive_sweep.tcl
```

Result — **ROBUST**, all five strategies met timing:

| directive | WNS (ns) | TNS |
|---|---|---|
| Default | +0.087 | 0 |
| Explore (shipped) | +0.123 | 0 |
| WLDrivenBlockPlacement | +0.017 | 0 |
| ExtraNetDelay_high | +0.171 | 0 |
| ExtraPostPlacementOpt | +0.122 | 0 |

Worst across genuinely different placements is +0.017 ns (WLDriven) — positive, and the margin
to watch as the RTL grows. The sweep leaves `impl_1` on the last directive; re-run the normal
build to restore the shipped Explore placement.

## RF safety

Fabric loopback never configures or raises TX — the board stays at the stock −89.75 dB
throughout, and the campaign reboots to stock at the end. Nothing radiates.
