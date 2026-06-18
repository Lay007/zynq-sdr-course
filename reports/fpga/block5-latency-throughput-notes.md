# Block 5 Latency and Throughput Notes

These notes record the latency and streaming-rate behaviour validated by the existing self-checking Block 5 HDL testbenches.

## Verification basis

| Source | What it proves |
|---|---|
| `blocks/block_05_fpga_hdl_flow/tb/tb_iq_passthrough.v` | one-cycle latency for valid-only passthrough |
| `blocks/block_05_fpga_hdl_flow/tb/tb_fir_iq_4tap.v` | one-cycle latency with deterministic vector matching |
| `blocks/block_05_fpga_hdl_flow/tb/tb_nco_mixer_iq.v` | one-cycle latency for the compact NCO mixer |
| `blocks/block_05_fpga_hdl_flow/tb/tb_axis_iq_passthrough.v` | one-cycle AXI-Stream transfer latency and clean backpressure behaviour |

## Latency and throughput summary

| Block | Latency, cycles | Sustained throughput | Interface model | Note |
|---|---:|---|---|---|
| `iq_passthrough` | 1 | 1 complex sample / clock when `in_valid=1` | valid-only | pure register stage |
| `fir_iq_4tap` | 1 | 1 complex sample / clock | valid-only | fully parallel 4-tap datapath |
| `nco_mixer_iq` | 1 | 1 complex sample / clock | valid-only | fixed-point mixer with LUT + DSP multipliers |
| `axis_iq_passthrough` | 1 | 1 AXI-Stream beat / clock while `m_axis_tready=1` | AXI-Stream | stalls safely under backpressure |

## SDR interpretation

- A one-cycle latency across all four blocks keeps the educational chain easy to reason about when matching RTL vectors against Python or fixed-point models.
- The valid-only blocks are appropriate for simple sample-by-sample DSP demonstrations, while `axis_iq_passthrough` is the right hand-off point toward a real Zynq DMA or AXI-Stream data path.
- The combination of zero BRAM usage and one-sample-per-clock throughput means the immediate scaling risk is not memory, but timing closure once multiple arithmetic stages are chained.
