# Lab 11.28 — Runtime QPSK through an external RTL-SDR

## Objective

Transmit the deterministic QPSK frame from the dual-modem PL through AD9361/TX1, record it with an independent RTL-SDR, and measure BER, EVM, residual frequency offset and clipping against the exact RTL ROM contents.

## Commands

Use a low-power antenna path or a calculated attenuated cable path. The measured antenna run used:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_22_capture_runtime_pl_rtl_monitor_wav.py `
  --modulation qpsk `
  --bit-bin-path tmp/bridge_txrx_mux.qpsk.cdcfix_20260707.wordswap.bit.bin `
  --center-frequency-hz 868300000 `
  --tx-attenuation-db -50 `
  --rtl-tuner-gain-db10 300 `
  --start-offset 62 `
  --qpsk-symbol-count 140 `
  --runtime-repeat-count 30 `
  --runtime-repeat-gap-ms 40 `
  --rebind-runtime-dds-driver `
  --rebind-runtime-adc-driver `
  --runtime-dds-ratecntrl 3
```

Analyze the generated manifest:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_28_read_rtl_wav_ota_qpsk.py `
  --manifest datasets/lab11_22_runtime_pl_rtl_monitor/manifest_live_20260707_qpsk_ota_cdcfix_02.yaml
```

## Metric calculation

The analyzer uses the exact QPSK RTL ROM as its reference. It removes one global DC estimate, detects burst energy with a median/MAD threshold, applies an RRC matched filter, and requires normalized reference correlation `>= 0.8`. It then estimates CFO from the linear phase slope of `rx * conj(reference)`, removes one complex gain/phase coefficient, and makes I/Q sign decisions.

The exact BER, FER, EVM, SNR-from-EVM, CFO, clipping and confidence-interval formulas are defined in `docs/digital-link-metrics.md`. In particular, `snr_from_evm_db = -20 log10(EVM_RMS)` is a diagnostic noise-dominant estimate, not calibrated RF SNR.

## Measured multi-burst result — 2026-07-07

| Metric | -55 dB run | -50 dB run |
|---|---:|---:|
| Commanded / detected bursts | 40 / 40 | 30 / 30 |
| BER=0 bursts | 23 / 40 | 30 / 30 |
| Frame error rate | 42.5% | 0% |
| Compared bits / bit errors | 11,200 / 18 | 8,400 / 0 |
| Aggregate BER | 1.607143e-3 | 0 |
| Median EVM RMS | 35.684% | 21.317% |
| Median SNR estimated from EVM | 8.95 dB | 13.43 dB |
| Median residual frequency offset | +1963.9 Hz | +1963.6 Hz |
| Median normalized correlation | 0.940 | 0.975 |
| Clipping fraction | 0 | 0 |

At `-50 dB`, the Wilson 95% interval for the zero-error burst rate is `88.65%…100%`. With zero errors in 8,400 compared bits, the rule-of-three upper bound is `BER < 3.571429e-4`; this is a sample-size bound, not a measured BER floor.

See `reports/hardware/qpsk-rtl-sdr-qualification-20260707.md` for plots, evidence files and limitations.

## Cross-session qualification — 2026-07-07

Three additional independent stock→runtime→stock sessions used the same payload and `-50 dB` operating point. Each session commanded 30 bursts.

| Session | Detected / commanded | BER=0 bursts | Bit errors / compared bits | Median EVM | Median CFO | Safe stock reboot |
|---|---:|---:|---:|---:|---:|---:|
| 01 | 30 / 30 | 30 / 30 | 0 / 8,400 | 18.396% | +1964.1 Hz | yes |
| 02 | 30 / 30 | 30 / 30 | 0 / 8,400 | 19.013% | +1975.1 Hz | yes |
| 03 | 30 / 30 | 30 / 30 | 0 / 8,400 | 19.728% | +1966.1 Hz | yes |
| Combined | 90 / 90 | 90 / 90 | 0 / 25,200 | 19.038% across frames | +1968.7 Hz across frames | 3 / 3 |

The combined zero-error burst-rate Wilson 95% interval is `95.91%…100%`. The zero-error BER rule-of-three bound is `BER < 1.190476e-4`. The session success interval is only `43.85%…100%` because three sessions are still a small session-level sample.

Rebuild the aggregate with:

```powershell
python tools/aggregate_lab11_28_sessions.py `
  "docs/assets/lab1128_lab11_22_runtime_pl_rtl_monitor_live_20260707_qpsk_ota_crosssession_*_metrics.json" `
  --json-out docs/assets/lab1128_qpsk_ota_crosssession_qualification_20260707.json `
  --plot-out docs/assets/lab1128_qpsk_ota_crosssession_summary_20260707.png
```

A controlled cabled run and a larger number of independent sessions remain necessary for calibrated link-budget and long-duration reliability claims.
