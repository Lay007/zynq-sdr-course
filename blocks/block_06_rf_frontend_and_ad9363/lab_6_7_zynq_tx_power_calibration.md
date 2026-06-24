# Lab 6.7 - Zynq TX power calibration and attenuator table

## Goal

Build a reproducible TX attenuation versus received power table for the
ZynqSDR + AD9363 platform, using the RTL-SDR as a calibrated (relative)
power reference.

This lab sits between the RX-only baseline (Lab 6.6) and the first full
over-the-air DDS tone observation (Lab 6.8). Its purpose is to establish a
safe TX attenuation range before committing to OTA experiments, so that
subsequent labs can choose attenuation settings with a known link budget.

## Why this lab

At the current stage:

- Lab 6.6 confirmed the ZynqSDR RX path is healthy;
- no RF attenuators are available for a conducted loopback;
- TX experiments require a known safe starting point before enabling the
  AD9363 PA;
- the RTL-SDR already exists as an independent receiver with a stable
  `tuner_gain_db10` setting.

The relative power table produced here lets later labs (6.8, 7.x, 11.x)
set TX attenuation to a point within the RTL-SDR dynamic range without
risking overload.

## Executable files

| File | Purpose |
|---|---|
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py` | confirm IIO device list before enabling TX |
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py` | used in sweep mode with `--tx-attenuation-db` argument |

No dedicated `lab_6_7_*.py` script is required: the sweep reuses `lab_6_8`
with a fixed DDS tone and varied TX attenuation.

## Measurement procedure

1. Confirm ZynqSDR IIO context is reachable:

   ```bash
   python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py \
     --uri ip:192.168.40.1
   ```

2. Set up the RTL-SDR at a fixed gain (e.g., tuner gain = 200 / 20 dB) and
   tune to the DDS tone frequency (center + offset).

3. For each TX attenuation value in the table below, run:

   ```bash
   python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py \
     --uri ip:192.168.40.1 \
     --center-frequency-hz 915000000 \
     --tx-attenuation-db <VALUE> \
     --tone-offset-hz 50000 \
     --capture-duration-s 2.0 \
     --run-tag tx_cal_<VALUE>dB
   ```

4. Read the RTL-SDR FFT peak for each run and record the received power.

## Suggested attenuation sweep

| TX attenuation (dB) | Expected RTL-SDR SNR | Notes |
|---|---|---|
| -89.75 (min TX) | noise floor | safe baseline — no signal expected |
| -60 | low | start here |
| -50 | moderate | standard course default |
| -40 | good | increase only with antenna separation > 2 m |
| -30 | high | check RTL-SDR for overload symptoms |

## Safety rules

- Never set TX attenuation above -30 dB without confirmed antenna separation
  of at least 2 m and no reflective enclosures.
- Always restore TX to the safe state (`TX LO powerdown = 1`,
  `TX attenuation = -89.75 dB`) after the sweep.
- Record the `dmesg` tail after each TX enable to catch any `xo_disable`
  or `clock_lost` warnings from the AD9363 driver.

## Expected outputs

| Output | Content |
|---|---|
| TX calibration table (JSON or Markdown) | TX attenuation vs RTL-SDR peak power (dB, relative) |
| `docs/assets/lab67_tx_power_calibration_table.json` | machine-readable calibration reference |

## Report checklist

- [ ] State RTL-SDR tuner gain used throughout the sweep.
- [ ] Record center frequency and tone offset.
- [ ] Attach the full calibration table.
- [ ] Identify the safe TX attenuation range for the available antenna geometry.
- [ ] Confirm TX was restored to safe state after sweep.

## Engineering conclusion template

```text
TX power calibration at ____ MHz used DDS tone offset ____ kHz and RTL-SDR
tuner gain ____ dB. Received power ranged from ____ dBFS at ____ dB attenuation
to ____ dBFS at ____ dB attenuation. Safe operating range for subsequent labs:
TX attenuation between ____ dB and ____ dB. TX was restored to safe state:
TX LO powerdown = 1, attenuation = -89.75 dB.
```
