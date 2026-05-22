# End-to-end tone demo measurement report

This page is the first executable flagship demonstration for the Zynq SDR Course. It turns the high-level course route into a reproducible measurement-style workflow that can run in CI without RF hardware.

## Purpose

The demo validates the complete engineering pattern:

```text
reference model -> fixed-point-friendly CI16 IQ -> dataset manifest -> offline analysis -> metrics -> measurement report
```

It is intentionally synthetic. This keeps the CI path deterministic while preserving the same structure that will later be used for real Zynq/AD9363 + RTL-SDR/HDSDR captures.

## How to run

From the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/end_to_end_tone_demo.py
```

Or run it as part of the executable lab smoke path:

```bash
python tools/run_all_labs.py
```

## Generated artifacts

The script generates the following artifacts:

| Artifact | Path | Role |
|---|---|---|
| Reference spectrum | `docs/assets/end_to_end_tone_reference_spectrum.png` | FFT of the ideal reference tone. |
| Captured spectrum | `docs/assets/end_to_end_tone_capture_spectrum.png` | FFT after synthetic RF/receiver impairments and CI16 quantization. |
| Captured IQ time trace | `docs/assets/end_to_end_tone_capture_time.png` | I/Q waveform used for sanity checking clipping and scaling. |
| Metrics JSON | `docs/assets/end_to_end_tone_metrics.json` | Machine-readable measurement summary. |
| Dataset manifest | `datasets/manifests/end_to_end_tone_demo_v1.yml` | Metadata, checksum, format, sample rate and RF-path assumptions. |
| CI16 capture | `blocks/block_11_integrated_sdr_project/assets/end_to_end_tone_demo/end_to_end_tone_demo_v1.ci16` | Generated synthetic IQ capture. |

## Signal model

| Parameter | Value |
|---|---:|
| Sample rate | `2.4 MS/s` |
| Center frequency metadata | `100 MHz` |
| Expected complex tone offset | `125 kHz` |
| Capture format | `CI16`, interleaved I/Q, little-endian |
| Sample count | `131072` |
| Simulated attenuation | `40 dB` |
| Simulated RX gain | `20 dB` |

## Simulated impairments

The synthetic capture intentionally includes small imperfections that are common in real SDR recordings:

| Impairment | Purpose |
|---|---|
| Frequency error | Tests peak detection and frequency-plan validation. |
| DC offset | Forces the analyzer to ignore the DC bin when searching for the tone. |
| I/Q gain mismatch | Makes the capture more realistic than an ideal mathematical tone. |
| Small phase mismatch | Prepares the route for later constellation and EVM work. |
| Additive noise | Enables an SNR-style estimate. |
| CI16 quantization | Bridges floating-point model and fixed-point-friendly IQ storage. |

## Measurement metrics

The JSON report contains:

| Metric | Meaning |
|---|---|
| `measured_peak_hz` | Detected baseband frequency of the strongest non-DC spectral component. |
| `frequency_error_hz` | Difference between measured and expected tone offset. |
| `estimated_snr_db` | Peak-to-median-noise-floor estimate. |
| `dc_offset_magnitude` | Mean complex offset magnitude. |
| `clipping_fraction` | Fraction of samples close to full-scale clipping. |
| `rms_level_dbfs` | RMS level relative to full scale. |
| `sha256` | Checksum of the generated CI16 capture. |

## Acceptance criteria

The demo is accepted when:

- the script exits with code `0`;
- all generated artifacts exist and are non-empty;
- the manifest contains sample rate, center frequency, format and checksum;
- the detected peak is close to the expected tone offset plus simulated frequency error;
- `clipping_fraction` is zero or close to zero;
- the workflow is included in `tools/run_all_labs.py`.

## Path to real hardware capture

The same structure should be reused for a real board-level experiment:

```text
Zynq/AD9363 tone generation -> controlled RF path -> RTL-SDR/HDSDR recording -> manifest -> analysis -> report
```

For hardware data, replace the generated CI16 file with a real capture and update:

- `source`;
- `hardware.receiver`;
- `hardware.transmitter`;
- `rf_path`;
- `attenuation_db`;
- `rx_gain_db`;
- `sha256`;
- sample rate and center frequency;
- notes about overload and RF safety.

## Safety note

For real RF experiments, use the [RF safety guide](rf-safety.md). Do not connect TX and RX directly without a calculated attenuation chain and receiver input protection assumptions.
