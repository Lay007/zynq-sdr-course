# AD9361 conducted tone loopback — 2026-07-15

## Result

A short TX1-to-RX1 conducted loopback through a marked 30 dB fixed attenuator
produced a clean DDS tone without ADC clipping. The conservative accepted point
used TX attenuation `-60 dB`, DDS scale `0.05` and manual RX gain `20 dB`.

| Parameter | Value |
|---|---:|
| RF chain | TX1 -> coax -> marked 30 dB attenuator -> RX1 |
| Center frequency | 915 MHz |
| DDS offset | +700 kHz |
| Sample rate | 3.84 MS/s |
| RF bandwidth | 2.0 MHz |
| Samples analyzed | 262,144 |
| TX attenuation | -60 dB |
| DDS scale | 0.05 |
| RX gain | 20 dB, manual |

| Metric | Result |
|---|---:|
| Measured tone offset | +700.019531 kHz |
| Frequency error | +19.531 Hz |
| SNR estimate | 15.54 dB |
| Peak | -114.90 dBFS |
| Noise floor | -130.44 dBFS |
| DC offset magnitude | 0.00000276 |
| Clipping fraction | 0 |
| Quality gate | PASS |

## Safe bring-up sequence

The board started with TX LO powered down and TX gain at `-89.75 dB`. A TX-off
capture established the local noise baseline. Short 65,536-sample captures then
tested `-89.75`, `-80`, `-70` and `-60 dB` TX attenuation at constant DDS scale
`0.05` and RX gain `20 dB`. The expected line first became unambiguous at
`-60 dB`; no point showed clipping. A final 262,144-sample capture at that same
setting supplied the reported metrics.

After every capture, the helper restored the stock state. Final readback showed
TX gain `-89.75 dB`, TX LO powerdown enabled, and the stock 2.4 GHz / 30.72 MS/s
configuration restored.

## Artifacts

- `docs/assets/lab68_conducted_loopback_915mhz_30db_metrics.json`
- `docs/assets/lab68_conducted_loopback_915mhz_30db_spectrum.png`
- `docs/assets/lab68_conducted_loopback_915mhz_30db_time_preview.png`

The raw CI16 capture and generated manifest remain local under
`tmp/conducted_loopback/`. The capture SHA256 is
`80D4AC1BDDDAD82237F20321F63AA32796538CF175034F4AD239C497EDCA6ACD`.

## Reproduction

With the same protected 50-ohm conducted path connected:

```powershell
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py `
  --uri ip:192.168.40.1 `
  --center-frequency-hz 915000000 `
  --sample-rate-hz 3840000 `
  --rf-bandwidth-hz 2000000 `
  --sample-count 262144 `
  --tone-offset-hz 700000 `
  --tone-scale 0.05 `
  --rx-hardwaregain-db 20 `
  --tx-hardwaregain-db -60 `
  --out-iq tmp/conducted_loopback/qualified_tone.ci16 `
  --manifest-out tmp/conducted_loopback/qualified_tone.yaml

python blocks/block_09_recording_and_analysis_tools/python/lab_9_2_read_ci16_iq_and_analyze.py `
  --manifest tmp/conducted_loopback/qualified_tone.yaml `
  --out-dir tmp/conducted_loopback/analysis
```

## Limitations and conclusion

The attenuator value is the marked nominal value; its `S21` and the cable loss
have not yet been measured with a NanoVNA. Therefore this run proves safe
conducted signal flow, frequency-plan correctness and absence of overload, but
it is not an absolute RF power calibration. Issue #25 still needs the passive
path `S21` measurement before full closure.
