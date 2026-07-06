# Integrated Zynq implementation summary

This report is generated from the current dual-modem course overlay after full Vivado synthesis, placement, routing and bitstream generation.

## Build context

| Field | Value |
|---|---|
| Tool | Vivado v.2021.1 (win64) Build 3247384 Thu Jun 10 19:36:33 MDT 2021 |
| Device | 7z020clg400-2 |
| Fully routed | True |
| Unrouted nets | 0 |
| Routing errors | 0 |
| Bitstream size | 2118912 bytes |
| Bitstream SHA256 | `5e46cf4e23b5485aef759822a8deef541383ed8eba5171d24728a36f9cdd1b8d` |

## Utilization

| LUT | FF | DSP | BRAM tiles |
|---:|---:|---:|---:|
| 13795 | 21780 | 28 | 4.0 |

## Timing

| WNS, ns | TNS, ns | Failing endpoints | Total endpoints | Timing met |
|---:|---:|---:|---:|---|
| 0.354 | 0.0 | 0 | 48851 | True |

## Interpretation

The routed report proves implementation feasibility for the exact integrated PL design. It does not prove AD9361 calibration, RF performance or clean-boot repeatability; those remain board-level gates.

Raw normalized reports are stored in `reports/fpga/integrated_zynq_raw/`.
