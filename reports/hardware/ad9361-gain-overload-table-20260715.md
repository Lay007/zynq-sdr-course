# AD9361 conducted gain and overload table — 2026-07-15

## Result

A protected TX1-to-RX1 path through a marked 30 dB fixed attenuator was used
to measure relative receive-gain and transmit-attenuation behavior at 915 MHz.
Ten short captures showed monotonic tone growth, stable frequency estimation
and zero clipping over the tested range.

This is a relative gain table, not an absolute input-power calibration. The
attenuator value is nominal and its `S21` has not yet been measured.

## Common setup

| Parameter | Value |
|---|---:|
| RF chain | TX1 -> coax -> marked 30 dB attenuator -> RX1 |
| Center frequency | 915 MHz |
| DDS offset | +700 kHz |
| DDS scale | 0.05 |
| Sample rate | 3.84 MS/s |
| RF bandwidth | 2.0 MHz |
| Samples per point | 65,536 |
| Gain mode | manual |

## RX gain sweep

TX attenuation was fixed at `-60 dB`.

| RX gain, dB | SNR, dB | Peak, dBFS | Noise floor, dBFS | Frequency error, Hz | Clipping | Gate |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 5.98 | -126.87 | -132.85 | -23,125.00 | 0 | FAIL |
| 10 | 7.38 | -124.49 | -131.86 | +19.53 | 0 | FAIL |
| 20 | 14.36 | -116.16 | -130.52 | +19.53 | 0 | PASS |
| 30 | 23.87 | -105.13 | -129.00 | +19.53 | 0 | PASS |
| 40 | 35.12 | -95.13 | -130.25 | +19.53 | 0 | PASS |

At `0 dB` RX gain the expected tone was below reliable detection and the peak
selector locked elsewhere inside the allowed search window. The frequency
estimate becomes stable by `10 dB`, while the quality gate first passes at
`20 dB`.

## TX attenuation sweep

RX gain was fixed at `30 dB`. More-negative TX values mean lower output power.

| TX attenuation, dB | SNR, dB | Peak, dBFS | Noise floor, dBFS | Frequency error, Hz | Clipping | Gate |
|---:|---:|---:|---:|---:|---:|---|
| -70 | 13.32 | -115.60 | -128.92 | +19.53 | 0 | PASS |
| -60 | 23.16 | -105.82 | -128.97 | +19.53 | 0 | PASS |
| -50 | 33.80 | -95.07 | -128.87 | +19.53 | 0 | PASS |
| -40 | 44.83 | -84.12 | -128.96 | +19.53 | 0 | PASS |
| -30 | 54.44 | -74.59 | -129.03 | +19.53 | 0 | PASS |

The measured peak changed by approximately 10 dB for each 10 dB TX step,
which is consistent with a linear conducted path over this range. No clipping
or noise-floor growth was observed. The sweep stopped at `-30 dB` because the
external attenuator has not yet been independently characterized; an overload
threshold was not established.

## Recommended starting points

| Purpose | TX attenuation | RX gain | DDS scale | Reason |
|---|---:|---:|---:|---|
| Lowest-power detectable bring-up | -70 dB | 30 dB | 0.05 | 13.32 dB SNR, no clipping |
| Robust routine tone check | -60 dB | 30 dB | 0.05 | 23.16 dB SNR, substantial headroom |
| Lower RX gain check | -60 dB | 20 dB | 0.05 | 14.36 dB SNR, no clipping |

Do not treat `-30 dB` as a generally safe default. It is only a measured point
for this specific nominal 30 dB conducted path.

## Reproduction and artifacts

Each point was captured with
`blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py`
and analyzed with
`blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py`.
The local CI16 files, manifests, plots and per-point metrics remain under
`tmp/gain_overload_20260715/`.

After every point the helper restored the stock state. Final readback must show
TX LO powerdown enabled and TX gain `-89.75 dB` before changing the RF path.

## Remaining work

1. Measure cable and attenuator `S21` at 915 MHz with a NanoVNA.
2. Repeat the table at one lower and one higher representative frequency.
3. Only after passive-path calibration, approach a large-signal limit with a
   stricter stop threshold and record the first compression/overload evidence.
