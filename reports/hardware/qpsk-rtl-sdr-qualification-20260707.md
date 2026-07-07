# QPSK Zynq-to-RTL-SDR OTA qualification — 2026-07-07

## Result

The timing-clean dual-modem payload transmitted its deterministic 140-symbol QPSK ROM frame through the Zynq TX1/AD9361 RF path. An independent RTL-SDR received the over-the-air signal through a separate antenna. The promoted `-50 dB` TX-gain run recovered all 280 compared bits with zero errors.

| Metric | Conservative run | Promoted run |
|---|---:|---:|
| TX hardware gain | -55 dB | -50 dB |
| RTL-SDR tuner gain | 30 dB | 30 dB |
| Compared bits | 280 | 280 |
| Bit errors | 1 | 0 |
| BER | 3.571429e-3 | 0 |
| EVM RMS | 37.379% | 20.250% |
| SNR estimated from EVM | 8.55 dB | 13.87 dB |
| Residual frequency offset | +2003.7 Hz | +1995.8 Hz |
| Clipping fraction | 0 | 0 |

Both runs used a 2.4 MS/s RTL-SDR capture centered at 868.3 MHz. The Zynq sample rate was 3.84 MS/s, the QPSK symbol rate was 480 ksymbol/s, and the RRC rolloff was 0.35. The promoted capture SHA256 is `ebea5717237f4c8a1df830370f124cc77ced9af32e741419f6e340ae9d669ffa`.

![Promoted QPSK constellation](../../docs/assets/lab1128_lab11_22_runtime_pl_rtl_monitor_live_20260707_qpsk_ota_cdcfix_02_constellation.png)

![Promoted QPSK selected-window spectrum](../../docs/assets/lab1128_lab11_22_runtime_pl_rtl_monitor_live_20260707_qpsk_ota_cdcfix_02_baseband_spectrum.png)

## Evidence chain

- Capture manifest: `datasets/lab11_22_runtime_pl_rtl_monitor/manifest_live_20260707_qpsk_ota_cdcfix_02.yaml`
- Capture/session report: `docs/assets/lab1122_runtime_pl_rtl_monitor_live_20260707_qpsk_ota_cdcfix_02.json`
- Offline metrics: `docs/assets/lab1128_lab11_22_runtime_pl_rtl_monitor_live_20260707_qpsk_ota_cdcfix_02_metrics.json`
- Lower-power comparison: matching `_01` manifest, capture report and metrics files
- Transmitted payload MD5: `414eca88fe628de06c9bef09cf73e30e`
- Transmitted payload SHA256: `48a17b8cbabec9c7d9c5236cb665397d154813e6537c24067765f601d73ead28`

The analyzer reads the exact `bpsk_frame_bits.mem` ROM shared by the QPSK RTL source, pairs consecutive bits onto I and Q, resamples the RTL-SDR recording, applies the RRC matched filter, estimates residual CFO and phase, and compares the recovered axes against all 280 transmitted bits.

## Reproduction

Capture:

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

Analyze:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_28_read_rtl_wav_ota_qpsk.py `
  --manifest datasets/lab11_22_runtime_pl_rtl_monitor/manifest_live_20260707_qpsk_ota_cdcfix_02.yaml
```

## Limits

- BER=0 applies to one selected 280-bit frame in the promoted recording; it is not a statistical BER floor or a 30/30 burst success claim.
- SNR is inferred from EVM after scalar/CFO alignment, not measured independently from calibrated RF power.
- The RF path was antenna-to-antenna, so geometry and ambient interference are not controlled like a cabled attenuator experiment.
- The raw WAV remains local-only; its SHA256, manifest, plots, capture report and derived metrics are committed.
- Every capture session rebooted the board to stock; the final state had TX gain `-89.75 dB` and the TX LO powered down.
