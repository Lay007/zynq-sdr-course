# Lab 10.6 — Digital RF Attenuator: Step, Range, and Linearity Check

## Goal

Learn how to verify a digital RF attenuator before using it in SDR experiments. After this lab, the student should understand how closely the measured attenuation follows the requested setting, whether the attenuator is suitable for controlled sweeps, and which limitations must be stated in the report.

This lab complements NanoVNA Lab 10.5 and prepares the measurement basis for Block 6 and Block 11: safe cabled loopback, RF level planning, and explaining differences between SNR, EVM, and BER.

## Equipment

- NanoVNA-H4 or a compatible VNA.
- Digital RF attenuator, for example 0…31.75 dB range with 0.25 dB step.
- SOLT calibration kit: Open, Short, Load, Thru.
- Two short 50-ohm SMA cables.
- 50-ohm load.
- Optional fixed protective attenuator, 3–10 dB.

## Safety

In this lab the attenuator is checked as a passive or small-signal device. Do not connect it directly to a Zynq/AD936x transmitter, signal generator, or amplifier output without calculating the power level, maximum allowed input power, and required protective attenuation.

Before measurement, check:

- attenuator maximum power rating;
- absence of DC voltage on the measured path;
- correct 50-ohm connections;
- absence of external RF signal at the NanoVNA input.

## Short theory

For an attenuator, the main parameter is `S21`, which describes transmission through a two-port network. If the attenuator is set to 10 dB, the ideal NanoVNA reading should be approximately `S21 = -10 dB` at the operating frequency.

A real measurement includes errors:

- frequency response ripple;
- cable and adapter loss;
- calibration error;
- finite step resolution;
- attenuator accuracy limit;
- input and output mismatch.

For the SDR course, the goal is not just a good-looking plot. The engineering conclusion is whether this attenuator can be used as a controlled RF-level element in BER/SNR/EVM experiments.

## NanoVNA preparation

1. Set the frequency span around the SDR operating band. Examples:
   - 100…1000 MHz for a general check;
   - 800…950 MHz for 868/915 MHz;
   - 2.3…2.5 GHz for 2.4 GHz, if the specific NanoVNA and attenuator support this range.
2. Connect measurement cables to the NanoVNA ports.
3. Perform SOLT calibration at the ends of these cables.
4. Enable `S21 LogMag` display.
5. Save the calibration state.

## Procedure

1. Set the attenuator to 0 dB.
2. Connect it between NanoVNA ports: CH0 → attenuator → CH1.
3. Measure `S21` and record the value at the operating frequency.
4. Repeat the measurement for a useful set of points, for example:
   - 0 dB;
   - 1 dB;
   - 3 dB;
   - 6 dB;
   - 10 dB;
   - 20 dB;
   - 30 dB;
   - 31.75 dB.
5. For small-step verification, measure a local range such as 0…2 dB with 0.25 dB step.
6. Save screenshots or CSV/Touchstone files.
7. Build an error table: requested attenuation, measured attenuation, error.

## Result table

| Frequency | Requested attenuation | Measured `S21` | Actual attenuation | Error | Conclusion |
|---:|---:|---:|---:|---:|---|
| `____ MHz` | 0 dB | `____ dB` | `____ dB` | `____ dB` | baseline |
| `____ MHz` | 1 dB | `____ dB` | `____ dB` | `____ dB` |  |
| `____ MHz` | 3 dB | `____ dB` | `____ dB` | `____ dB` |  |
| `____ MHz` | 6 dB | `____ dB` | `____ dB` | `____ dB` |  |
| `____ MHz` | 10 dB | `____ dB` | `____ dB` | `____ dB` |  |
| `____ MHz` | 20 dB | `____ dB` | `____ dB` | `____ dB` |  |
| `____ MHz` | 30 dB | `____ dB` | `____ dB` | `____ dB` |  |
| `____ MHz` | 31.75 dB | `____ dB` | `____ dB` | `____ dB` | max range |

Actual attenuation is easiest to calculate relative to the 0 dB baseline:

```text
A_actual(dB) = S21_0dB - S21_setting
error(dB) = A_actual - A_setting
```

## 0.25 dB step check

| Requested attenuation | Measured `S21` | Increment from previous point | Expected increment | Conclusion |
|---:|---:|---:|---:|---|
| 0.00 dB | `____ dB` | — | — | baseline |
| 0.25 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 0.50 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 0.75 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 1.00 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 1.25 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 1.50 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 1.75 dB | `____ dB` | `____ dB` | 0.25 dB |  |
| 2.00 dB | `____ dB` | `____ dB` | 0.25 dB |  |

## What to inspect on the plot

- `S21` should decrease approximately by the requested attenuation.
- The `S21` trace should not contain unexpected deep notches inside the operating band.
- The error should not jump sharply between neighboring settings.
- At high attenuation, the NanoVNA noise floor can limit accuracy.
- If `S21` stops changing while attenuation increases, the measurement may have reached the instrument dynamic range or the setup may be wrong.

## Link to Zynq-SDR

After verification, the attenuator can be used as a controlled element in later work:

- Lab 6.7 — dBm vs dBFS power calibration;
- Lab 6.8 — Zynq stock-shell OTA DDS tone observation;
- Lab 11.23 — Runtime PL RTL-SDR attenuation sweep;
- final BER/SNR/EVM measurements.

The main engineering conclusion is: when the attenuator step is known and verified, BER, EVM, or SNR changes can be connected to a controlled RF-level change instead of an unknown RF-path error.

## Review questions

1. Why is `S21` more important than `S11` for an attenuator?
2. Why is attenuation error best calculated relative to the 0 dB baseline?
3. What happens if the attenuator has poor input or output matching?
4. Why can NanoVNA readings become unstable at high attenuation values?
5. How can a 1 dB attenuator error affect BER/SNR conclusions?

## Artifacts

- NanoVNA screenshots or CSV/Touchstone export;
- attenuation range table;
- 0.25 dB step-check table;
- short conclusion on attenuator suitability for controlled sweeps;
- limitations: frequency, power, dynamic range, and accuracy.