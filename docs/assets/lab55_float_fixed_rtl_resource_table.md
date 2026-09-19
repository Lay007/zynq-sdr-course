# Lab 5.5 resource and latency comparison

| Implementation | Numerical model | Typical FPGA resources* | Latency (cycles) | Notes |
|---|---|---|---:|---|
| Python float | float64 reference | N/A (software) | N/A | best analytical reference |
| Python fixed-point | Q1.15 emulation | N/A (software) | N/A | mirrors hardware quantization |
| RTL FIR 4-tap | Q1.15 integer MAC | ~4 multipliers, ~3 adders, registers | 1-2 | synthesizable datapath |

*Resource row is an educational estimate for architecture discussion.
