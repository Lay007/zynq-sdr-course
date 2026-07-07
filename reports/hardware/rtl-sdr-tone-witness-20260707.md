# ZynqSDR to RTL-SDR tone witness — 2026-07-07

A low-power antenna-to-antenna smoke test verified that both connected RF devices and the capture workflow operate together.

| Parameter | Value |
|---|---:|
| Zynq TX center frequency | 868.300 MHz |
| DDS offset | +200 kHz |
| Zynq TX attenuation | -55 dB |
| DDS scale | 0.1 |
| RTL-SDR sample rate | 2.4 MS/s |
| RTL-SDR tuner gain | 30 dB |
| Samples analyzed | 1,048,576 |

| Metric | Result |
|---|---:|
| Measured tone offset | +201.965 kHz |
| Frequency error | +1.965 kHz |
| SNR estimate | 40.30 dB |
| Peak | -51.52 dBFS |
| Clipping fraction | 0 |
| Quality gate | PASS |

The first conservative step at `-70 dB`, scale `0.05` did not expose the expected tone. Increasing only to `-55 dB`, scale `0.1` produced a clean witness without clipping. After capture, the helper restored stock state with TX at `-89.75 dB` and TX LO powered down.

Artifacts:

- `docs/assets/lab1124_rtl_smoke_868m3_step2_report.json`
- `docs/assets/lab11_24_dds_tone_rtl_monitor_live_20260707_rtl_smoke_868m3_step2_metrics.json`
- `docs/assets/lab94_lab11_24_dds_tone_rtl_monitor_live_20260707_rtl_smoke_868m3_step2_spectrum.png`
- `docs/assets/lab94_lab11_24_dds_tone_rtl_monitor_live_20260707_rtl_smoke_868m3_step2_time_preview.png`

The raw WAV and manifest remain local under `tmp/`; this report is an instrument-path witness, not yet the publication-cleared QPSK dataset.
