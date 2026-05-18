# Lab 5.5 - Float vs fixed-point vs RTL comparison

## Goal

Create a reproducible comparison of three implementation levels for one FIR block:

- floating-point reference model;
- fixed-point software model (Q1.15);
- RTL reference vectors from the educational Verilog testbench.

The lab answers a practical integration question:

> Is the fixed-point model numerically aligned with RTL, and what resource/latency trade-offs should be reported?

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

## Report checklist

- [ ] Include error figure and quote RMSE for float/fixed against RTL.
- [ ] State whether fixed-point exactly matches RTL vectors.
- [ ] Include resource/latency table in the report appendix.
- [ ] Explain why floating-point is used as algorithmic reference.

