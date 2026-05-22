# CIC, fixed-point and FPGA bridge

This page explains why CIC filters are a key bridge between multirate DSP theory and FPGA implementation. It is not a notebook track; it is an engineering roadmap for deterministic scripts, fixed-point analysis, generated figures, RTL mapping and measurement reports.

## Why CIC belongs in this course

CIC filters are especially useful in SDR receiver and transmitter chains because they perform high-rate decimation or interpolation using only integrators, comb sections, delays, additions and subtractions. That makes them attractive for FPGA implementation where multiplier resources are limited or should be reserved for later FIR stages.

Typical SDR placement:

```text
ADC / RF frontend -> CIC decimator -> compensation FIR -> channel filter -> demodulator
```

or for a transmitter:

```text
modulator -> pulse shaping -> interpolation FIR -> CIC interpolator -> DAC / RF frontend
```

## CIC structure

A decimating CIC filter consists of:

1. `N` cascaded integrators running at the high input sample rate;
2. rate change by factor `R`;
3. `N` cascaded comb sections running at the lower output sample rate;
4. differential delay `M` in the comb section.

The basic parameters are:

| Symbol | Meaning |
|---|---|
| `R` | Decimation or interpolation factor. |
| `N` | Number of CIC stages. |
| `M` | Differential delay. |
| `B_in` | Input word length. |
| `B_acc` | Required internal accumulator width. |

## Bit-growth rule

The maximum CIC gain is:

```text
G = (R * M)^N
```

The conservative bit-growth estimate is:

```text
growth_bits = ceil(N * log2(R * M))
B_acc = B_in + growth_bits
```

This is the first fixed-point checkpoint. A CIC lab is not complete unless it states the accumulator width and explains where overflow can occur.

## Passband droop

CIC filters are efficient but not flat in the passband. This matters in SDR because a receiver chain may preserve amplitude information for EVM, SNR, BER or calibration.

Engineering options:

| Option | Use when |
|---|---|
| Accept droop | Narrow signal bandwidth and loose amplitude requirements. |
| Add compensation FIR | Wider passband or measurement-grade amplitude response. |
| Split decimation stages | Large rate changes need better alias and passband control. |
| Use FIR-only decimation | Lower rates or when multiplier cost is acceptable. |

## FPGA implementation checklist

| Item | Required decision |
|---|---|
| Input format | Signed integer width, binary point and scaling. |
| Integrator width | Must include CIC bit growth. |
| Comb width | Usually same as integrator or explicitly rounded. |
| Saturation / wrap | Must be intentional and documented. |
| Decimation strobe | Defines when comb stages update. |
| Reset behavior | Integrators must have deterministic reset. |
| Latency | Needed for downstream synchronization. |
| Compensation FIR | Required if passband droop is unacceptable. |

## Lab 7.5 role

The executable lab `blocks/block_07_tx_rx_chains/python/lab_7_5_cic_decimator.py` provides the first deterministic course artifact for this bridge.

It generates:

```text
docs/assets/lab75_cic_response.png
docs/assets/lab75_cic_decimation_spectrum.png
docs/assets/lab75_cic_bit_growth.png
docs/assets/lab75_cic_metrics.json
```

The generated metrics include:

- input and output sample rates;
- decimation factor;
- CIC stage count;
- differential delay;
- theoretical bit growth;
- recommended accumulator width;
- passband droop at the wanted tone;
- measured output peak frequency;
- blocker alias frequency after decimation.

## Path to RTL

The next implementation step is an RTL lab:

```text
Python CIC model -> fixed-point vectors -> Verilog CIC decimator -> testbench -> model vs RTL comparison
```

Suggested future files:

```text
blocks/block_05_fpga_hdl_flow/rtl/cic_decimator.v
blocks/block_05_fpga_hdl_flow/tb/tb_cic_decimator.v
blocks/block_05_fpga_hdl_flow/python/generate_cic_vectors.py
docs/assets/lab55_cic_model_vs_rtl.png
```

## Acceptance criteria

A CIC implementation is ready for hardware-facing SDR labs when:

- bit growth is calculated;
- overflow behavior is documented;
- passband droop is measured;
- alias behavior after decimation is visible;
- fixed-point test vectors exist;
- RTL output is compared against the model;
- the implementation has reset, valid/enable and latency notes.
