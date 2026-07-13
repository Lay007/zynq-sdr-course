# NanoVNA Measurement Report

## 1. Measurement identification

| Field | Value |
|---|---|
| Date and operator | |
| Instrument and firmware | |
| DUT | |
| Frequency range | |
| Sweep points | |
| Cables and adapters | |
| Calibration plane | |
| Calibration file / slot | |

Recommended artifact-set name:

```text
YYYYMMDD_<dut>_<start>-<stop>MHz_<s11|s21>_<run>
```

## 2. Calibration and control checks

- [ ] `OPEN`, `SHORT`, `LOAD` and `THRU` were completed.
- [ ] Calibration was performed at the ends of the measurement cables.
- [ ] Cables and sweep range were not changed after calibration.
- [ ] A 50-ohm `LOAD` control shows the expected match.
- [ ] A `THRU` control has no unexplained S21 notches.

## 3. Connection diagram

Describe `PORT1 → DUT → PORT2`, all adapters and DUT orientation. For a one-port measurement, explicitly state that PORT2 was not used.

## 4. Marker values

| Frequency | S11, dB | VSWR | S21, dB | Phase / delay | Comment |
|---:|---:|---:|---:|---:|---|
| | | | | | |
| | | | | | |
| | | | | | |

## 5. Evidence artifacts

- [ ] `S11 LOGMAG` screenshot.
- [ ] Smith-chart screenshot.
- [ ] `S21 LOGMAG` screenshot.
- [ ] `.s1p` or `.s2p` Touchstone file.
- [ ] CSV export when available.
- [ ] Connection photograph.
- [ ] Checksums for source files.

Relative paths:

```text
screenshots/
touchstone/
csv/
photos/
checksums.sha256
```

## 6. Interpretation for the SDR bench

Answer separately:

1. What additional loss does the DUT introduce at the SDR operating frequencies?
2. Are there S21 notches or a poor match near the experiment frequency?
3. Should the external attenuation, TX gain or RX gain be adjusted?
4. Can the measured defect explain degraded EVM, SNR or BER?
5. Which RF-path parameters must be copied into the Block 11 manifest?

## 7. Conclusion

- DUT suitability for subsequent BER/SNR experiments: **yes / conditional / no**.
- Valid operating range: 
- Required RF-path loss correction: 
- Limitations and uncertainty: 
