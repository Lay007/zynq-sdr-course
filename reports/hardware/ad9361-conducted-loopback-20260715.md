# AD9361 conducted loopback — 2026-07-15

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

## Runtime BPSK and QPSK follow-up

The same protected TX1-to-RX1 path was then exercised with the runtime PL
modems. These checks deliberately distinguish a fabric/BIST test from a real RF
test: the new Lab 11.27 `rf` mode configures AD9361 but does not enable either
internal loopback.

| Check | Payload MD5 | RF settings | Result |
|---|---|---|---|
| QPSK fabric preflight | `e5f91b5271ce3295ffcb1088ee477405` | RF skipped | 10/10 frames, 140/140 symbols, BER = 0 |
| BPSK conducted, self-timed | `662222122c76331e793d1049e42a2507` | TX -60 dB, RX 30 dB | best run 204/281 bits, 90 errors, timed out |
| QPSK conducted, fixed phase | `662222122c76331e793d1049e42a2507` | TX -60 dB, RX 30 dB | best run 139/140 symbols, 129 errors |
| QPSK conducted, DC blocker + Costas, raw ADC | `e5f91b5271ce3295ffcb1088ee477405` | TX -40 dB, RX 30 dB | 0/10 preamble locks at offset 108 |

The BPSK result improved from 89 to 204 received bits when TX attenuation moved
from -70 to -60 dB, but the capture debug peak stayed at 29--30 counts and the
error rate did not close. Changing the BPSK decision axis from I to Q produced no
preamble lock. This points to burst timing/phase alignment rather than overload.

The fixed-phase QPSK run is stronger localization evidence: 139 of 140 symbols
were recovered, while about half of the bits were wrong. That is consistent with
an unresolved constellation phase. A later payload containing the DC blocker
and Costas loop remained perfect in fabric loopback, but its physical raw-ADC
mode did not lock. Raising TX from -60 to -40 dB did not change the raw-path
diagnostic amplitude, so the remaining blocker is the runtime RX source/scaling
and burst-phase path, not insufficient conducted RF power.

The legacy `bridge_rx_only` host-TX control was also repeated. It again left
`rx_valid_count` at zero, confirming that image is not a valid fallback for this
measurement.

Evidence:

- `docs/assets/lab1119_bpsk_conducted_20260715.json`
- `docs/assets/lab1127_qpsk_fabric_preflight_20260715.json`
- `docs/assets/lab1127_qpsk_conducted_no_costas_20260715.json`
- `docs/assets/lab1127_qpsk_conducted_costas_raw_20260715.json`

After each runtime experiment the board was rebooted to stock. The final
readback again showed TX LO powered down, TX attenuation `-89.75 dB`, LO at
2.4 GHz and the stock 30.72 MS/s sample rate.

## Limitations and conclusion

The attenuator value is the marked nominal value; its `S21` and the cable loss
have not yet been measured with a NanoVNA. Therefore this run proves safe
conducted signal flow, frequency-plan correctness and absence of overload. It
also reconfirms the QPSK modem in fabric and observes partial BPSK/QPSK frames
through the real cable, but it does not yet claim end-to-end conducted BER
success or an absolute RF power calibration. Issue #25 still needs the passive
path `S21` measurement, and the runtime RX timing/source blocker above must be
closed.
