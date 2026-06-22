# Lab 6.8 - Zynq stock-shell OTA DDS tone observation

## Goal

Transmit a short DDS-generated single tone from `TX1`, receive it on `RX1`
through a short over-the-air path, and save the result as a reproducible `CI16`
dataset that can be checked with the generic Block 9 offline analyzer.

This lab answers the practical question:

> Can the clean stock shell already support a safe, measured, host-driven RF transmit-and-receive proof before the full BPSK overlay is ready?

## Why this lab matters now

At the current stand stage:

- the course BPSK overlay still does not preserve a boot-safe AD9361 shell;
- the stock shell already exposes `ad9361-phy`, DDS and RX capture devices over network IIO;
- antennas are installed on `TX1` and `RX1`, separated by a few meters;
- no attenuators are currently available for a conducted loopback.

That makes a conservative OTA tone the correct next hardware step. It validates:

- stock-shell TX and RX control from the host;
- DDS tone generation through `cf-ad9361-dds-core-lpc`;
- short RF self-observation through the air path;
- `CI16` dataset generation and checksum tracking;
- offline frequency-plan validation through the Block 9 tooling.

## Executable files

| File | Purpose |
|---|---|
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py` | configure LO/gain/DDS, capture CI16 IQ, write manifest |
| `datasets/lab6_8_zynq_ota_tone_observation/manifest_tone_915MHz_700kHz_live_20260622.yaml` | first curated stock-shell OTA tone dataset |

## Live capture command

Run from the repository root:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py \
  --uri ip:192.168.40.1 \
  --center-frequency-hz 915000000 \
  --sample-rate-hz 3840000 \
  --rf-bandwidth-hz 2000000 \
  --tone-offset-hz 700000 \
  --tone-scale 0.25 \
  --rx-hardwaregain-db 30 \
  --tx-hardwaregain-db -40 \
  --sample-count 262144 \
  --out-iq datasets/lab6_8_zynq_ota_tone_observation/raw/zynq_ota_tone_915MHz_700kHz_live_20260622.ci16 \
  --manifest-out datasets/lab6_8_zynq_ota_tone_observation/manifest_tone_915MHz_700kHz_live_20260622.yaml
```

The capture script:

1. connects to the remote IIO context;
2. snapshots the current AD9361 RX/TX and DDS state;
3. applies a conservative OTA tone setup;
4. enables `TX1_I_F1` and `TX1_Q_F1` DDS tone channels in quadrature;
5. captures interleaved `CI16` I/Q samples from `cf-ad9361-lpc`;
6. restores the previous RF and DDS state;
7. writes the CI16 file and a manifest with checksum, settings and expected tone offset.

## Offline analysis

Analyze the recorded tone through the generic Block 9 reader:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py \
  --manifest datasets/lab6_8_zynq_ota_tone_observation/manifest_tone_915MHz_700kHz_live_20260622.yaml
```

This writes:

```text
docs/assets/lab92_lab6_8_zynq_ota_tone_915MHz_700kHz_live_20260622_spectrum.png
docs/assets/lab92_lab6_8_zynq_ota_tone_915MHz_700kHz_live_20260622_time_preview.png
docs/assets/lab6_8_zynq_ota_tone_915MHz_700kHz_live_20260622_metrics.json
```

## Measured live result

The repository includes a measured live run captured on `2026-06-22` with:

- `915 MHz` LO;
- `700 kHz` expected tone offset;
- `3.84 MS/s` sample rate;
- `2.0 MHz` RF bandwidth;
- manual `30 dB` RX gain;
- `-40 dB` TX attenuation;
- AGC disabled.

The offline analyzer reports:

- measured peak `700019.531 Hz`;
- frequency error `19.531 Hz`;
- estimated `SNR 39.32 dB`;
- `quality_pass = True`.

Lower-power attempts such as `TX -60 dB / RX 20 dB` still showed the tone near
the expected offset, but full-band edge spurs remained stronger than the wanted
line. The measured dataset stored here is the lowest radiated setting that made
the expected tone the dominant spectral line.

## Interpretation notes

- This is still a short-air-path sanity check, not a calibrated link-budget measurement.
- The dataset manifest constrains peak search to a `+-50 kHz` window around the expected tone. That keeps raw full-band edge spurs from hijacking the metric.
- The result is strong enough to validate LO plan, sample-rate interpretation and conservative TX/RX control before the BPSK modem handoff.

## Safety notes

- Keep AGC disabled while bringing up the first tone.
- Start from high attenuation and low RX gain, then increase only as needed.
- Do not treat this setup as a substitute for a proper attenuated conducted loopback.

## Report checklist

- [ ] State center frequency, tone offset, sample rate and RF bandwidth.
- [ ] Record RX gain, TX attenuation and antenna separation assumptions.
- [ ] Attach the tone manifest and checksum.
- [ ] Include the offline spectrum plot and time preview.
- [ ] Report measured tone offset, frequency error and SNR.
- [ ] State what this proves for the future BPSK hardware route.

## Engineering conclusion template

```text
The stock-shell AD9361 platform transmitted a DDS-generated tone at ____ MHz LO
with expected baseband offset ____ kHz and received it on RX1 over a short OTA
path. The capture used sample rate ____ MS/s, RF bandwidth ____ MHz, RX gain
____ dB and TX attenuation ____ dB. Offline CI16 analysis measured the tone at
____ kHz with frequency error ____ Hz, SNR ____ dB and checksum ______.
This means the stock-shell RF path is / is not ready for the first controlled
BPSK handoff because ______.
```
