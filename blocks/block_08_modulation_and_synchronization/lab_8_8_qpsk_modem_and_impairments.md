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
the Block-5 HDL smoke (`tools/run_block5_hdl_smoke.sh`, target `tb_qpsk_zynq_ber_top`). Per
symbol QPSK carries 2 bits, so at the same symbol rate/bandwidth as BPSK it doubles the bit
rate — that is the whole point of QPSK.

## Impairments: what noise and CFO do to the constellation

![QPSK constellation under impairments](https://lay007.github.io/zynq-sdr-course/assets/qpsk_constellation_impairments.png)

- **Ideal** — four clean points at (±1, ±1)/√2.
- **AWGN 10 dB** — four tight clouds; decisions still trivially correct.
- **AWGN 4 dB** — clouds spread and start to cross the I/Q axes → bit errors appear.
- **CFO (uncorrected)** — a frequency offset rotates every symbol by a growing phase, so the
  four points smear into a **ring**: without carrier recovery QPSK is undecodable. This is
  the phase/frequency problem of [Lab 8.1](lab_8_1_cfo_estimation_correction.md) /
  [Lab 8.2](lab_8_2_phase_offset_correction.md), and de-rotating that ring is exactly what a
  carrier-recovery loop (Costas / 4th-power) does before the hard decision.

## BER vs Eb/N0

![Gray QPSK BER vs Eb/N0](https://lay007.github.io/zynq-sdr-course/assets/qpsk_ber_vs_ebn0.png)

Because Gray QPSK is two orthogonal BPSK axes, its per-bit BER equals the BPSK curve,
`BER = Q(√(2·Eb/N0))`, and the simulation lands on that theory line across 0–10 dB. So QPSK
buys **2× the bit rate at the same Eb/N0 and BER** as BPSK — you pay with a denser
constellation (smaller noise margin at a given Es/N0), not with energy per bit.

## Reproduce

```bash
# HDL modem loopback (BER = 0) — part of the Block-5 smoke:
bash tools/run_block5_hdl_smoke.sh        # -> PASS: qpsk_zynq_ber_top loopback ... BER=0

# Impairment figures (BER curve + constellations):
python blocks/block_08_modulation_and_synchronization/python/qpsk_impairments_ber.py
```

## Next steps

- **Carrier recovery** (Costas / 4th-power) to de-rotate the CFO ring — turns the smeared
  constellation back into four points for over-the-air QPSK.
- **Hardware**: drop the QPSK modem into the runtime AD9361 bridge (same DAC-mux / ADC-tap /
  gpreg plane as the BPSK bridge in [Lab 11.26](../block_11_integrated_sdr_project/lab_11_26_runtime_dds_bypass_bpsk_ota.md))
  for QPSK BER = 0 in digital loopback, then the real-hardware constellation of
  [Lab 8.7](lab_8_7_real_hardware_bpsk_metrics.md) with four points instead of two.
