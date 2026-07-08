# Hardware Validation Backlog

This page separates documentation work from tasks that require real hardware access.

## Priority hardware tasks

| Priority | Issue | Task | Evidence to collect |
|---|---:|---|---|
| P0 | #25 | Validate safe cabled loopback | attenuation value, gain settings, signal-level check, NanoVNA `S21` check of the passive path |
| P1 | #26 | Publish and repeat QPSK demo IQ | measured local manifest/plots/metrics exist; add raw-data access and per-burst statistics |
| P2 | #29 | Add AD9363 gain table | gain settings, measured clipping/SNR behavior; use `templates/ad9363-gain-overload-log.md` during the board session |
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
| #25 | The tone-and-IQ-capture portion is closed by Lab 6.8. The remaining loopback portion is done when a safe cabled run has attenuation value, gain settings, capture metadata, FFT plot, NanoVNA evidence for the passive RF path and short conclusion. |
| #26 | A small QPSK IQ dataset has a manifest, checksum or external immutable link, replay command, constellation plot and EVM/SNR summary. |
| #29 | The AD9363 gain table records settings, input path, clipping behavior, safe starting values and measurement limitations. The measurement log template is `templates/ad9363-gain-overload-log.md`. |

## NanoVNA pre-check for safe cabled loopback

Before connecting the AD9363 TX/RX path for conducted or near-field experiments, record a short NanoVNA check of the passive RF path:

| Item | Measurement | Done when |
|---|---|---|
| Cable | `S21` | insertion loss is recorded at the operating frequency |
| Fixed attenuator | `S21` | measured attenuation is close to the marked value |
| Digital attenuator | `S21` | selected sweep points are characterized or Lab 10.6 is referenced |
| Load | `S11` / VSWR | load is close to 50 ohm at the operating frequency |
| Optional filter | `S21` | passband and stopband behavior are documented |

Store screenshots, CSV or Touchstone files together with the RF measurement report. This prevents a bad cable, adapter, filter or attenuator from being misdiagnosed as CFO, ADC overload, synchronization failure or an FPGA logic bug.

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
- Board-session measurement log templates.

## Tasks that require hardware

- Safe cabled loopback validation after the OTA tone baseline.
- AD9363 gain table.
- Receiver large-signal checks.
- Final measured QPSK or OFDM demo.