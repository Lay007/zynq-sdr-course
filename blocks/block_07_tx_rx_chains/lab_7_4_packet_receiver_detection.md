# Lab 7.4 - Packet receiver chain and frame detection

## Goal

Introduce a compact packet receiver flow:

- known preamble;
- AGC normalization;
- matched-filter frame detection;
- false-alarm and miss analysis.

## Engineering question

> How reliably can we detect packet starts and quantify misses/false detections before moving to full synchronization chains?

## Executable file

| File | Purpose |
|---|---|
| `blocks/block_07_tx_rx_chains/python/lab_7_4_packet_receiver_detection.py` | burst generation, detector, metrics |

Run from the repository root:

```bash
python blocks/block_07_tx_rx_chains/python/lab_7_4_packet_receiver_detection.py
```

## Generated artifacts

```text
docs/assets/lab74_packet_detection_metric.png
docs/assets/lab74_packet_detection_timeline.png
docs/assets/lab74_packet_receiver_metrics.json
```

## Key metrics

| Metric | Meaning |
|---|---|
| `true_positives` | packets detected within tolerance |
| `false_positives` | detections that do not map to a true packet |
| `misses` | true packets not detected |
| `detection_probability` | TP / true packet count |
| `false_alarm_rate` | FP / number of metric samples |
| timing error mean/std | synchronization quality for detected packets |

## Report checklist

- [ ] State preamble length, threshold, and tolerance.
- [ ] Include metric plot with threshold and detections.
- [ ] Include timeline plot with true vs detected starts.
- [ ] Report TP/FP/miss and detection probability.
- [ ] Explain threshold trade-off (miss rate vs false alarms).

