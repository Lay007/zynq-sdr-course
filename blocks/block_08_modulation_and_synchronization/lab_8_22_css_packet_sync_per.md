# Lab 8.22 — Packet-level CSS synchronization and PER

## Goal

Extend the signal-level CSS detector from Labs 8.20/8.21 into a deterministic packet receiver:

- detect a repeated-upchirp preamble and estimate packet start;
- verify a two-symbol sync word and two downchirps;
- estimate coarse integer-bin and fine fractional-bin CFO;
- correct CFO before payload decisions;
- measure SER, PER, missed detections and false alarms;
- expose sample-rate-offset sensitivity.

The waveform remains **CSS/LoRa-like**, not LoRa-compatible. It deliberately omits the LoRa header, whitening, coding, interleaving and CRC.

## Packet structure

```text
noise prefix | 8 upchirps | sync symbols 18,52 | 2 downchirps |
16 payload symbols | noise suffix
```

The packet-start metric dechirps each candidate preamble window, accumulates FFT-bin power over all repeated chirps and compares the strongest bin with the mean bin power. The sync word and downchirps reject a high timing metric that does not have the expected packet structure.

## CFO estimation

The preamble FFT peak supplies the integer-bin CFO. Phase advance of that peak across consecutive repeated chirps supplies the fractional-bin CFO:

```text
CFO = integer FFT-bin shift + phase_step / (2π)
```

The default experiment injects `1.25` bin spacings. Without correction every payload packet fails; after synchronization and correction the reference `-6 dB` point reaches zero PER for the deterministic seed.

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_22_css_packet_sync_per.py
```

## Generated artifacts

```text
docs/assets/lab822_css_timing_metric.png
docs/assets/lab822_css_per_vs_snr.png
docs/assets/lab822_css_sro_sensitivity.png
docs/assets/lab822_css_packet_metrics.json
```

## Statistical scope

- 1000 packets at every SNR point;
- 16,000 compared payload symbols per SNR point;
- 1000 independent noise-only false-alarm trials;
- 200 packets per sample-rate-offset point.

The zero-error points are finite tests, not proof of an arbitrarily low PER. With 1000 clean packets, the usual zero-failure 95% upper bound is approximately `3/1000`.

## Acceptance criteria

- the example packet start, sync word and downchirps are recovered;
- normalized CFO error is below `0.05` bin;
- corrected PER is lower than uncorrected PER at the reference point;
- at least 1000 packets are evaluated per SNR point;
- missed-detection and false-alarm statistics are present;
- the SRO sweep shows both degradation and the benefit/limit of resampling correction.

## What to expect

Packet results against SNR (1000 packets per point, 1.25-bin CFO injected):

| SNR | Missed detection | PER uncorrected | PER corrected | SER corrected |
|---:|---:|---:|---:|---:|
| −15 dB | 0.948 | 1.0 | 1.0 | 0.609 |
| −12 dB | 0.419 | 1.0 | 0.93 | 0.139 |
| −9 dB | 0.013 | 1.0 | 0.045 | 0.004 |
| −6 dB | 0 | 1.0 | 0 | 0 |
| −3 dB | 0 | 1.0 | 0 | 0 |

Sample-rate offset (200 packets per point): up to 100 ppm nothing fails; at 250 ppm every uncorrected
packet fails and correction recovers all of them; at 500 ppm even the corrected receiver loses 20 %
of packets. No false alarms in 1000 noise-only trials.

- **Without CFO correction nothing gets through at any SNR**: a 1.25-bin offset shifts every symbol
  by one bin plus a quarter, which is exactly the failure Lab 8.21 predicts.
- **Missed detection dominates below −9 dB.** The packet is lost before the payload detector sees
  it, so PER rises faster than SER.

## Exercises

1. What is the 95 % upper bound on PER at −6 dB given 0 failures in 1000 packets? What would you
   need to claim PER below 1e-4?
2. Convert 250 ppm of sample-rate offset into how far a 16-symbol payload drifts, in samples, by its
   last symbol. Why does even the corrected receiver start losing packets at 500 ppm?
