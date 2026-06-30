# Lab 6.7 - dBm vs dBFS power calibration

## Goal

Build a reproducible relationship between RF power in `dBm` and measured digital
amplitude in `dBFS` for the ZynqSDR + AD9363 platform, using the RTL-SDR as a
relative monitoring receiver and an external attenuator or calibrated reference
point when available.

This lab sits between the RX-only baseline (Lab 6.6) and the first full
over-the-air DDS tone observation (Lab 6.8). Its purpose is to establish a safe
TX attenuation range and a documented amplitude scale before committing to OTA
experiments, so that subsequent labs can choose attenuation settings with a
known link budget.

## Why this lab

At the current stage:

- Lab 6.6 confirmed the ZynqSDR RX path is healthy;
- TX experiments require a known safe starting point before enabling the AD9363
  PA;
- the RTL-SDR already exists as an independent receiver with a stable
  `tuner_gain_db10` setting;
- the course now needs a clear bridge between analog RF power (`dBm`) and
  digital sample amplitude (`dBFS`).

The table produced here lets later labs (6.8, 7.x, 11.x) set TX attenuation to a
point within the RTL-SDR dynamic range without risking overload. It also makes
it explicit that `dBFS` is not an absolute RF power unit unless a calibration
reference is recorded.

## Key definitions

| Term | Meaning | Course interpretation |
|---|---|---|
| `dB` | Ratio between two values | Used for attenuation, gain, SNR and relative spectrum differences |
| `dBFS` | Decibels relative to digital full scale | FFT/sample amplitude relative to ADC or file full-scale range |
| `dBm` | Decibels relative to 1 mW | Absolute RF power at a defined impedance, usually 50 ohm |

Important rule:

```text
dBFS is relative to the digital receiver scale.
dBm is absolute RF power at a measurement plane.
A conversion from dBFS to dBm is only valid after calibration.
```

## Calibration model

Use one calibration point measured at the same frequency, gain, sample rate,
FFT processing chain and receiver settings:

```text
P_dBm = P_ref_dBm + (P_dBFS - P_ref_dBFS)
```

where:

- `P_ref_dBm` is the known RF power at the receiver input or measurement plane;
- `P_ref_dBFS` is the measured digital peak or integrated power for that same
  reference signal;
- `P_dBFS` is the measured digital value for the unknown signal;
- `P_dBm` is the estimated RF power under the same receiver settings.

This is a relative calibration. Change any of the following and the calibration
must be repeated: tuner gain, analog gain, sample rate, FFT window, RBW/bin
integration method, center frequency, cables, attenuators or antenna geometry.

## Executable files

| File | Purpose |
|---|---|
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py` | confirm IIO device list before enabling TX |
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py` | used in sweep mode with `--tx-attenuation-db` argument |

No dedicated `lab_6_7_*.py` script is required: the sweep reuses `lab_6_8` with a
fixed DDS tone and varied TX attenuation. If a calibrated RF source or power
meter is available, record the reference point in the same report table.

## Measurement procedure

1. Confirm ZynqSDR IIO context is reachable:

   ```bash
   python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py \
     --uri ip:192.168.40.1
   ```

2. Set up the RTL-SDR at a fixed gain (for example, tuner gain = 200 / 20 dB)
   and tune to the DDS tone frequency (center + offset).

3. Record the receiver settings before any sweep:

   | Parameter | Value |
   |---|---|
   | Center frequency | `__________ Hz` |
   | Tone offset | `__________ Hz` |
   | Sample rate | `__________ sps` |
   | RTL-SDR tuner gain | `__________ dB` |
   | FFT size / window | `__________` |
   | Measurement plane | antenna / cable / attenuator output / other |

4. If a calibrated reference is available, record one known point:

   | Reference RF power (`dBm`) | Measured digital level (`dBFS`) | Notes |
   |---:|---:|---|
   | `__________` | `__________` | same gain, frequency and FFT settings |

5. For each TX attenuation value in the table below, run:

   ```bash
   python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py \
     --uri ip:192.168.40.1 \
     --center-frequency-hz 915000000 \
     --tx-attenuation-db <VALUE> \
     --tone-offset-hz 50000 \
     --capture-duration-s 2.0 \
     --run-tag tx_cal_<VALUE>dB
   ```

6. Read the RTL-SDR FFT peak for each run and record the received level in
   `dBFS`. If a valid reference point exists, estimate the corresponding `dBm`
   using the calibration model above.

## Suggested attenuation sweep

| TX attenuation (dB) | Expected RTL-SDR SNR | Notes |
|---:|---|---|
| -89.75 (min TX) | noise floor | safe baseline - no signal expected |
| -60 | low | start here |
| -50 | moderate | standard course default |
| -40 | good | increase only with antenna separation > 2 m |
| -30 | high | check RTL-SDR for overload symptoms |

## Result table template

| Run | TX attenuation (dB) | RTL-SDR peak (dBFS) | Estimated power (dBm) | SNR (dB) | Notes |
|---|---:|---:|---:|---:|---|
| baseline | -89.75 | `____` | n/a | `____` | noise floor |
| tx_cal_-60dB | -60 | `____` | `____` | `____` |  |
| tx_cal_-50dB | -50 | `____` | `____` | `____` |  |
| tx_cal_-40dB | -40 | `____` | `____` | `____` |  |
| tx_cal_-30dB | -30 | `____` | `____` | `____` | overload check |

If no calibrated `dBm` reference is available, leave the `Estimated power (dBm)`
column as `n/a` and explicitly state that the result is a relative `dBFS`
calibration only.

## Safety rules

- Never set TX attenuation above -30 dB without confirmed antenna separation of
  at least 2 m and no reflective enclosures.
- Prefer an external attenuator for any conducted or near-field measurement.
- Always restore TX to the safe state (`TX LO powerdown = 1`,
  `TX attenuation = -89.75 dB`) after the sweep.
- Record the `dmesg` tail after each TX enable to catch any `xo_disable` or
  `clock_lost` warnings from the AD9363 driver.
- Stop the sweep if the FFT peak stops increasing linearly with TX attenuation
  or if the spectrum shows clipping/overload products.

## Expected outputs

| Output | Content |
|---|---|
| TX calibration table (JSON or Markdown) | TX attenuation vs RTL-SDR peak power (`dBFS`) and optional estimated `dBm` |
| `docs/assets/lab67_tx_power_calibration_table.json` | machine-readable calibration reference |
| Report conclusion | valid receiver settings, safe TX attenuation range and calibration limitations |

Suggested JSON shape:

```json
{
  "lab": "6.7",
  "title": "dBm vs dBFS power calibration",
  "center_frequency_hz": 915000000,
  "tone_offset_hz": 50000,
  "receiver": "RTL-SDR",
  "receiver_gain_db": 20.0,
  "reference": {
    "available": false,
    "power_dbm": null,
    "measured_dbfs": null
  },
  "points": [
    {
      "tx_attenuation_db": -50.0,
      "measured_peak_dbfs": null,
      "estimated_power_dbm": null,
      "snr_db": null,
      "notes": "fill after measurement"
    }
  ]
}
```

## Report checklist

- [ ] State RTL-SDR tuner gain used throughout the sweep.
- [ ] Record center frequency, sample rate and tone offset.
- [ ] Describe whether the measurement is OTA, conducted, attenuated or
      calibrated with a known reference.
- [ ] Attach the full attenuation-vs-`dBFS` table.
- [ ] Attach the optional `dBm` estimate only if a valid reference point exists.
- [ ] Identify the safe TX attenuation range for the available antenna geometry.
- [ ] Confirm TX was restored to safe state after sweep.

## Engineering conclusion template

```text
TX power calibration at ____ MHz used DDS tone offset ____ kHz and RTL-SDR
tuner gain ____ dB. Received power ranged from ____ dBFS at ____ dB attenuation
to ____ dBFS at ____ dB attenuation. A dBm conversion was / was not applied.
Reference point: ____ dBm = ____ dBFS. Estimated RF power range: ____ dBm to
____ dBm. Safe operating range for subsequent labs: TX attenuation between
____ dB and ____ dB. TX was restored to safe state: TX LO powerdown = 1,
attenuation = -89.75 dB.
```
