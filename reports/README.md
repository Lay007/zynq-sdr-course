# Reports

This directory stores report templates and lightweight report examples that are useful for course review.

## Policy

- Keep large generated vendor reports out of the repository unless they are intentionally curated.
- Prefer concise Markdown summaries with links to raw tool output when needed.
- Include commit hash, tool version and board/device name in every hardware or FPGA report.

## Subdirectories

| Path | Purpose |
|---|---|
| `fpga/` | FPGA utilization, timing, latency and throughput summaries |

## Current curated FPGA reports

| File | Purpose |
|---|---|
| `fpga/z7020-resource-summary-template.md` | board-level OOC resource summary with real numbers |
| `fpga/block5-utilization-summary.md` | per-module LUT/FF/DSP/BRAM summary |
| `fpga/block5-timing-summary.md` | per-module timing summary at 100 MHz |
| `fpga/block5-latency-throughput-notes.md` | latency and throughput notes from HDL testbenches |
| `fpga/vivado_ooc_raw/block5_vivado_ooc_metrics.json` | machine-readable summary of the Vivado OOC run |

## Recommended report types

- FPGA resource summary.
- Timing summary.
- Hardware validation note.
- Final measurement report.
- Dataset analysis report.
