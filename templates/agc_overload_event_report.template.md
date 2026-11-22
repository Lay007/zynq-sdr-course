# AD9361 two-board overload and AGC event report

## Provenance and hardware
| Field | Value |
|---|---|
| Evidence type | synthetic / RTL simulation / GPIO-on-board / measured RF |
| Experiment ID / UTC | |
| Board A TX image / git revision | |
| Board B RX image / git revision | |
| AD9361/AD9363 identification and channel | |
| Board schematic / XDC verifying CTRL_OUT | |
| bitstream hash / AXI-Lite base | |
| RF LO / sampling / RX bandwidth | |
| RX mode / gain before and after | |
| TX attenuation / waveform amplitude | |
| RF path and verified total S21 | |
| Safety checks and maximum input level | |
| RX IIO PHY name, software version | |
| CTRL_OUT selector and mask, before / after | |
| Clock source and timestamp alignment method | |
| IQ capture format, sample count, checksum | |

## Scope and synchronization

State whether event time is recorded in PL ticks, RX sample indices or host time.
Do not calculate inter-board sub-millisecond latency from Linux process timestamps.
State how a local 'step' reference was generated and how it shares the event-clock domain.

## Observations

| Run | Gain mode | Level step (dB) | Large LMT events | Large ADC events | Small ADC events | Gain change events (separate selector) | IQ clipped (%) | Settling (ms) | Evidence |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| | | | | | | | | | |

## Plots
- [ ] IQ magnitude (dBFS) vs time, from real IQ capture
- [ ] RX gain vs time, stating IIO polling limitations
- [ ] CTRL_OUT event/sticky timeline, when physically routed
- [ ] MGC / slow / fast comparison with uncertainties
- [ ] Blocker-in-analog-passband case, with RF bandwidth explicitly stated

## Analysis and engineering decision

State whether overload is detected before visible IQ clipping, which detector
dominates, whether AGC reset/peak-wait periods affect event counts, and which
mode best preserves the target waveform. Distinguish a hypothesis from an
observed or measured effect.

## Reproduction

Exact commands, script versions, testbench result, frequency/level settings,
passive-path calibration, and cleanup. Do not publish confidential IQ captures.
