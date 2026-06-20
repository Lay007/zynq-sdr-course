# Hardware Validation Backlog

This page separates documentation work from tasks that require real hardware access.

## Priority hardware tasks

| Priority | Issue | Task | Evidence to collect |
|---|---:|---|---|
| P0 | #25 | Validate Zynq/AD9363 tone and IQ capture | frequency plan, screenshot, IQ metadata, FFT plot |
| P0 | #25 | Validate safe cabled loopback | attenuation value, gain settings, signal-level check |
| P1 | #26 | Capture QPSK demo IQ | dataset manifest, constellation, EVM/SNR metrics |
| P2 | #29 | Add AD9363 gain table | gain settings, measured clipping/SNR behavior |
| P2 | #25/#26 | Add final hardware report | report page, figures, limitations |

## Priority non-hardware follow-up

| Priority | Task | Evidence to collect |
|---|---|---|
| P1 | Promote Block 5 OOC Vivado reports to integrated design reports | placed-and-routed utilization, timing, clocking context |
| P1 | Keep the hardware evidence index synchronized with new bring-up artifacts | evidence map entries, status labels, next proof action |
| P1 | Keep board-session templates ready | report template, dataset manifest template, compact measurement table |

## Issue-to-evidence closure plan

| Issue | Done when |
|---:|---|
| #25 | A tone or cabled loopback run has a frequency plan, AD9363 settings, attenuation notes, capture metadata, FFT plot and short conclusion. |
| #26 | A small QPSK IQ dataset has a manifest, checksum or external immutable link, replay command, constellation plot and EVM/SNR summary. |
| #29 | The AD9363 gain table records settings, input path, clipping behavior, safe starting values and measurement limitations. |

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
- Routed Vivado implementation reports for the exact board design.

## Tasks that require hardware

- Real board-level tone and IQ capture validation.
- AD9363 gain table.
- Receiver large-signal checks.
- Final measured QPSK or OFDM demo.
