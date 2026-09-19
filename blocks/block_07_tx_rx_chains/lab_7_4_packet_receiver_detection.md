# Lab 7.4 - Packet receiver chain and frame detection

## Goal

Introduce a compact packet receiver flow:

- known preamble;
- AGC normalization;
- matched-filter frame detection;
- false-alarm and miss analysis.

## Why this lab matters

A receiver that is always running has to answer, on every sample, a question that a
loopback simulation never asks: *is there a packet starting here at all?* Answer too
eagerly and noise triggers false detections that waste the decoder and corrupt
statistics; answer too cautiously and you miss real packets. The standard tool is a
**matched filter against a known preamble**, normalised so that the score does not
depend on the (unknown, varying) signal amplitude — that is what the AGC step and the
energy normalisation in `detection_metric()` are for. The peak *position* then
doubles as the coarse frame timing that every later synchronisation stage (Block 8)
starts from, so a detector that fires in roughly the right place is not good enough.

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

## What to expect

With the defaults (12 packets, 64-symbol BPSK preamble at 4 samples/symbol, random
packet amplitudes 0.55–1.25, noise 0.22 rms, threshold 0.20, tolerance 16 samples):

```text
True packets: 12
Detected candidates: 12
TP / FP / Miss: 12 / 0 / 0
Detection probability / miss rate / false alarm rate: 1.000 / 0.000 / 0.000000
Timing error mean/std (samples): 0.00 / 0.00
```

Things worth checking in the plots:

- **The metric peaks at about 0.9 at every true start** and stays at a noise floor
  around 0.05 (rarely above 0.18) in the gaps and inside payloads. The normalised
  score is `|<x, preamble>| / (|preamble|·|x|)`, so it is close to 1 only when the
  received window really looks like the preamble, regardless of how loud the packet is.
- **The timing error is exactly zero here** because the model is synthetic, sample-
  aligned and has no carrier offset or unknown delay fraction. Do not expect this on
  real captures; a real detector's peak location is uncertain by a fraction of a symbol
  and is refined by the timing loops of Block 8.
- **The tolerance (16 samples = 4 symbols) is part of the definition of "detected".**
  A detection that lands 100 samples from the true start is *not* a synchronised
  packet, even though something crossed the threshold; always state the tolerance next
  to the detection probability.

## Exercises

1. Sweep the threshold from 0.10 to 0.70 in steps of 0.05. At which threshold does the
   first false alarm disappear, and how much margin is there between it and the
   weakest true peak? (With the defaults, 0.10 and 0.15 give one false alarm, 0.20 and
   above give none.) Why is a threshold just above the noise floor fragile?
2. Raise `noise_rms` to 0.5 and then 1.0. When does the detection probability start to
   fall, and does the miss or the false alarm appear first?
3. Halve `preamble_symbols` to 32. How does the gap between true peaks and the noise
   floor change, and what does that say about why real packets use long preambles?
4. Multiply the received stream by `exp(j·2π·f·n/fs)` for `f` = 200, 1000, 2000 and
   5000 Hz. Compute the phase the offset accumulates over the 256-sample preamble
   (`2π·f·256/fs`), then compare with the detector: the mean true peak falls from about
   0.91 to 0.83, 0.57 and 0.19, and at 5 kHz every packet is missed. Why does the
   matched filter tolerate a fraction of a radian but collapse once the phase wraps
   around, and what would a CFO-tolerant detector do differently? (This is the
   motivation for the CFO estimators of Block 8.)

## Report checklist

- [ ] State preamble length, threshold, and tolerance.
- [ ] Include metric plot with threshold and detections.
- [ ] Include timeline plot with true vs detected starts.
- [ ] Report TP/FP/miss and detection probability.
- [ ] Explain threshold trade-off (miss rate vs false alarms).

