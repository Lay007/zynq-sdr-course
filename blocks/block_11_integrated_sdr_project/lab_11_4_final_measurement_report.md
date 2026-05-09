# Lab 11.4 — Final Measurement Report

## Goal

Prepare the final engineering report for the integrated SDR project.

## Engineering question

> Does the final project provide enough evidence that the SDR chain works as intended?

## Required report sections

| Section | Required content |
|---|---|
| Abstract | project goal and result |
| Architecture | block diagram and interfaces |
| Method | simulation, RTL, RF and recording workflow |
| Setup | hardware, software, frequencies and gains |
| Results | figures, metrics and pass/fail table |
| Discussion | limitations and error sources |
| Reproducibility | commands, metadata and artifacts |
| Conclusion | engineering result and next steps |

## Minimum figures

- architecture diagram;
- TX/RX frequency plan;
- FFT of captured signal;
- constellation after synchronization;
- EVM/BER/SNR summary;
- reproducibility summary.

## Pass/fail table

| Criterion | Target | Measured | Status |
|---|---:|---:|---|
| frequency error |  |  |  |
| SNR |  |  |  |
| EVM |  |  |  |
| BER |  |  |  |
| clipping fraction |  |  |  |

## Report checklist

- [ ] All figures have captions.
- [ ] All metrics have units.
- [ ] Metadata are attached.
- [ ] Commands are reproducible.
- [ ] Limitations are stated honestly.
- [ ] The conclusion follows from measured data.

## Engineering conclusion template

```text
The final SDR project achieved ______. The measured frequency error was ____ Hz, SNR was ____ dB,
EVM was ____ % and BER was ____. The project meets / does not meet the success criteria because ______.
```
