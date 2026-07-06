# Lab 11.20 - Read RTL-SDR WAV IQ, demodulate OTA BPSK, and measure BER

## Objective

Offline-process a WAV IQ recording made by an RTL-SDR acting as a passive RF
monitor, demodulate the BPSK burst captured from the ZynqSDR TX antenna, and
report BER and EVM against the known course reference bit sequence.

This lab is the offline analysis counterpart to the live-capture labs
(11.21–11.22). It takes a WAV file path (plus an optional YAML manifest) and
produces a self-contained BER/EVM evidence package without any hardware present.

## Context

The RTL-SDR external monitor approach was adopted because:

- the PL RX path of the ZynqSDR is still stalled at `rx_valid_count = 0`;
- RTL-SDR can receive the ZynqSDR TX signal over the air independently;
- a WAV recording made during Lab 11.21 or 11.22 can be replayed offline any
  number of times with different demodulator parameters.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_20_read_rtl_wav_ota_bpsk_ber.py` | load WAV, normalize IQ, detect BPSK frame, compute BER/EVM |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_20_read_rtl_wav_ota_bpsk_ber.py \
  --wav-path datasets/lab11_21_rtl_monitor/capture_live_20260623.wav \
  --manifest-path datasets/lab11_21_rtl_monitor/manifest_live_20260623.yaml \
  --run-tag rtl_ota_bpsk_ber_live
```

## Processing chain

```
WAV file (int16 I/Q interleaved)
  → normalize to complex float
  → frequency-shift to baseband (if center offset in manifest)
  → matched filter (RRC, 16 sps)
  → timing recovery (Gardner or threshold peak)
  → differential or coherent BPSK decision
  → frame search (preamble correlation)
  → BER and EVM against reference bits
  → plots and JSON metrics
```

## WAV format expected

The WAV must be 16-bit stereo (left = I, right = Q) or 16-bit mono with
interleaved I/Q as produced by the RTL-SDR capture helper (Lab 11.21 / 11.22).

```text
sample_rate = WAV header rate (e.g. 3 840 000 or 2 400 000)
samples     = 16-bit signed integer
layout      = I[0] Q[0] I[1] Q[1] ...
```

## Expected outputs

| File | Content |
|---|---|
| `docs/assets/lab1120_<tag>_spectrum.png` | RX baseband spectrum |
| `docs/assets/lab1120_<tag>_constellation.png` | symbol constellation |
| `docs/assets/lab1120_<tag>_ber_metrics.json` | BER, EVM, sample count, timing offset |

## Success criteria

| Metric | Target |
|---|---|
| BER total | ≤ 1 % (or 0 for clean OTA) |
| EVM | record and compare against the matched baseline; no universal pass threshold is used until amplitude/timing normalization is calibrated |
| Frame detected | yes |

## Live result on 2026-06-23

Applied to a WAV recording captured during the stock-shell BPSK OTA run
(Lab 11.21), the offline demodulator detected the preamble, recovered
281 payload bits, and measured BER = 0 / EVM ≈ 55 %. This passes the bit-recovery
gate, while the high EVM remains a diagnostic result rather than a modulation-quality
pass. It matches the on-board AD9361 baseline from Lab 11.14 (EVM = 54.98 %), so
future captures should be compared against that baseline until normalization is revised.

## Report checklist

- [ ] State WAV file source (which lab captured it).
- [ ] State WAV sample rate and center frequency from manifest.
- [ ] Attach constellation plot.
- [ ] Record BER and EVM.
- [ ] State whether the frame was detected and how many payload bits were recovered.

## Engineering conclusion template

```text
The RTL-SDR WAV recording from ____ at ____ MHz (Fs = ____ MS/s) was offline-
demodulated. Frame detection: ____. Payload bits recovered: ____. BER = ____.
EVM = ____ %. The OTA BPSK link is / is not confirmed viable because ______.
```
