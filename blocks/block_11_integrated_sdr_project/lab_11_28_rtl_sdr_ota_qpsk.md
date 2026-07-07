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

## Measured result — 2026-07-07

| Gate | Result |
|---|---:|
| Compared bits | 280 |
| Bit errors / BER | 0 / 0 |
| EVM RMS | 20.250% |
| SNR estimated from EVM | 13.87 dB |
| Residual frequency offset | +1995.8 Hz |
| Clipping fraction | 0 |

The lower-power `-55 dB` run produced one error in 280 bits and 37.379% EVM. Raising the TX gain to `-50 dB` improved the selected frame without clipping. See `reports/hardware/qpsk-rtl-sdr-qualification-20260707.md` for the complete evidence chain and limitations.

This result is a single-frame external RF qualification. A burst-by-burst detector and a controlled cabled run are still required for a repeatability or BER-floor claim.
