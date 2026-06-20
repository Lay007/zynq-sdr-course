# HDL latency contract

This page records the observable latency and throughput contract for the HDL blocks used in the course smoke tests.

The contract is intentionally separate from the Verilog source. It helps students and reviewers understand that valid/data timing is part of the interface, not an implementation detail hidden inside a testbench.

## Rules

- Latency is counted from the input `valid` sample accepted by the DUT to the corresponding output `valid` sample.
- Throughput describes the steady-state input rate after reset and pipeline fill.
- Testbenches must compare expected vectors after the documented latency, not by guessing a one-cycle delay.
- When an RTL pipeline is changed, this page and the matching testbench must be updated in the same change.

## Block 5 HDL contracts

| Module | Observable latency | Steady-state throughput | Testbench | Notes |
|---|---:|---:|---|---|
| `iq_passthrough` | 1 cycle | 1 complex sample / cycle | `tb_iq_passthrough.v` | Minimal registered streaming example. |
| `fir_iq_4tap` | 1 cycle | 1 complex sample / cycle | `tb_fir_iq_4tap.v` | Small direct-form FIR used for early RTL/model comparison. |
| `nco_mixer_iq` | 1 cycle | 1 complex sample / cycle | `tb_nco_mixer_iq.v` | DDS/mixer example with deterministic vectors. |
| `bpsk_symbol_mapper` | 1 cycle | 1 bit / cycle | `tb_bpsk_symbol_mapper.v` | Maps deterministic bits to Q1.15 BPSK symbols. |
| `bpsk_upsampler_8x` | 1 cycle | 1 input symbol / 8 output sample slots | `tb_bpsk_upsampler_8x.v` | Generates one non-zero symbol followed by seven zero-stuffing samples. |
| `bpsk_rrc_tx_fir` | 8 cycles | 1 complex sample / cycle | `tb_bpsk_rrc_tx_fir.v` | Registered symmetric-tap FIR reduction tree. |
| `bpsk_rrc_rx_fir` | 8 cycles | 1 complex sample / cycle | `tb_bpsk_rx_bit_recovery.v` | Thin matched-filter wrapper around the TX RRC FIR core. |
| `bpsk_symbol_timing_sampler` | 1 cycle from accepted matched-filter sample to sampled symbol | 1 selected symbol every `SPS` valid samples | `tb_bpsk_rx_bit_recovery.v` | Deterministic fixed-phase sampler used before full timing recovery labs. |
| `bpsk_hard_decision` | 1 cycle | 1 symbol / cycle | `tb_bpsk_rx_bit_recovery.v` | Real(sample) threshold detector. |
| `bpsk_framed_tx_chain` | frame dependent | streaming after start | `tb_bpsk_framed_loopback.v` | Includes bit source, mapper, upsampler and RRC filtering. |
| `bpsk_rx_bit_recovery_chain` | frame dependent | streaming after matched-filter fill | `tb_bpsk_framed_loopback.v` | Includes matched filter, timing sampler and hard decision. |
| `bpsk_zynq_ber_top` | frame dependent | one configured frame per `start` pulse | `tb_bpsk_zynq_ber_top.v` | Top-level BER path for Zynq integration. |
| `bpsk_zynq_ber_axi_lite` | software-polling dependent | one configured frame per AXI-Lite `start` pulse | `tb_bpsk_zynq_ber_axi_lite.v` | Register wrapper around the Zynq-ready BER top-level. |
| `axis_iq_passthrough` | 1 AXI-Stream transfer | 1 AXI-Stream beat / cycle when ready | `tb_axis_iq_passthrough.v` | AXI-Stream wrapper smoke check. |

## Review checklist

Before changing a pipelined HDL block, verify:

1. the testbench still models the real DUT latency;
2. the expected-vector generator has not encoded an outdated delay;
3. the smoke script still compiles and runs the affected testbench;
4. a failure message points to the module and timing relation clearly;
5. this contract remains synchronized with the RTL and lab text.
