# AD9361 conducted loopback — 2026-07-15

## Result

A short TX1-to-RX1 conducted loopback through a measured 30 dB fixed attenuator
produced a clean DDS tone without ADC clipping. The conservative accepted point
used TX attenuation `-60 dB`, DDS scale `0.05` and manual RX gain `20 dB`.

| Parameter | Value |
|---|---:|
| RF chain | TX1 -> coax -> measured 30 dB attenuator -> RX1 |
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
| QPSK phase-picker fabric qualification | `b916ea6f67ec91834e3441a031338a3e` | RF skipped | 3/3 frames, 140/140 symbols, BER = 0 |
| QPSK conducted, phase picker + Costas, raw ADC | `b916ea6f67ec91834e3441a031338a3e` | TX -60 dB, RX 30 dB | 1/24 full frames; best 140/140 symbols, 142/280 errors at offset 2 |
| QPSK conducted, phase picker + Costas, RX FIFO | `b916ea6f67ec91834e3441a031338a3e` | TX -60 dB, RX 30 dB | 0/24 full frames |
| BPSK conducted control on final payload | `b916ea6f67ec91834e3441a031338a3e` | TX -60 dB, RX 30 dB | 214/281 bits, 99 errors, timed out |

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

The next payload integrated the already-tested eight-phase matched-filter picker
into the runtime QPSK chain. Its first implementation exposed a real 250 MHz
timing failure (`WNS -4.635 ns`) and was rejected without loading the board. The
picker argmax was changed from a seven-comparator combinational chain to one
comparison per phase during the last measurement symbol; its dynamic delay tap
was also restricted to the eight reachable samples. The final implementation
meets all timing constraints with `WNS +0.129 ns`, `WHS +0.051 ns`, zero failing
endpoints and zero DRC errors. The word-swapped payload is 2,507,608 bytes with
SHA256 `812D0825B313C8340015C448679FE5A0A4FB56E21A833B22D89AC2ED5D349628`.

The raw conducted capture peaks at only 27--30 ADC counts. The former signal
gate of 1000 therefore kept both the picker and Costas loop frozen. A bridge-only
threshold of 8 passes the captured 3000-sample leading-noise stress test at BER
0/280 and, on hardware, changes the result from no QPSK locks to one complete
140-symbol frame. Its 142/280 residual errors are near the random half-bit floor,
so sample phase and frame length are no longer the primary blocker; carrier or
constellation recovery on the raw RX source is. The FIFO source never produced a
full frame and is not a fallback. The BPSK control remained partial (214/281), so
the QPSK-only changes did not falsely close or mask the BPSK limitation.

Evidence:

- `docs/assets/lab1119_bpsk_conducted_20260715.json`
- `docs/assets/lab1127_qpsk_fabric_preflight_20260715.json`
- `docs/assets/lab1127_qpsk_conducted_no_costas_20260715.json`
- `docs/assets/lab1127_qpsk_conducted_costas_raw_20260715.json`

After each runtime experiment the board was rebooted to stock. The final
readback again showed TX LO powered down, TX attenuation `-89.75 dB`, LO at
2.4 GHz and the stock 30.72 MS/s sample rate.

## Limitations and conclusion

The attenuator was subsequently checked at 30 dB with a flat response from
50 MHz to 1 GHz, covering the 915 MHz test frequency. Cable loss was not
measured separately, so this is a calibrated attenuator value rather than an
absolute connector-to-connector power calibration. The run proves safe
conducted signal flow, frequency-plan correctness and absence of overload. It
also reconfirms the QPSK modem in fabric and now recovers a complete QPSK frame
through the real cable, but it does not yet claim end-to-end conducted BER
success because that frame contains 142/280 bit errors. The remaining blocker is
raw-path carrier/constellation recovery; BPSK timing recovery also remains
partial.
