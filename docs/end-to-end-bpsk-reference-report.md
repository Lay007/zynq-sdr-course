# End-to-end BPSK reference report

This page defines the first executable modem route for the course:

```text
MATLAB reference -> fixed-point export -> HDL symbol mapper -> future Zynq TX/RX BER flow
```

It is still synthetic, but it already produces the shared files that the Simulink and Verilog stages can consume directly.

## How to run

From the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/end_to_end_bpsk_reference.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_symbol_mapper_vectors.py
iverilog -g2012 -o blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_symbol_mapper.out ^
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v ^
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_symbol_mapper.v
vvp blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_symbol_mapper.out
```

## Generated artifacts

| Artifact | Path | Role |
|---|---|---|
| TX spectrum | `docs/assets/end_to_end_bpsk_reference_tx_spectrum.png` | Verifies pulse-shaped burst occupancy. |
| Capture spectrum | `docs/assets/end_to_end_bpsk_reference_capture_spectrum.png` | Verifies the impaired synthetic capture. |
| Matched-filter constellation | `docs/assets/end_to_end_bpsk_reference_constellation.png` | Shows the recovered BPSK symbols. |
| Matched-filter trace | `docs/assets/end_to_end_bpsk_reference_matched_filter.png` | Shows symbol-sampling alignment after the receiver filter. |
| Metrics JSON | `docs/assets/end_to_end_bpsk_reference_metrics.json` | Machine-readable BER/EVM/reference metrics. |
| Dataset manifest | `datasets/manifests/end_to_end_bpsk_reference_v1.yml` | Metadata and intended hardware route. |
| Shared package | `blocks/block_11_integrated_sdr_project/assets/end_to_end_bpsk_reference/` | Fixed-point and handoff exports for MATLAB, Simulink and HDL. |

## Fixed-point handoff

The Block 11 package exports the files that matter for the next two stages:

| File | Consumer |
|---|---|
| `tx_bits.txt` | MATLAB and HDL vector generation |
| `tx_symbols_q15.txt` | Symbol-mapper and stream-format reference |
| `rrc_taps_q15.txt` | Simulink fixed-point filter and future RTL pulse shaping |
| `sample_plan.json` | Reference symbol timing after matched filtering |
| `end_to_end_bpsk_reference_v1_tx_reference.ci16` | Offline replay and capture-reader validation |
| `end_to_end_bpsk_reference_v1.ci16` | Offline BER and spectrum checks |

## Current numerical target

The synthetic package is accepted when:

- the script exits with code `0`;
- `ber_payload` is zero or near zero;
- the Q1.15 exports are present and non-empty;
- the HDL symbol mapper testbench passes against vectors derived from the same frame bits;
- the manifest and metrics JSON are regenerated with a valid checksum.

## MATLAB and HDL anchor points

| Stage | File |
|---|---|
| MATLAB mirror | `blocks/block_11_integrated_sdr_project/matlab/end_to_end_bpsk_reference.m` |
| Python package generator | `blocks/block_11_integrated_sdr_project/python/end_to_end_bpsk_reference.py` |
| HDL mapper | `blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v` |
| HDL vectors | `blocks/block_05_fpga_hdl_flow/python/generate_bpsk_symbol_mapper_vectors.py` |
| HDL testbench | `blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_symbol_mapper.v` |

## Hardware promotion path

The recommended first measured route is:

```text
MATLAB BPSK burst -> Simulink fixed-point export -> Zynq TX -> Zynq RX -> BER
                                            \
                                             -> RTL-SDR monitor spectrum
```

This keeps BER on the controlled Zynq RX chain and uses RTL-SDR only as an external observer.
