#!/usr/bin/env python3
"""Lab 11.5 - AXI DMA pipeline latency and jitter model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class PipelineConfig:
    packets: int = 800
    samples_per_packet: int = 4096
    sample_rate_hz: float = 2.4e6
    input_buffer_pkts: int = 10
    output_buffer_pkts: int = 10
    dma_in_mean_us: float = 135.0
    dma_in_jitter_us: float = 22.0
    fpga_proc_mean_us: float = 95.0
    fpga_proc_jitter_us: float = 14.0
    dma_out_mean_us: float = 145.0
    dma_out_jitter_us: float = 24.0
    seed: int = 115


@dataclass(frozen=True)
class PipelineMetrics:
    processed_packets: int
    dropped_packets: int
    drop_ratio: float
    mean_latency_us: float
    p95_latency_us: float
    p99_latency_us: float
    latency_jitter_std_us: float
    throughput_msample_per_s: float


def positive_gaussian(rng: np.random.Generator, mean_us: float, std_us: float) -> float:
    return float(max(rng.normal(mean_us, std_us), 1.0))


def main() -> None:
    cfg = PipelineConfig()
    rng = np.random.default_rng(cfg.seed)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    inter_arrival_us = cfg.samples_per_packet / cfg.sample_rate_hz * 1e6
    arrival_times = np.arange(cfg.packets, dtype=np.float64) * inter_arrival_us

    stage1_free = 0.0
    stage2_free = 0.0
    stage3_free = 0.0
    queue1: list[float] = []
    queue2: list[float] = []

    latencies: list[float] = []
    completion_times: list[float] = []
    dropped = 0

    for t_arr in arrival_times:
        queue1 = [x for x in queue1 if x > t_arr]
        queue2 = [x for x in queue2 if x > t_arr]

        if len(queue1) >= cfg.input_buffer_pkts:
            dropped += 1
            continue

        start1 = max(t_arr, stage1_free)
        dur1 = positive_gaussian(rng, cfg.dma_in_mean_us, cfg.dma_in_jitter_us)
        end1 = start1 + dur1
        stage1_free = end1
        queue1.append(end1)

        if len(queue2) >= cfg.output_buffer_pkts:
            dropped += 1
            continue

        start2 = max(end1, stage2_free)
        dur2 = positive_gaussian(rng, cfg.fpga_proc_mean_us, cfg.fpga_proc_jitter_us)
        end2 = start2 + dur2
        stage2_free = end2
        queue2.append(end2)

        start3 = max(end2, stage3_free)
        dur3 = positive_gaussian(rng, cfg.dma_out_mean_us, cfg.dma_out_jitter_us)
        end3 = start3 + dur3
        stage3_free = end3

        latencies.append(end3 - t_arr)
        completion_times.append(end3)

    processed = len(latencies)
    if processed == 0:
        raise RuntimeError("No packets processed in AXI DMA simulation.")

    lats = np.array(latencies, dtype=np.float64)
    duration_us = max(completion_times) - min(arrival_times)
    throughput = (processed * cfg.samples_per_packet) / max(duration_us, 1e-12)

    metrics = PipelineMetrics(
        processed_packets=processed,
        dropped_packets=dropped,
        drop_ratio=float(dropped / max(cfg.packets, 1)),
        mean_latency_us=float(np.mean(lats)),
        p95_latency_us=float(np.percentile(lats, 95)),
        p99_latency_us=float(np.percentile(lats, 99)),
        latency_jitter_std_us=float(np.std(lats)),
        throughput_msample_per_s=float(throughput),
    )

    trace_path = ASSET_DIR / "lab115_axi_dma_latency_trace.png"
    hist_path = ASSET_DIR / "lab115_axi_dma_latency_histogram.png"
    metrics_path = ASSET_DIR / "lab115_axi_dma_latency_metrics.json"

    plt.figure(figsize=(7.8, 4.4))
    plt.plot(lats, linewidth=1.0)
    plt.axhline(metrics.mean_latency_us, linestyle="--", color="tab:red", label="mean")
    plt.grid(True, alpha=0.35)
    plt.xlabel("Processed packet index")
    plt.ylabel("Latency, us")
    plt.title("Lab 11.5 - AXI DMA pipeline latency trace")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(trace_path, dpi=180)
    plt.close()

    plt.figure(figsize=(7.2, 4.2))
    plt.hist(lats, bins=30, alpha=0.8)
    plt.grid(True, alpha=0.35)
    plt.xlabel("Latency, us")
    plt.ylabel("Packet count")
    plt.title("Lab 11.5 - AXI DMA latency histogram")
    plt.tight_layout()
    plt.savefig(hist_path, dpi=180)
    plt.close()

    metrics_path.write_text(
        json.dumps(
            {
                "config": asdict(cfg),
                "metrics": asdict(metrics),
                "inter_arrival_us": inter_arrival_us,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 11.5 - AXI DMA pipeline latency and jitter")
    print(f"Processed/dropped packets: {metrics.processed_packets}/{metrics.dropped_packets}")
    print(f"Drop ratio: {metrics.drop_ratio:.4f}")
    print(
        "Latency mean/p95/p99 (us): "
        f"{metrics.mean_latency_us:.2f}/{metrics.p95_latency_us:.2f}/{metrics.p99_latency_us:.2f}"
    )
    print(f"Latency jitter std (us): {metrics.latency_jitter_std_us:.2f}")
    print(f"Throughput (Msample/s): {metrics.throughput_msample_per_s:.3f}")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
