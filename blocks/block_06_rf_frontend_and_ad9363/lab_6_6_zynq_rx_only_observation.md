# Lab 6.6 - Zynq RX-only observation on the clean image

## Goal

Capture the first receive-only CI16 IQ artifact from the clean stock Pluto-like
image on the Zynq-7020 + AD9361 board and compare its FM-band spectrum with the
earlier RTL-SDR observation.

This lab answers the practical question:

> Can the cleaned-up board image already produce a reproducible host-side RX capture package before any TX work or attenuator-based loopback is available?

## Why this lab matters now

At the current stand stage:

- no attenuators are available yet;
- TX remains intentionally conservative under the course-clean overlay;
- antennas are connected to `RX1` on the Zynq board and to the independent RTL-SDR path.

That makes `RX-only` the correct next hardware step. It validates:

- clean image bring-up;
- network IIO access;
- AD9361 RX configuration from the host;
- CI16 dataset generation;
- offline replay through the Block 9 tooling;
- qualitative cross-receiver comparison on the same FM broadcast band.

## Executable files

| File | Purpose |
|---|---|
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_6_capture_zynq_rx_only.py` | configure RX, capture CI16 IQ, write manifest |
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_6_compare_receivers.py` | overlay Zynq and RTL-SDR FM spectra |
| `datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml` | first curated clean-image RX dataset |
| `datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454_live_20260622.yaml` | repeated live RX-only dataset captured on 2026-06-22 |

## Live capture command

Run from the repository root:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_6_capture_zynq_rx_only.py \
  --uri ip:192.168.40.1 \
  --center-frequency-hz 103119454 \
  --sample-rate-hz 2400000 \
  --rf-bandwidth-hz 2000000 \
  --gain-control-mode manual \
  --rx-hardwaregain-db 50 \
  --rf-port-select A_BALANCED \
  --sample-count 262144 \
  --out-iq datasets/lab6_6_zynq_rx_observation/raw/zynq_rx_fm_103119454Hz.ci16 \
  --manifest-out datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml
```

The capture script:

1. connects to the remote IIO context;
2. snapshots the current RX state;
3. applies a short receive-only FM observation setup;
4. captures interleaved CI16 I/Q samples from `cf-ad9361-lpc`;
5. restores the previous RX state;
6. writes the CI16 file and a dataset manifest with checksum and capture metadata.

## Offline analysis

Analyze the captured CI16 package through the generic Block 9 reader:

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py \
  --manifest datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml
```

This writes:

```text
docs/assets/lab92_lab6_6_zynq_rx_fm_103119454_spectrum.png
docs/assets/lab92_lab6_6_zynq_rx_fm_103119454_time_preview.png
docs/assets/lab6_6_zynq_rx_fm_103119454_metrics.json
```

## Cross-receiver comparison

Overlay the Zynq RX dataset and the existing RTL-SDR FM observation:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_6_compare_receivers.py \
  --zynq-manifest datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml \
  --rtl-manifest datasets/lab1_0_rtl_sdr_observation/manifest_fm_103119454.yaml
```

This writes:

```text
docs/assets/lab66_lab6_6_zynq_rx_fm_103119454_vs_lab1_0_rtl_sdr_fm_103119454_spectrum.png
docs/assets/lab66_lab6_6_zynq_rx_fm_103119454_vs_lab1_0_rtl_sdr_fm_103119454_metrics.json
```

## Latest measured rerun

The repository also keeps a repeated live rerun captured on `2026-06-22`:

```text
datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454_live_20260622.yaml
docs/assets/lab92_lab6_6_zynq_rx_fm_103119454_live_20260622_spectrum.png
docs/assets/lab92_lab6_6_zynq_rx_fm_103119454_live_20260622_time_preview.png
docs/assets/lab6_6_zynq_rx_fm_103119454_live_20260622_metrics.json
docs/assets/lab66_lab6_6_zynq_rx_fm_103119454_live_20260622_vs_lab1_0_rtl_sdr_fm_103119454_spectrum.png
docs/assets/lab66_lab6_6_zynq_rx_fm_103119454_live_20260622_vs_lab1_0_rtl_sdr_fm_103119454_metrics.json
```

That rerun used:

- `103.119454 MHz` center frequency;
- `2.4 MS/s` sample rate;
- `2.0 MHz` RF bandwidth;
- manual `45 dB` RX gain;
- passive `RX-only` OTA reception.

## What should be recorded

At minimum, keep:

- context URI and firmware/model strings from the clean image;
- center frequency, sample rate, RF bandwidth, gain mode and gain;
- RF port selection (`RX1` path assumptions);
- CI16 file checksum;
- FFT plot and time preview;
- one short comparison note against the RTL-SDR observation.

## Interpretation notes

- This is a receive-only baseline, not an absolute calibrated measurement.
- The overlay plot should be interpreted by spectral shape and occupancy, not by absolute amplitude.
- Wideband FM is not a narrow single-tone test, so peak-bin location is only a quick sanity check.
- The next engineering step after this lab is a controlled RX gain/overload table, not TX loopback.

## Report checklist

- [ ] State that TX remained in the safe course-clean default state.
- [ ] Attach the Zynq CI16 manifest.
- [ ] Record the exact RX gain mode and hardware gain.
- [ ] Include the offline spectrum plot from the CI16 reader.
- [ ] Include the receiver comparison overlay.
- [ ] State whether the Zynq clean-image RX path is ready for future Block 6/7 labs.

## Engineering conclusion template

```text
The clean-image Zynq board was observed in receive-only mode at ____ MHz with
sample rate ____ MS/s, RF bandwidth ____ MHz, gain mode ____ and RX gain ____ dB.
The capture was saved as CI16 with checksum ______ and replayed through the
Block 9 reader. Compared with the earlier RTL-SDR FM observation, the Zynq
capture does / does not show a consistent occupied FM-band shape because ______.
This means the clean-image RX path is / is not ready for the next hardware lab because ______.
```
