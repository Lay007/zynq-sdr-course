# SDR platform teardown template

Use this template when adding a new SDR board, RF frontend or observation receiver to the course.

The goal is not to repeat a vendor datasheet. The goal is to turn a board into an engineering object that can be reviewed, reproduced and used safely in a lab.

## 1. Platform summary

| Field | Notes |
|---|---|
| Board / module | Commercial name and revision. |
| Main RFIC | Tuner, transceiver or RF frontend. |
| Digital device | FPGA, SoC, MCU or host-only path. |
| Host interface | USB, Ethernet, PCIe, AXI, IIO, UART or other. |
| Clock sources | Main reference, optional external reference, clock distribution. |
| Intended role in the course | Observation receiver, cabled loopback endpoint, FPGA target, measurement helper. |

## 2. Signal-chain view

Describe the path in both directions if the platform supports them.

```text
RX connector -> protection/matching -> RFIC -> ADC/DDC -> digital interface -> host or FPGA
TX source    -> digital interface -> DAC/DUC -> RFIC -> matching/protection -> TX connector
```

For receive-only devices, keep only the RX path.

## 3. RFIC notes

Capture the properties that matter for labs:

- tuning range;
- instantaneous bandwidth;
- sample-rate limits;
- gain-control modes;
- analog filtering options;
- known zero-IF artifacts such as DC offset, LO feedthrough and IQ imbalance;
- calibration requirements;
- safe starting settings.

## 4. Digital datapath

Explain where samples are processed:

| Stage | Location | Course implication |
|---|---|---|
| Capture buffering | Host, PS, FPGA or driver | Determines latency and possible overruns. |
| DDC / DUC | RFIC, FPGA or host | Determines where fixed-point effects appear. |
| Packet framing | FPGA, firmware or host | Determines what can be tested in HDL. |
| Metrics | Offline script, host application or FPGA counter | Determines reproducibility of evidence. |

## 5. Transport and timing limits

Record the practical limits that students will hit before they hit theory limits:

- maximum reliable sample rate;
- buffer size and latency;
- underflow/overflow symptoms;
- timestamp or burst support;
- operating-system scheduling assumptions;
- repeatability limits for short bursts.

## 6. Clocking and frequency accuracy

Describe:

- reference clock source;
- ppm accuracy if known;
- external reference input or output;
- expected carrier-frequency offset;
- how clock error is measured or compensated in the lab.

## 7. Power and connection safety

Record:

- power input path;
- USB or external supply constraints;
- any bias or DC presence on RF connectors;
- attenuator requirement for cabled tests;
- default low-power startup procedure;
- what must be checked before connecting instruments or another SDR.

## 8. Course mapping

| Course block | How this platform is used |
|---|---|
| Block 1-3 | First observation, spectrum, IQ and filtering. |
| Block 5 | FPGA-facing comparison or HDL target if applicable. |
| Block 6 | RF frontend settings and measurement discipline. |
| Block 7 | TX/RX chain and cabled loopback. |
| Block 8 | CFO, phase, timing and impairment analysis. |
| Block 9 | IQ recording, metadata and replay. |
| Block 11-12 | Integrated project and final report evidence. |

## 9. Evidence package

A mature platform entry should include:

- this teardown page;
- a safe starting configuration;
- a short capture manifest;
- at least one generated plot;
- a small metrics table;
- limitations and next actions.
