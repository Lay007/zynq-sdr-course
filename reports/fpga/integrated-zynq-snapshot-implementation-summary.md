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
| Bitstream size | 2505900 bytes |
| Bitstream SHA256 | `973bb897010af1f5e3c31ccbd37b69e8e5ecf8abe624edea8e5a42954feb4e41` |

## Utilization

| LUT | FF | DSP | BRAM tiles |
|---:|---:|---:|---:|
| 27597 | 36169 | 216 | 8.0 |

## Timing

| WNS, ns | TNS, ns | Failing endpoints | Total endpoints | Timing met |
|---:|---:|---:|---:|---|
| 0.003 | 0.0 | 0 | 105709 | True |

## Interpretation

This routed report applies only to the named build flow. Hardware compatibility, runtime clock activity and RF performance require separate board evidence.

Raw normalized reports are stored in `reports/fpga/integrated_zynq_snapshot_raw/`.
