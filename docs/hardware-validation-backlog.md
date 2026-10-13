# Hardware Validation Backlog

This page separates documentation work from tasks that require real hardware access.

## Priority hardware tasks

| Priority | Issue | Task | Evidence to collect |
|---|---:|---|---|
| P0 | #25 | Complete safe cabled loopback validation | conducted capture/report are measured; add NanoVNA `S21` for the cable and marked 30 dB attenuator |
| Done | #26 | Publish and repeat QPSK demo IQ | public 64 KiB synthetic Git LFS payload, SHA256, deterministic rebuild, zero-BER replay and report assets are committed; measured OTA raw-data review remains separate |
| P2 | #29 | Extend AD9363 gain table | 915 MHz relative sweeps and the two-board large-signal boundary are measured; add passive-path calibration and other frequencies |
| P2 | #58 | AGC gain-transition phase experiment | gain-step amplitude/phase transients and static/dynamic modem BER are measured on two boards (`reports/hardware/ad9361-agc-transient-20261014.md`); still needed: steps synchronised to frames, and a common-reference or single-board setup to resolve the slow-attack phase step |
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
| #25 | The safe cabled tone run now has nominal attenuation, gain settings, capture metadata, FFT/metrics and a short conclusion in `reports/hardware/ad9361-conducted-loopback-20260715.md`. Full closure still requires NanoVNA `S21` evidence for the cable and marked 30 dB attenuator. |
| #26 | Complete for the synthetic replay scope: the public QPSK IQ fixture has a Git LFS payload, manifest, checksum, deterministic rebuild, replay command, zero BER/SER, constellation plot and EVM/SNR summary. This does not close publication review for the separate measured OTA WAV. |
| #29 | The first relative table is recorded in `reports/hardware/ad9361-gain-overload-table-20260715.md` with safe starting values and limitations. The large-signal boundary is measured on the two-board bench in `reports/hardware/ad9361-two-board-overload-20261013.md` (clipping onset per RX gain, BER under clipping, RSSI saturation). Full closure still requires calibrated passive-path loss and multiple frequencies. |

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

- NanoVNA characterization of the cable and marked 30 dB attenuator used by the measured conducted loopback.
- Calibrated multi-frequency extension of the AD9363 gain table and controlled large-signal boundary.
- Receiver large-signal checks.
- Final measured QPSK or OFDM demo.
