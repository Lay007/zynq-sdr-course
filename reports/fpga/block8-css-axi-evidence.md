# Block 8 CSS AXI accelerator: Vivado OOC implementation evidence

[Русская версия](block8-css-axi-evidence_ru.md)

## Result

Vivado 2021.1 fully routes `css_sf7_axi_accelerator` out of context and meets
the `100 MHz` constraint on `xc7z020clg400-2`:

| Metric | Post-route result |
|---|---:|
| WNS / TNS | `+0.165 ns` / `0.000 ns` |
| Failing endpoints | `0 / 3018` |
| Critical data-path delay | `9.712 ns` |
| Critical-period estimate | `101.678 MHz` |
| Fully routed nets | `2135 / 2135` |
| Routing errors / DRC errors | `0 / 0` |

The critical path remains inside the sequential DFT, from its sample-index
state through distributed sample memory and DSP48 arithmetic to the registered
term. The AXI-Stream result registers and AXI-Lite control plane do not become
the critical path.

## Resources

| Resource | Post-synthesis | Post-route | XC7Z020 available |
|---|---:|---:|---:|
| Slice LUT | 849 | 787 | 53,200 |
| Slice registers | 867 | 867 | 106,400 |
| BRAM tiles | 1.5 | 1.5 | 140 |
| DSP48E1 | 16 | 16 | 220 |

Compared with the isolated detector's routed result, the AXI boundary adds 156
LUTs and 446 registers while preserving the BRAM and DSP counts. The register
increase is dominated by the held 256-bit output packet and the AXI-Lite result
snapshot.

## Reproduction

Run from the repository root on Windows:

```powershell
python tools/generate_block8_css_axi_vivado_reports.py
```

To revalidate existing reports without rerunning Vivado:

```powershell
python tools/generate_block8_css_axi_vivado_reports.py --reuse
```

The source-only flow creates an in-memory project, constrains `aclk` to
`10.000 ns`, and runs synthesis, optimization, placement, physical
optimization, and routing. It commits no project, checkpoint, bitstream, log,
or journal.

## Latency and throughput

RTL regression proves 16,644 clocks from the final accepted sample to the AXI
result and 16,645 clocks to the AXI-Lite sticky status/IRQ. At 100 MHz the
symbol initiation interval remains 16,772 clocks, or 5,962.318 decisions/s.

## DRC and evidence limits

The final DRC has no error-severity violations. Its 46 warning-level violations
are the same OOC methodology findings as the detector-only run: 44 DSP48
pipelining recommendations, one unloaded internal-status warning, and the
expected missing-PS7 warning. OOC stream/register ports have no I/O delays or
`HD.PARTPIN_LOCS`.

This proves routed internal timing for the AXI RTL top, not a complete Zynq
block design. PS7, AXI interconnect/DMA, clock/reset infrastructure, address
assignment, and board constraints are still absent; no bitstream or hardware
test has been performed.

Machine-readable metrics and normalized reports are in
`reports/fpga/block8_css_axi_vivado_ooc_raw/`.
