# SDR Measurement Report Template

Use this template for RF, IQ recording and hardware validation labs.

## 1. Experiment summary

| Field | Value |
|---|---|
| Lab or project | TBD |
| Date | TBD |
| Hardware | TBD |
| Software tools | TBD |
| Goal | TBD |

## 2. Signal configuration

| Parameter | Value |
|---|---|
| Center frequency | TBD |
| Sample rate | TBD |
| RF bandwidth | TBD |
| Modulation | TBD |
| TX gain | TBD |
| RX gain | TBD |
| Capture format | TBD |

## 3. Setup diagram

```text
reference model
-> Zynq / AD9363
-> RF path
-> RTL-SDR
-> HDSDR IQ capture
-> offline analysis
```

## 4. Measurements

| Metric | Result | Comment |
|---|---:|---|
| Peak frequency | TBD | spectrum check |
| Occupied bandwidth | TBD | RF check |
| SNR | TBD | quality estimate |
| EVM | TBD | modulation quality |
| BER | TBD | receiver quality |

## 5. Plots

Include:

- FFT spectrum;
- waterfall screenshot if available;
- constellation plot;
- EVM or BER plot;
- hardware setup photo if useful.

## 6. Engineering conclusion

Summarize:

- whether the experiment passed;
- what limits the measurement quality;
- what should be changed in the next iteration;
- which assumptions must be documented.

## 7. Reproducibility notes

List exact commands, scripts and data files needed to reproduce the report.
