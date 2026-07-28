# Lab 8.8 — QPSK modem, impairments and BER

## Goal

Extend the BPSK path to QPSK with two bits per symbol and verify two implementation levels:

1. a synthesizable QPSK modem that recovers a complete frame at `BER = 0` in ideal HDL loopback;
2. an AWGN/CFO channel model that shows how impairments affect the constellation and BER.

## Modem and verification

QPSK uses two orthogonal BPSK axes. The mapper creates Gray-coded points before the shared chain performs upsampling, RRC filtering, symbol sampling and hard decisions:

```text
dibit source → QPSK mapper → upsampler → RRC TX → loopback →
RRC RX → symbol sampler → hard decision → BER counter
```

The `tb_qpsk_zynq_ber_top` testbench checks 140 symbols / 280 bits at `BER = 0`.

## Impairments

- AWGN spreads the four clusters and eventually moves samples across decision boundaries.
- CFO rotates the constellation from symbol to symbol and turns the four points into a ring without correction.
- Gray QPSK has the same theoretical per-bit error probability as BPSK: `Q(√(2·Eb/N0))`.

## Reproduce

```bash
python blocks/block_08_modulation_and_synchronization/python/qpsk_impairments_ber.py
python tools/run_block5_hdl_smoke.py
```

Expected result: the simulated BER curve follows theory, HDL loopback passes without errors, and the CFO case demonstrates why carrier recovery is required.

## Next step

[Lab 8.9](lab-8-9-qpsk-carrier-recovery.md) closes the CFO problem with a Costas loop and known-preamble resolution of the `90°` ambiguity.
