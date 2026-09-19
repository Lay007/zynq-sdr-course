# Lab 5.5 - Float vs fixed-point vs RTL comparison

## Goal

Create a reproducible comparison of three implementation levels for one FIR block:

- floating-point reference model;
- fixed-point software model (Q1.15);
- RTL reference vectors from the educational Verilog testbench.

The lab answers a practical integration question:

> Is the fixed-point model numerically aligned with RTL, and what resource/latency trade-offs should be reported?

## Why this lab matters

When a design is split across three worlds — a float model that defines the
algorithm, a fixed-point model that predicts the hardware, and the RTL that *is* the
hardware — the single most valuable question is "do they agree, and if not, by how
much and why?". A mismatch you find here costs a minute; the same mismatch found on
the board costs a bitstream build and a debugging session. The comparison also
teaches what each model is *for*: the float model is the reference the fixed-point
model is judged against, and the fixed-point model is the reference the RTL is
judged against. Only the second comparison is expected to be exact.

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_05_fpga_hdl_flow/python/lab_5_5_float_fixed_rtl_comparison.py` | computes error metrics and resource/latency table |

Run from the repository root:

```bash
python blocks/block_05_fpga_hdl_flow/python/lab_5_5_float_fixed_rtl_comparison.py
```

## Generated artifacts

```text
docs/assets/lab55_float_fixed_rtl_error.png
docs/assets/lab55_float_fixed_rtl_resource_table.md
docs/assets/lab55_float_fixed_rtl_metrics.json
```

## Comparison outputs

| Output | Meaning |
|---|---|
| `RMSE float-RTL` | average mismatch between floating model and integer RTL vectors |
| `RMSE fixed-RTL` | average mismatch between Q1.15 model and RTL vectors |
| `MAX abs error` | worst-case mismatch in LSB units |
| resource/latency table | implementation-level trade-off summary for report |

## What to expect

The default run compares 8 valid output samples of the 4-tap IQ FIR:

```text
Compared valid samples: 8
RMSE float-RTL: 0.2778 LSB
RMSE fixed-RTL: 0.0000 LSB
MAX |float-RTL|: 0.3750 LSB
MAX |fixed-RTL|: 0.0000 LSB
Fixed exact match with RTL: True
```

Two different kinds of "agreement" appear here, and they should not be confused:

- **Fixed vs RTL is exact (0 LSB).** The fixed-point Python model and the Verilog
  implement the same integer arithmetic (Q1.15 products, the same rounding and
  saturation), so any nonzero difference would be a bug in one of them. This is a
  hard pass/fail check.
- **Float vs RTL differs by up to 0.375 LSB.** This is not an error: the float
  model does not round, so it differs from any integer implementation by
  quantization — less than one LSB here. This is a tolerance check
  (`pass_float_within_1_lsb`), not an equality check.

The resource/latency table is an *architecture-discussion estimate* (the script
states this explicitly), not a synthesis result; real numbers come from the Vivado
utilization and timing reports (see Block 5 report templates).

## Report checklist

- [ ] Include error figure and quote RMSE for float/fixed against RTL.
- [ ] State whether fixed-point exactly matches RTL vectors.
- [ ] Include resource/latency table in the report appendix.
- [ ] Explain why floating-point is used as algorithmic reference.

