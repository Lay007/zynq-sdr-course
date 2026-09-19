# Lab 11.5 - AXI DMA pipeline latency and jitter

## Goal

Model packet-level throughput, latency, and jitter for a simplified Zynq runtime pipeline:

- DMA input stage;
- FPGA DSP stage;
- DMA output stage;
- finite queue depth and packet drops.

## Why this lab matters

A DSP block that is correct on paper can still fail in a running system because the data does not
arrive in time. Packets move through DMA in, the FPGA stage and DMA out; each stage takes a
variable time, and each hand-off has a finite queue. If the slowest stage cannot keep up with
the arrival rate the queues fill and packets are dropped; if it can, the price is latency and
jitter. This lab turns that into numbers so queue depth and packet size are chosen, not guessed.

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

## What to expect

With the default model (800 packets of 4096 samples at 2.4 MS/s, so one packet every 1706.7
microseconds; stage means 135 / 95 / 145 microseconds with 22 / 14 / 24 microsecond jitter;
10-packet queues) a correct run prints:

```text
Processed/dropped packets: 800/0
Drop ratio: 0.0000
Latency mean/p95/p99 (us): 373.55/430.19/453.33
Latency jitter std (us): 33.81
Throughput (Msample/s): 2.402
```

How to read it:

- **Mean latency 373.6 microseconds is essentially the sum of the three stage means**
  (135 + 95 + 145 = 375): with no queueing, a packet just walks through the stages.
- **p99 is 453 microseconds, 80 microseconds above the mean.** The report quotes tail
  latency because a real-time deadline is set by the worst packets, not the average.
- **Zero drops here is not a discovery, it is headroom.** Even the slowest stage (145
  microseconds) needs only about 8.5 % of the 1706.7 microsecond packet period, so the queues never
  fill and their depth (10) is far more than needed. The interesting operating region is much
  faster or much slower than this default; see the exercises.
- **Throughput 2.402 MS/s equals the offered rate**, as it must when nothing is dropped.

## Exercises

1. The slowest stage takes 145 microseconds. At what sample rate does the packet period fall to
   145 microseconds? Predict the drop ratio just above that rate, edit `sample_rate_hz`, and check.
2. At a rate where the pipeline is close to saturation, reduce both queue depths from 10 to 1 and
   then to 2. How do drops and p99 latency change, and why does queue depth not help a
   pipeline that is truly overloaded?
3. Halve `samples_per_packet`. Latency per packet falls, but per-packet overhead now matters
   more; sketch how you would decide the packet size for your own design.

## Report checklist

- [ ] State packet size and sample rate assumptions.
- [ ] Include latency trace and histogram.
- [ ] Report mean/p95/p99 latency.
- [ ] Report jitter and drop ratio.
- [ ] Provide queue-depth recommendation for target throughput.

