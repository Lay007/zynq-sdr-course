# Lab 11.31 — Coarse-CFO estimator stress sweep

## Objective

[Lab 11.30](lab_11_30_two_board_cfo_validation.md) proved the `qpsk_coarse_cfo.v` estimator on a
live two-board link — but the two AD9361s happened to sit only ~0.3 ppm apart, an inter-board
carrier offset of about **−290 Hz**. That is *inside* a Costas loop's few-hundred-hertz pull-in,
so the estimator's whole reason for existing — acquiring the **tens of kHz** a Costas loop cannot
— was never actually exercised on silicon. A passing run at −290 Hz does not tell you the
estimate is right at −40 kHz.

This lab injects a **controlled** offset. Board A transmits the same cyclic QPSK at `carrier + Δ`
while board B receives at `carrier`, so the recovered signal carries a known Δ (plus the intrinsic
−290 Hz). Sweeping Δ across ±70 kHz demonstrates three properties on a real signal at once:

1. the 4th-power estimator **tracks** the injected CFO across the whole ±60 kHz unambiguous range;
2. the fixed-point RTL arithmetic **agrees with the float reference** at every offset, not just
   near zero;
3. beyond ±60 kHz the estimate **folds (aliases)** by 120 kHz, exactly as `4·ω ∈ (−π, π]`
   predicts — the design's ambiguity boundary, demonstrated rather than asserted.

## Why ±60 kHz

The estimator raises each symbol to the 4th power to strip the QPSK modulation (the four
constellation points map to one), leaving a tone at `4·ω` where `ω` is the per-symbol phase
increment from the CFO. It then measures that tone's angle. An angle is only unambiguous over one
turn, so `4·ω` must stay inside `(−π, π]`:

```
|ω| < π/4  per symbol   →   |f| < Rsym/8 = 480 kSym/s / 8 = 60 kHz
```

Below 60 kHz the estimate is the true CFO. Above it, `4·ω` wraps, and the reported frequency folds
back by `2·60 = 120 kHz` — an alias, not an error. This lab drives the estimator straight through
that boundary so the fold is visible in the data.

## Setup

```
board A  ──  cyclic QPSK out of the DAC via DMA, TX_LO = carrier + Δ
   │
   │   TX1 ──▶ 30 dB attenuator ──▶ RX1     (contained SMA cable, 915 MHz base)
   ▼
board B  ──  RX_LO = carrier (fixed) ──▶ raw IQ capture ──▶ SSH ──▶ host estimator
```

The CFO is injected purely by **detuning board A's transmit LO** — the waveform, the sample rate
and board B's receive LO never change — so the recovered offset is Δ plus the boards' intrinsic
difference, and nothing else. The lab reuses Lab 11.30's transmitter and receiver plumbing
verbatim (`reset_tx_dma`, detached streaming, DAC-source readback, one contiguous capture); see
that lab for the traps those guard against.

## Method

Per Δ: quiet both boards, retune board A's `TX_LO_frequency` to `carrier + Δ`, stream the cyclic
QPSK, capture on board B, and run the **same** float and fixed-point estimators from
`coarse_cfo_ref.py` over the recovered symbols (matched filter → best integer sub-symbol phase →
4th-power estimate over successive 256-symbol windows). The `dTX=0` row is measured first and its
result is the intrinsic offset that every expected value is referenced against.

The fixed-point column applies the RTL's `SQ_SHIFT=11` truncation to symbols rescaled to the
~2000-LSB matched-filter magnitude seen on real captures, so `f-vs-fx` is the gap between the
float reference and the **shipped HDL's integer arithmetic**, not between two floats.

## Results

Measured 2026-07-18, 915 MHz base, board A TX −30 dB into a 30 dB attenuator, board B RX 50 dB.
Intrinsic offset at `dTX=0`: **−238 Hz**. It drifts run to run with temperature and reference
tolerance — −194, −238 and −288 Hz across three cold boots — which is exactly why the estimator
exists; the injected Δ is what the table is keyed on.

| dTX | measured CFO | std | expected (folded) | error | EVM | float-vs-fixed | note |
|------:|-------------:|-----:|------------------:|-------:|-----:|---------------:|:------|
| +0.0 kHz  | −238 Hz     | 18   | −238 Hz     | +0 Hz    | 4.7 % | 0.15 Hz | intrinsic |
| +5.0 kHz  | +4 605 Hz   | 187  | +4 762 Hz   | −157 Hz  | 20 %  | 0.78 Hz | |
| +10.0 kHz | +9 368 Hz   | 42   | +9 762 Hz   | −394 Hz  | 36 %  | 1.39 Hz | |
| +20.0 kHz | +19 218 Hz  | 416  | +19 762 Hz  | −545 Hz  | 43 %  | 2.76 Hz | |
| +30.0 kHz | +29 371 Hz  | 1341 | +29 762 Hz  | −392 Hz  | 49 %  | 4.53 Hz | |
| +40.0 kHz | +39 222 Hz  | 113  | +39 762 Hz  | −540 Hz  | 40 %  | 2.39 Hz | |
| +50.0 kHz | +49 565 Hz  | 333  | +49 762 Hz  | −197 Hz  | 29 %  | 1.80 Hz | |
| −10.0 kHz | −9 897 Hz   | 93   | −10 238 Hz  | +341 Hz  | 37 %  | 1.20 Hz | |
| −30.0 kHz | −29 563 Hz  | 307  | −30 238 Hz  | +675 Hz  | 42 %  | 2.91 Hz | |
| −50.0 kHz | −49 995 Hz  | 616  | −50 238 Hz  | +243 Hz  | 42 %  | 1.55 Hz | |
| +55.0 kHz | +54 623 Hz  | 324  | +54 762 Hz  | −139 Hz  | 29 %  | 1.38 Hz | |
| +60.0 kHz | +59 708 Hz  | 67   | +59 762 Hz  | −54 Hz   | 9.6 % | 0.25 Hz | **boundary** |
| +70.0 kHz | **−50 106 Hz** | 259 | −50 238 Hz | +132 Hz  | 24 %  | 1.07 Hz | **alias → −50.2 kHz** |
| −70.0 kHz | **+49 496 Hz** | 136 | +49 762 Hz | −266 Hz  | 26 %  | 1.45 Hz | **alias → +49.8 kHz** |

Reading the table:

- **Tracking.** From −50 kHz to +55 kHz the measured CFO follows the injected offset with a few
  hundred hertz of error — well inside a Costas loop's pull-in. That is exactly the division of
  labour the two-stage receiver is built on: coarse removes the bulk, the loop closes the residual.
- **The fold.** At +70 kHz the estimate does not read +70 kHz and it is not wrong — it reads
  −50.2 kHz, precisely `70 − 120`. −70 kHz folds to +49.8 kHz the same way. The boundary row at
  +60 kHz is the hinge: `4·ω` sits just short of `π`, EVM drops back to single digits because the
  derotated constellation is nearly aligned, and one hair further wraps it. Right *on* the
  singularity a burst's windows split between +60 and −60 kHz — the same point on the 4·ω circle —
  so the per-window estimates are combined with a **circular mean** (in the 4·ω domain), not a plain
  average that would land on the meaningless midpoint. Away from the boundary the two agree to under
  a hertz; only this row depends on it.
- **Float vs fixed.** The RTL's integer arithmetic stays within **~4.5 Hz** of the float reference
  across the entire range — the fixed-point truncation is not what limits the estimate; the finite
  measurement window is (note how `std` tracks EVM, both worst near ±30 kHz where the raw
  constellation spins fastest within a window).

The mid-sweep EVM values are high **by construction**: EVM here is measured on the raw recovered
symbols *before* the Costas loop removes the residual, so a large injected CFO smears the
constellation. It is a witness that a real offset is present, not a link-quality figure — the
downstream loop is what turns these into decodable symbols (and did, at BER 0, in Lab 11.30).

## Self-test (no radio)

```
python python/lab_11_31_coarse_cfo_stress_sweep.py --self-test
```

Applies each Δ to the *generated* waveform in software (`×e^{j2πΔn/fs}`) and runs the identical
recovery. With no radio the intrinsic offset is zero, so the estimator must track each Δ to within
a few hundred hertz and fold cleanly at the boundary; the error is itself folded into ±60 kHz so
the ±60 kHz singularity (where the estimate may legitimately take either sign) does not read as a
120 kHz miss. Run it before any hardware session if you have touched the host-side analysis.

## Run it on hardware

```
python python/lab_11_31_coarse_cfo_stress_sweep.py \
    --host-a 192.168.40.1 --host-b 192.168.20.1 --carrier 915e6
```

Both boards must be flashed with the bench image (per-board `README-bench.txt` on each SD card).
The sweep is unattended and self-cleaning: it retunes, streams, captures and quiets board A between
every Δ, and forces both boards to −89.75 dB on exit — including after a failure. Results are
written to `coarse_cfo_stress_sweep.json` alongside the printed table.

## RF safety

This is a **conducted** lab: board A's TX1 reaches board B's RX1 through a cable and a 30 dB
attenuator, and nothing radiates. The default −30 dB TX is safe behind that attenuator. Over the
air the limit is **−50 dB** — do not raise power to "see the signal", and do not run this sweep on
an antenna. Both boards are quieted on exit; board B's stock `rc.user` re-arms a 71 MHz
transmitter on every boot, which the shared plumbing kills before anything else.

## What this unlocks

The estimator is validated end to end on silicon across its full operating range, which was the
precondition for wiring it into the fabric receiver. `qpsk_rx_bit_recovery_chain` can instantiate it
ahead of the Costas loop behind a `coarse_cfo_en` bit, `qpsk_zynq_ber_top` exposes that bit, and the
gpreg bridge drives it from **`gp_ctrl[13]`** — so the offset can be stripped in fabric at runtime
with a single register write. The [Block 05 smoke suite](../block_05_fpga_hdl_flow/) covers the whole
path from the bridge down, and the estimator decodes a 25 kHz injected offset to BER 0.

Timing, however, is **not yet closed**: the 4th-power multiply-accumulate is deep and does not meet
the fast divide-select clock, and synthesis/phys-opt hides intermediate registers a name-based
multicycle cannot reach (pipelining the accumulate moved the failing stage but did not close it). So
the estimator is gated behind a **compile-time `COARSE_ENABLE` (default 0)**: the stock bitstream
compiles the datapath out entirely and keeps its clean baseline timing, and the coherent loopback
still decodes at BER 0/280 through a plain passthrough. The remaining step is to pipeline the
4th-power datapath (or apply post-place timing directives) so it closes, then rebuild with
`COARSE_ENABLE=1` and re-run the two-board link with `gp_ctrl[13]=1` — the receiver acquiring the
real inter-board CFO **in fabric** rather than on the host.
