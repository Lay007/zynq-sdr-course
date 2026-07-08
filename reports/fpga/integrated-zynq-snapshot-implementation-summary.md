# Integrated Zynq implementation summary

This report is generated from the `vendor snapshot bridge_txrx_mux / Performance_ExtraTimingOpt` flow after full Vivado synthesis, placement, routing and bitstream generation.

## Build context

| Field | Value |
|---|---|
| Tool | Vivado v.2021.1 (win64) Build 3247384 Thu Jun 10 19:36:33 MDT 2021 |
| Device | 7z020clg400-2 |
| Fully routed | True |
| Unrouted nets | 0 |
| Routing errors | 0 |
| Bitstream size | 2519848 bytes |
| Bitstream SHA256 | `50ae27c0cca1fde8621d8a405cdee53dc5d25b5c5fb1dc47e6c1a8d7faac0bb7` |

## Utilization

| LUT | FF | DSP | BRAM tiles |
|---:|---:|---:|---:|
| 27649 | 36224 | 216 | 8.0 |

## Timing

| WNS, ns | TNS, ns | Failing endpoints | Total endpoints | Timing met |
|---:|---:|---:|---:|---|
| 0.096 | 0.0 | 0 | 105870 | True |

## Interpretation

This routed report applies only to the named build flow. Hardware compatibility, runtime clock activity and RF performance require separate board evidence.

Raw normalized reports are stored in `reports/fpga/integrated_zynq_snapshot_raw/`.
