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
python blocks/block_11_integrated_sdr_project/python/lab_11_20_read_rtl_wav_ota_bpsk_ber.py \
  --manifest datasets/lab11_20_rtl_sdr_ota_bpsk/manifest_live_20260624a.yaml
```

The WAV files are not in git (they are hundreds of megabytes). The manifest's `local_path_hint_windows` names the file the analyzer looks for; pass `--iq-path` to point at your own copy.

## Processing chain

```
WAV file (int16 I/Q) -> complex float, global DC removed
  -> coarse frequency candidates: spectrum peaks near the expected offset
  -> for each candidate: mix to baseband, resample to the reference rate,
     crop the active window, RRC matched filter
  -> fine-frequency grid x 16 sampling phases: correlate with the 25-bit preamble
  -> two scorings of the best frame:
       reference-aided: gain/phase fitted over the whole known frame,
                        candidate with the fewest bit errors kept
       receiver:        candidate with the highest normalised preamble correlation,
                        gain/phase from the preamble, decision-directed PLL,
                        BER on the 256 payload bits only
  -> plots and JSON metrics
```

The reference-aided numbers use the known payload, which no receiver has. They are an upper bound on link quality. The receiver scoring is what a real demodulator of this frame could achieve.

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

## Re-scored captures — 2026-09-24

Both 2026-06-24 captures whose WAVs are available locally, analysed with the current script:

| Capture | Reference-aided bit errors | Reference-aided EVM | Receiver bit errors (payload) | Receiver EVM |
|---|---:|---:|---:|---:|
| `manifest_live_20260624_stock_10cm_ref` | 0 / 281 | 10.60 % | 0 / 256 | 9.97 % |
| `manifest_live_20260624a` | 0 / 281 | 20.64 % | 0 / 256 | 9.47 % |

- **BER = 0 holds for a real receiver** on both captures (256 payload bits each, so the claim is only "below about 1 %", see the rule of three in [Lab 8.7](/zynq-sdr-course/en/labs/lab-8-7-snr-vs-ber-traps/)).
- **The reference-aided EVM can be worse than the receiver's.** On `20260624a` the selected frequency correction is exactly 2600.000 Hz, a point of the fine search grid. The small residual offset keeps rotating the constellation across the frame. One gain/phase coefficient for the whole frame cannot follow that rotation, so the EVM is 20.6 %; the PLL tracks it and gets 9.5 %. EVM measured without phase tracking includes the estimator's own error, not only the channel.

## Live result on 2026-06-23

This result is reference-aided and was not re-scored: its WAV is not available locally.

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
