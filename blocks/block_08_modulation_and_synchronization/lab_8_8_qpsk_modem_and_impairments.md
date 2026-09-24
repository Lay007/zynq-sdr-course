# Lab 8.8 — QPSK modem, impairments and BER

## Goal

Extend the BPSK path to **QPSK** (two bits per symbol, four constellation points) and
study how the two classic impairments of this block — **noise** and a **carrier frequency
offset (CFO)** — hit the constellation and the bit-error rate. Two layers:

1. a synthesizable **QPSK modem** that recovers a full frame at **BER = 0** in an ideal
   HDL loopback (the RTL you would put on the FPGA), and
2. a **channel/impairment simulation** that adds AWGN and CFO and plots the BER-vs-Eb/N0
   curve against theory.

## The QPSK modem (HDL, ideal loopback)

QPSK is just **two independent BPSK axes**: the low bit drives I, the high bit drives Q
(Gray-coded, so one bit flip moves to an adjacent corner). So the modem reuses the shared
complex-I/Q blocks of the BPSK chain unchanged — `bpsk_upsampler_8x`, `bpsk_rrc_tx_fir`,
`bpsk_rrc_rx_fir`, `bpsk_symbol_timing_sampler` — and only the mapper / decision / framing
are QPSK-specific:

```
dibit source -> qpsk_symbol_mapper -> upsampler -> RRC TX  ── loopback ──►
    RRC RX (matched filter) -> fixed-phase sampler -> qpsk_hard_decision -> qpsk_ber_counter
```

`tb_qpsk_zynq_ber_top` loops TX I/Q straight back into RX and sweeps the sampling phase:
it recovers all **140 QPSK symbols (280 bits) at BER = 0** (start_offset = 62). Run it via
the Block-5 HDL smoke (`python tools/run_block5_hdl_smoke.py`, target `tb_qpsk_zynq_ber_top`). Per
symbol QPSK carries 2 bits, so at the same symbol rate/bandwidth as BPSK it doubles the bit
rate — that is the whole point of QPSK.

## Impairments: what noise and CFO do to the constellation

![QPSK constellation under impairments](/zynq-sdr-course/assets/qpsk_constellation_impairments.png)

- **Ideal** — four clean points at (±1, ±1)/√2.
- **AWGN 10 dB** — four tight clouds; decisions still trivially correct.
- **AWGN 4 dB** — clouds spread and start to cross the I/Q axes → bit errors appear.
- **CFO (uncorrected)** — a frequency offset rotates every symbol by a growing phase, so the
  four points smear into a **ring**: without carrier recovery QPSK is undecodable. This is
  the phase/frequency problem of [Lab 8.1](/zynq-sdr-course/en/labs/lab-8-1-cfo-estimation-correction/) /
  [Lab 8.2](/zynq-sdr-course/en/labs/lab-8-2-phase-offset-correction/), and de-rotating that ring is exactly what a
  carrier-recovery loop (Costas / 4th-power) does before the hard decision.

## BER vs Eb/N0

![Gray QPSK BER vs Eb/N0](/zynq-sdr-course/assets/qpsk_ber_vs_ebn0.png)

Because Gray QPSK is two orthogonal BPSK axes, its per-bit BER equals the BPSK curve,
`BER = Q(sqrt(2*Eb/N0))`, and the simulation lands on that theory line across 0-10 dB. So QPSK
buys **2x the bit rate at the same Eb/N0 and BER** as BPSK: you pay with a denser
constellation (smaller noise margin at a given Es/N0), not with energy per bit.

The default run prints the simulated BER at each integer Eb/N0 from 0 to 10 dB:

| Eb/N0 | 0 dB | 2 dB | 4 dB | 6 dB | 8 dB | 10 dB |
|---|---:|---:|---:|---:|---:|---:|
| simulated BER | 7.89e-2 | 3.77e-2 | 1.26e-2 | 2.39e-3 | 2.2e-4 | 0 |
| theory `Q(sqrt(2*Eb/N0))` | 7.86e-2 | 3.75e-2 | 1.25e-2 | 2.39e-3 | 1.91e-4 | 3.9e-6 |

The two rows agree down to Monte Carlo noise. **The 0 at 10 dB is a resolution limit, not an
error-free link:** the run compares 400 000 bits, where theory predicts about 1.6 errors at
3.9e-6, so seeing none is unremarkable and the curve can only resolve BER down to about 2.5e-6
(the same "BER = 0 needs a stated bit count" rule as in
[Lab 8.7](/zynq-sdr-course/en/labs/lab-8-7-snr-vs-ber-traps/)).

## Reproduce

```bash
# HDL modem loopback (BER = 0) — part of the Block-5 smoke:
python tools/run_block5_hdl_smoke.py      # -> PASS: qpsk_zynq_ber_top loopback ... BER=0

# Impairment figures (BER curve + constellations):
python blocks/block_08_modulation_and_synchronization/python/qpsk_impairments_ber.py
```

## Exercises

1. At 8 dB the table shows 2.2e-4 against a theory of 1.91e-4. Convert both to error counts out of 400 000 bits (88 and about 76) and decide whether the difference is significant, using the Poisson standard deviation (about the square root of the count).
2. At Eb/N0 = 6 dB, what is Es/N0 for QPSK? Explain why the per-bit BER still equals BPSK at the same Eb/N0 although the QPSK points are closer together for the same symbol energy.
3. Replace the Gray mapping with a natural one (dibits 00, 01, 10, 11 on consecutive quadrants). Predict the BER ratio before you run it. A quick simulation of this change gave about 1.4-1.5 times the Gray BER at 0, 4 and 8 dB (for example 1.89e-2 against 1.27e-2 at 4 dB): with natural mapping one of the two neighbouring quadrants differs in both bits, so an average symbol error costs 1.5 bits instead of 1.
4. The HDL loopback prints `PASS: qpsk_zynq_ber_top loopback recovered 140 QPSK symbols at BER=0 (start_offset=62)`. How many bits is that, and what is the smallest BER this single run can claim?

## Next steps

- **Carrier recovery** — a decision-directed Costas loop de-rotates the CFO ring back into four
  points (and resolves the residual 90° ambiguity with the preamble): done in
  **[Lab 8.9 — QPSK carrier recovery](/zynq-sdr-course/en/labs/lab-8-9-qpsk-carrier-recovery/)**.
- **Hardware**: the QPSK modem now runs in the runtime AD9361 bridge and decodes at BER = 0 in
  digital loopback ([Lab 11.27](/zynq-sdr-course/en/labs/lab-11-27-runtime-qpsk-digital-loopback/), which uses the
  same DAC-mux / ADC-tap / gpreg plane as the BPSK bridge in
  [Lab 11.26](/zynq-sdr-course/en/labs/lab-11-26-runtime-dds-bypass-bpsk-ota/)), and
  over the air on a two-board link ([Lab 11.4](/zynq-sdr-course/en/labs/lab-11-4-final-measurement-report/)). The real-hardware
  constellation of [Lab 8.15](/zynq-sdr-course/en/labs/lab-8-15-real-hardware-bpsk-metrics/) with four points instead
  of two is still to be repeated for QPSK.
