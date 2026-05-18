# Lab 11.5 - AXI DMA pipeline latency and jitter

## Goal

Model packet-level throughput, latency, and jitter for a simplified Zynq runtime pipeline:

- DMA input stage;
- FPGA DSP stage;
- DMA output stage;
- finite queue depth and packet drops.

## Engineering question

> Can the pipeline sustain target packet rate with acceptable latency and jitter, and what queue depth is required?

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_5_axi_dma_latency_jitter.py` | latency/jitter simulation with finite buffers |

Run from the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_5_axi_dma_latency_jitter.py
```

## Generated artifacts

```text
docs/assets/lab115_axi_dma_latency_trace.png
docs/assets/lab115_axi_dma_latency_histogram.png
docs/assets/lab115_axi_dma_latency_metrics.json
```

## Key metrics

| Metric | Meaning |
|---|---|
| `drop_ratio` | dropped packets / offered packets |
| `mean_latency_us` | average end-to-end packet latency |
| `p95_latency_us`, `p99_latency_us` | tail latency indicators |
| `latency_jitter_std_us` | latency spread |
| `throughput_msample_per_s` | effective throughput |

## Report checklist

- [ ] State packet size and sample rate assumptions.
- [ ] Include latency trace and histogram.
- [ ] Report mean/p95/p99 latency.
- [ ] Report jitter and drop ratio.
- [ ] Provide queue-depth recommendation for target throughput.

