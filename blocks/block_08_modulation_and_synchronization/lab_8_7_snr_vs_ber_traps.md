# Lab 8.7 - SNR is not enough: BER/EVM traps

## Objective

Show why a digital SDR link must not be accepted from SNR alone. A receiver can
show a strong signal and a comfortable noise margin while the recovered bit
stream is still wrong because of carrier offset, timing error, phase ambiguity,
clipping or frame misalignment.

The lab produces a deterministic synthetic QPSK impairment sweep and records the
minimum link-quality evidence expected from later RF labs: SNR, EVM, BER,
compared bit count, frame-sync assumption and engineering conclusion.

## Key lesson

```text
SNR answers: "Is the signal visible above the noise?"
BER answers: "Did the digital link recover the correct bits?"
```

For BPSK/QPSK/OFDM labs, a high SNR is only a necessary condition. It is not a
proof of a working digital link. A reviewed result should include BER or FER and
the number of bits or frames that were actually compared.

## Files

| Path | Purpose |
|---|---|
| `blocks/block_08_modulation_and_synchronization/python/lab_8_7_snr_vs_ber_traps.py` | deterministic QPSK impairment sweep with SNR/EVM/BER metrics |

## Run

```bash
python blocks/block_08_modulation_and_synchronization/python/lab_8_7_snr_vs_ber_traps.py
```

## Scenarios

| Scenario | What remains high | What fails | Lesson |
|---|---|---|---|
| AWGN reference | SNR | nothing significant | Baseline case where SNR tracks BER reasonably well. |
| High-SNR CFO | SNR | BER/EVM | Frequency offset rotates the constellation; SNR does not see the phase walk. |
| Timing error | SNR | BER/EVM | Sampling away from the symbol center creates wrong decisions. |
| QPSK 90-degree ambiguity | SNR and aligned EVM | BER | A constellation can look clean after rotation, but bits are mapped to the wrong quadrant. |
| Clipping / overload | apparent SNR | EVM/BER margin | ADC/numeric overload is not Gaussian noise. |
| Wrong frame alignment | SNR | BER | A strong packet is useless if the receiver compares the wrong bits. |

## Expected outputs

| File | Content |
|---|---|
| `docs/assets/lab87_snr_vs_ber_summary.png` | SNR versus BER summary plot |
| `docs/assets/lab87_constellation_cfo.png` | constellation example with carrier-frequency offset |
| `docs/assets/lab87_constellation_timing_error.png` | constellation example with timing error |
| `docs/assets/lab87_constellation_qpsk_phase_ambiguity.png` | constellation example with unresolved QPSK quadrant ambiguity |
| `docs/assets/lab87_snr_vs_ber_metrics.json` | machine-readable scenario metrics and conclusions |

## Acceptance rule for later digital-link labs

A BPSK/QPSK/OFDM result is not considered a confirmed digital link until the
report states:

- SNR or noise estimate;
- EVM or constellation-quality metric;
- BER or FER;
- number of compared bits or frames;
- frame-sync status;
- frequency/timing offset notes when relevant.

If BER/FER is missing, the conclusion should be limited to spectrum or waveform
quality, not digital-link correctness.

## Engineering conclusion template

```text
The signal had SNR = ____ dB and EVM = ____ %, but BER = ____ over ____ bits.
Therefore the experiment confirms / does not confirm a working digital link.
The limiting factor is most likely ____ because ____.
```
