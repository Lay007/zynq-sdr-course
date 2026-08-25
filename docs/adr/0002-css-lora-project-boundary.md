# ADR 0002: Split educational CSS RTL from the complete LoRa PHY

## Status

Accepted — 2026-08-25

## Context

The course and the companion
[`zynq-lora-phy-positioning`](https://github.com/Lay007/zynq-lora-phy-positioning)
repository both contain chirp processing. Uncoordinated development had produced
two different dechirp arithmetic contracts inside the course and risked copying a
large generated LoRa correlator into an educational code path.

The course needs small readable RTL that exposes fixed-point effects and can run
quickly in Icarus Verilog. The positioning project needs a complete interoperable
LoRa PHY, oversampled acquisition, packet framing, timing/CFO estimation, ToA/TDoA,
generated HDL and Zynq board integration.

## Decision

The repositories have different canonical responsibilities:

- `zynq-sdr-course` owns the generic CSS learning route: waveform, dechirp, a
  compact SF7 sequential detector, bit-exact Python vectors and self-checking RTL;
- `zynq-lora-phy-positioning` owns the complete LoRa implementation: SF5–SF12,
  oversampled two-FFT correlation, packet coding/framing, synchronization,
  timestamp metadata, ToA/TDoA and hardware acceptance;
- the course may explain or link the production architecture, but does not copy
  HDL Coder output or claim LoRa interoperability from its compact detector;
- inside the course, the registered saturating Q1.15 Block 8 dechirp is the only
  canonical arithmetic contract. Alternative unsaturated Block 5 RTL is retired.

## Options considered

| Option | Complexity | Reproducibility | Educational value | Decision |
|---|---:|---:|---:|---|
| Duplicate the complete LoRa correlator in both repositories | High | Low | Low | Rejected |
| Make the course depend on a sibling checkout | Medium | Low | Medium | Rejected |
| Keep a compact independent CSS baseline and link the full PHY | Low | High | High | Accepted |

## Consequences

- Course CI remains vendor-independent and numerically self-checking.
- The compact detector is an architectural baseline, not the final SF5–SF12 FFT
  accelerator described by issue #46.
- Cross-project comparisons must state input scaling explicitly: the course uses
  Q1.15 IQ, while the generated LoRa correlator currently exposes signed 16-bit
  inputs with 10 fractional bits.
- Full LoRa performance and RF/positioning claims must cite evidence from the
  companion repository.

## Follow-up

1. Keep the course all-symbol SF7 regression green.
2. Add AXI-Stream/AXI-Lite only as a separate, reviewable course increment.
3. Use the companion project for SF/BW mode coverage and board-level evidence.
4. Revisit this boundary if a small shared vector-format package becomes useful;
   do not introduce a runtime dependency between the repositories.
