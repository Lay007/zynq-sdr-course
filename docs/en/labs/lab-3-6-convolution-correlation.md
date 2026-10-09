# Lab 3.6 — Convolution and correlation for SDR

This lab separates two operations that are often confused in early DSP learning: convolution for filtering and correlation for detection. It is a deterministic script-driven lab, not a notebook workflow.

## Goal

Use one synthetic SDR-style signal to show two different engineering roles:

| Operation | SDR role | FPGA / implementation consequence |
|---|---|---|
| Convolution | FIR filtering, pulse shaping, channel response. | Multiply-accumulate structure, latency, coefficient quantization. |
| Correlation | Preamble detection, delay estimation, synchronization. | Sliding matched filter, accumulator width, threshold logic. |

## Run command

From the repository root:

```bash
python blocks/block_03_dsp_basics/python/lab_3_6_convolution_correlation.py
```

Or run it as part of the reproducibility suite:

```bash
python tools/run_all_labs.py
```

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `docs/assets/lab36_convolution_filtering.png` | Shows convolution as FIR filtering. |
| `docs/assets/lab36_correlation_detection.png` | Shows matched correlation peak for preamble detection. |
| `docs/assets/lab36_correlation_metrics.json` | Delay estimate, delay error and peak-to-median metric. |

## Engineering questions

1. Why is convolution the natural operation for FIR filtering?
2. Why is correlation the natural operation for preamble detection?
3. How does noise affect the correlation peak?
4. What accumulator width would be required in a fixed-point correlator?
5. How would you implement a sliding correlator in FPGA logic?

## What to expect

```text
Estimated delay: 512 samples
Delay error: 0 samples
Correlation peak/median: 40.00 dB
```

- A 64-symbol QPSK preamble is buried at sample 512 in a 2048-sample record, passed through a
  3-tap multipath channel, at 9 dB SNR, then low-pass filtered. The SNR is measured over the whole record; the preamble fills only 64 of the 2048 samples, so inside the preamble the SNR is about 24 dB. Correlating with the known preamble
  finds it **exactly**.
- **The peak stands 40 dB above the median correlation value.** A 64-symbol preamble gives a
  coherent gain of `10*log10(64) = 18 dB` in power over any single sample; the peak-to-median ratio
  is larger because the median of a noise-only correlation is well below its mean.
- The FIR is symmetric and applied with `mode="same"`, so it adds no delay. The channel is causal.
  Until September 2026 the channel was also applied with `mode="same"`, which moved the preamble one
  sample early and made the lab report 511: a reminder that the convolution mode is part of the
  model, not a plotting detail.

## Exercises

1. Lower the SNR from 9 dB to 0, −6 and −12 dB. At which SNR does the delay estimate start to
   fail, and how does the peak-to-median ratio behave just before that?
2. Shorten the preamble from 64 to 16 symbols. How many dB of peak-to-median do you lose? Compare
   with `10*log10(64/16)`.
3. Apply the FIR with `np.convolve(rx, h)` (full) instead of `mode="same"`. By how many samples does
   the estimate move, and why is it exactly `(len(h) - 1) / 2`?

<details markdown="1">
<summary>Answers (checked by running the lab script)</summary>

1. With the lab's noise model the estimate does not fail at 0, −6 or −12 dB: it stays at 512 samples while the peak-to-median ratio falls by about 3 dB per 3 dB of SNR (40.0 → 31.1 → 25.2 → 19.4 dB). Over 20 noise seeds it starts failing near −18 dB (15/20 correct) and is gone by −30 dB (0/20). The reason it survives so long is the SNR definition: it is measured over the whole 2048-sample record, but the preamble occupies only 64 samples, so the SNR inside the preamble is 15 dB higher than the label; add the 18 dB coherent gain of 64 symbols and −18 dB is still a positive margin.
2. Run as written, the 16-symbol preamble shows *more* peak-to-median (41.6 dB) than the 64-symbol one, because the lab scales the noise to the record's average power, which drops with a shorter preamble. With the noise power held fixed, 16 symbols give 36.3 dB against 40.2: a 3.9 dB loss, less than the `10·log10(64/16) = 6 dB` of coherent gain, because the median of the correlation is not the noise power.
3. The estimate moves from 512 to 532 samples: 20 = `(41 − 1)/2`. The full convolution of a symmetric 41-tap filter delays the signal by half its length; `mode="same"` crops that delay away.

</details>

## Report checklist

- Include both generated plots.
- Report the true and estimated delay.
- Report the delay error in samples.
- Report the correlation peak-to-median value.
- Explain how the FIR stage and matched correlator would map to RTL.

## Bridge to later blocks

This lab feeds directly into:

- Block 05: FIR and matched-filter RTL structures;
- Block 08: synchronization and preamble detection;
- Block 11: receiver-chain measurement reports.
