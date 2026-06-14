# Hardware Validation Backlog

This page separates documentation work from tasks that require real hardware access.

## Priority hardware tasks

| Priority | Task | Evidence to collect |
|---|---|---|
| P0 | Validate Zynq/AD9363 tone output | frequency plan, screenshot, IQ metadata, FFT plot |
| P0 | Validate safe conducted loopback | attenuation value, gain settings, overload check |
| P1 | Capture QPSK demo IQ | dataset manifest, constellation, EVM/SNR metrics |
| P1 | Export Vivado resource reports | utilization, timing, latency notes |
| P2 | Add AD9363 gain table | gain settings, measured clipping/SNR behavior |
| P2 | Add final hardware report | report page, figures, limitations |

## Definition of done

A hardware task is done when it has:

- exact setup description;
- hardware and software versions;
- RF safety notes;
- data or screenshot evidence;
- reproducible analysis command;
- short engineering conclusion.

## Tasks that do not require hardware

- Dataset manifest templates.
- Final project rubric.
- Student CI guide.
- FPGA resource report template.
- Synthetic replay examples.

## Tasks that require hardware

- Real RF output validation.
- AD9363 gain table.
- Receiver overload thresholds.
- Vivado implementation reports for the exact board design.
- Final measured QPSK or OFDM demo.
