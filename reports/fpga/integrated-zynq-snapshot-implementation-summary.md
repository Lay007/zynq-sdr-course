# Integrated Zynq implementation summary

This report is generated from the `vendor snapshot bridge_txrx_mux` flow after full Vivado synthesis, placement, routing and bitstream generation.

## Build context

| Field | Value |
|---|---|
| Tool | Vivado v.2021.1 (win64) Build 3247384 Thu Jun 10 19:36:33 MDT 2021 |
| Device | 7z020clg400-2 |
| Fully routed | True |
| Unrouted nets | 0 |
| Routing errors | 0 |
| Bitstream size | 2516200 bytes |
| Bitstream SHA256 | `753ced5676e1364c62a3c12c9006290368519803dda602bda64cee617ddf3428` |

## Utilization

| LUT | FF | DSP | BRAM tiles |
|---:|---:|---:|---:|
| 27887 | 36203 | 212 | 8.0 |

## Timing

| WNS, ns | TNS, ns | Failing endpoints | Total endpoints | Timing met |
|---:|---:|---:|---:|---|
| -1.676 | -53.405 | 66 | 105640 | False |

## Interpretation

This routed report applies only to the named build flow. Hardware compatibility, runtime clock activity and RF performance require separate board evidence.

Raw normalized reports are stored in `reports/fpga/integrated_zynq_snapshot_raw/`.
