# Lab 6.8 Zynq OTA Tone Observation

This folder stores the first short over-the-air `CI16` IQ capture where the
stock `Zynq-7020 + AD9361` shell transmits a DDS-generated tone from `TX1` and
receives it on `RX1` through separate antennas.

The raw file is stored through `Git LFS`, while the manifest keeps the checksum,
RF settings and replay command.

## Files

| File | Role |
|---|---|
| `manifest_tone_915MHz_700kHz_live_20260622.yaml` | Curated live stock-shell OTA tone manifest |
| `raw/*.ci16` | Short interleaved signed-int16 I/Q recording stored through Git LFS |

## Capture

Run from the repository root:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py \
  --uri ip:192.168.40.1
```

## Offline analysis

```bash
python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py \
  --manifest datasets/lab6_8_zynq_ota_tone_observation/manifest_tone_915MHz_700kHz_live_20260622.yaml
```

## Notes

- The measured live capture uses `915 MHz` LO, `700 kHz` tone offset, `3.84 MS/s`,
  `2 MHz` RF bandwidth, manual `30 dB` RX gain and `-40 dB` TX attenuation.
- The manifest constrains peak search to a narrow window around the expected tone
  so raw full-band edge spurs do not hide the wanted signal.
- Review the legal/publication status of the real RF capture before pushing to a
  public remote.
