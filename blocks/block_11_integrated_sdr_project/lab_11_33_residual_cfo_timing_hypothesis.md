# Lab 11.33 — Residual-CFO pull-in and a rejected timing hypothesis

## Goal

Turn the low clean-attempt rate left by Lab 11.32 into a falsifiable diagnosis. The lab uses
the exact `core_rx` samples retained by the bridge BRAM, RTL replay, timing-closed Vivado
builds, and equal-budget live two-board runs. A change is accepted only if it improves the
physical link, not merely the replay.

## What the captures disproved

The cyclic frame repeats every 1120 ADC samples over the live portion of the captures. No
meaningful within-frame sample-clock walk is visible across a 140-symbol frame. The immediate
failure was therefore not the continuous timing drift originally suspected after Lab 11.32.

One 30 kHz two-board capture reproduced the carrier failure exactly in Icarus:

| Receiver | Received | Errors |
|---|---:|---:|
| original Costas settings | 140 symbols | 124 / 280 bits |
| `KI_LOG=4`, acquisition 64 symbols, tracking `KP_LOG=7` | 140 symbols | 0 / 280 bits |

The tuned loop was accepted and built into the boot image. On the conducted link at +30 kHz
CFO, offset 4 produced **27/40 BER=0 attempts** and **39/40 full frames**. This is a useful
improvement, but still not a continuous BER=0 receiver.

## The attractive change that was rejected

The next hypothesis was that the feedforward phase picker ranked phases while the 65-tap
matched filter was filling. A candidate waited eight symbols, accumulated the
rotation-invariant score `I²+Q²`, and delayed the intact preamble. It passed retained-capture
replay and all QPSK top/bridge tests.

The first combinational implementation was physically invalid: `WNS=-2.779 ns`,
`TNS=-1772.272 ns`, 3113 failing endpoints. Pipelining the DSP squares reduced this to one
endpoint at -0.002 ns; post-route physical optimization closed the candidate at
**WNS=+0.010 ns, TNS=0**, 75,689 fully routed nets and zero routing errors.

Timing closure did not make the algorithm a win. Equal 40-attempt live runs at the three
candidate offsets all lost to the accepted receiver:

| Receiver | Offset | Full frames | BER=0 frames | Clean-attempt rate |
|---|---:|---:|---:|---:|
| accepted L1 burst picker + tuned Costas | 4 | 39/40 | 27/40 | **67.5%** |
| settled `I²+Q²` candidate | 1 | 22/40 | 4/40 | 10.0% |
| settled `I²+Q²` candidate | 3 | 31/40 | 12/40 | 30.0% |
| settled `I²+Q²` candidate | 5 | 29/40 | 14/40 | 35.0% |

![Accepted receiver versus rejected timing picker](/zynq-sdr-course/assets/lab1133_residual_cfo_timing_hypothesis.png)

The candidate was removed from RTL and from the SD card. Board B was cold-booted back into
the accepted image and rechecked: FPGA `operating`, core ID `0x4250534B`, AD9361/XADC/capture
IIO devices present, TX at `-89.75 dB`.

## Reproduce the evidence assembly

The hardware attempts are produced by the Lab 11.32 runner. Lab 11.33 deliberately consumes
those raw per-attempt JSON files without hiding no-lock results:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_33_residual_cfo_timing_hypothesis.py `
  --accepted tmp/lab1133_30k_fixed4.json `
  --candidate tmp/lab1133_pipeline_30k_fixed1.json `
  --candidate tmp/lab1133_pipeline_30k_fixed3.json `
  --candidate tmp/lab1133_pipeline_30k_fixed5.json
```

Canonical summary: [`lab1133_residual_cfo_timing_hypothesis.json`](/zynq-sdr-course/assets/lab1133_residual_cfo_timing_hypothesis.json).

## Decision and next experiment

Keep the residual-CFO Costas tuning. Reject the settled squared-energy picker. The next step
is a genuine continuous QPSK timing-recovery loop with explicit acquisition/tracking state,
tested first against retained captures and then by a longer two-board BER campaign. The lab's
main result is methodological: simulation pass plus timing closure is necessary, but live A/B
evidence still has veto power.
