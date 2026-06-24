# Lab 11.21 - Capture RTL-SDR monitor WAV during stock-shell ZynqSDR BPSK TX

## Objective

Use an RTL-SDR dongle as an independent RF monitor to record the ZynqSDR BPSK
transmit burst over the air, while the ZynqSDR operates in stock-shell mode
(Lab 11.14 configuration). The resulting WAV file is the primary input to the
offline BER analysis in Lab 11.20.

## Why an external monitor

The ZynqSDR's own PL RX path is stalled at `rx_valid_count = 0` under the
runtime overlay. The RTL-SDR provides a completely independent receive chain
that is not affected by the course FPGA overlay state, so it can confirm whether
the ZynqSDR TX signal is actually radiated — independently of any PL RX issue.

## Hardware setup

```
ZynqSDR TX1 antenna  ─── (air gap, ~1–5 m) ───  RTL-SDR antenna
                                                    │
                                                 USB 2.0
                                                    │
                                                 Host PC
                                               (rtl_sdr / SoapySDR)
```

- ZynqSDR center frequency: **915 MHz**, TX attenuation: **-50 dB**.
- RTL-SDR tuned to the same center frequency with 10–20 dB tuner gain.
- Antennas must be in the same room; no attenuators needed for this short path.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_11_integrated_sdr_project/python/lab_11_21_capture_rtl_sdr_monitor_wav.py` | start stock-shell BPSK TX, simultaneously capture RTL-SDR WAV, save manifest |

## Run

```bash
python blocks/block_11_integrated_sdr_project/python/\
lab_11_21_capture_rtl_sdr_monitor_wav.py \
  --center-frequency-hz 915000000 \
  --sample-rate-hz 2400000 \
  --tuner-gain-db10 200 \
  --capture-duration-s 5.0 \
  --wav-out datasets/lab11_21_rtl_monitor/capture_live.wav \
  --manifest-out datasets/lab11_21_rtl_monitor/manifest_live.yaml \
  --run-tag stock_bpsk_rtl_monitor
```

The script:

1. configures the stock AD9361 TX path over SSH (same settings as Lab 11.14);
2. starts a cyclic BPSK burst from the stock host TX DMA;
3. simultaneously opens the RTL-SDR device and records raw I/Q to a WAV file;
4. stops TX after `--capture-duration-s` seconds;
5. restores the AD9361 to its safe state;
6. saves the WAV file and a YAML manifest with all capture metadata.

## WAV output format

```text
codec:       PCM 16-bit signed integer
channels:    2  (left = I, right = Q)
sample rate: --sample-rate-hz value (written into WAV header)
endianness:  little
```

The WAV can be loaded directly by Lab 11.20 without any conversion.

## Key parameters

| Parameter | Default | Notes |
|---|---|---|
| `--center-frequency-hz` | 915 000 000 | Must match ZynqSDR TX LO |
| `--sample-rate-hz` | 2 400 000 | RTL-SDR hardware rate; must be ≥ 2× signal BW |
| `--tuner-gain-db10` | 200 (= 20.0 dB) | Increase if signal is weak |
| `--capture-duration-s` | 5.0 | Must be long enough to capture full burst |

## Live result on 2026-06-23

The RTL-SDR captured a 5-second WAV at 2.4 MS/s while the stock-shell BPSK
cyclic burst was active. Offline analysis (Lab 11.20) on that WAV found the
preamble, recovered 281 bits, and measured BER = 0 / EVM ≈ 55 %. The capture
confirms that the ZynqSDR TX1 path radiates a detectable, demodulable BPSK
signal at 915 MHz.

## Report checklist

- [ ] Confirm RTL-SDR device index and driver (rtlsdr / SoapySDR).
- [ ] Record tuner gain and actual AGC setting.
- [ ] State ZynqSDR TX attenuation and sample rate.
- [ ] Attach the YAML manifest.
- [ ] Cross-reference with Lab 11.20 offline BER result.

## Engineering conclusion template

```text
The RTL-SDR monitor captured ____ seconds of WAV at ____ MS/s while the
ZynqSDR stock-shell BPSK TX was active at ____ MHz with TX attenuation ____ dB.
The WAV contains a detectable / undetectable BPSK burst because ____.
Offline Lab 11.20 BER result: ____. OTA TX viability: confirmed / not confirmed.
```
