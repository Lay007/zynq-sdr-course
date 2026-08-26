# ADR 0003: Separate CSS sample data and control planes

[Русская версия](0003-css-accelerator-axi-boundary_ru.md)

**Status:** Accepted

**Date:** 2026-08-26

**Deciders:** Repository maintainers

## Context

The compact SF7 detector needs a Zynq PS/PL boundary that remains useful with
DMA, exposes software-readable diagnostics, and preserves AXI backpressure.
Sample-by-sample AXI-Lite writes would be slow; AXI-Lite-only results would also
couple every consumer to software polling.

## Decision

Use AXI4-Stream for packed Q1.15 input samples and one atomic 256-bit result
packet. Use AXI4-Lite for identification, control/status, a last-result snapshot,
counters, and IRQ. Keep all interfaces in one clock domain in the course top
level and place any CDC or data-width conversion in the system block design.

## Options considered

| Option | Complexity | DMA fit | Software observability | Decision |
|---|---:|---:|---:|---|
| AXI-Stream input/output plus AXI-Lite status | Medium | High | High | Accepted |
| AXI-Stream input, AXI-Lite-only result | Low | Medium | High | Rejected |
| AXI-Lite sample and result registers only | Low RTL / high software | Low | High | Rejected |

## Consequences

- Stream backpressure cannot lose a result.
- Software can inspect the last result without consuming the result stream.
- Fixed 128-beat grouping remains explicit; TLAST mismatch is diagnostic and
  does not implement packet resynchronization.
- A narrow DMA/interconnect may need a converter for the 256-bit result beat.
- Complete PS7 integration, address assignment, CDC decisions, and board timing
  remain system-level work.
