# Lab 10.5 — NanoVNA and RF Demo Kit: S11/S21, VSWR and Smith Chart

## Goal

Learn to use a NanoVNA-H4 and an RF Demo Kit as a safe bridge between RF theory and SDR bench measurements. The lab helps the student see not only a spectrum in SDR software, but also real matching, reflection, transmission and passive-network frequency response.

## Equipment

- NanoVNA-H4 or a compatible VNA.
- RF Demo Kit for NanoVNA-F or a similar educational board with SMA/IPX ports.
- SOLT calibration kit: Short, Open, Load, Thru.
- SMA/IPX adapters and short cables.
- 3–10 dB attenuator for input protection when the connection is uncertain.
- Optional: NanoVNA-Saver for plots, CSV/Touchstone export and TDR analysis.

## Safety

A NanoVNA is a small-signal instrument. Do not connect it to a Zynq/AD936x transmitter output, signal generator or amplifier without a power budget and a protective attenuator. Before connecting an unknown circuit, check that there is no DC voltage and no external RF source on the port.

## Short theory

A VNA measures complex S-parameters. For this lab two quantities are enough:

- `S11` — input reflection. It is used to estimate matching, VSWR and the point on the Smith chart.
- `S21` — forward transmission through a two-port network. It is used to measure the frequency response of a filter, cable, attenuator or thru path.

The SDR connection is direct: poor matching and unexpected `S21` notches may look like poor SNR, although the root cause is in the RF path, cable, adapter or filter rather than in DSP.

## NanoVNA mini-glossary

| Term | Meaning in this lab |
|---|---|
| `DUT` | Device under test: measured circuit or component. |
| `PORT1` / `CH0` | Source/reflection port; primary port for `S11`. |
| `PORT2` / `CH1` | Receiver port for the transmitted signal; used for `S21`. |
| `STIMULUS` | Sweep range setup: START, STOP, CENTER, SPAN. |
| `LOGMAG` | Magnitude in dB; convenient for filters and attenuators. |
| `PHASE` | S-parameter phase. |
| `SMITH` | Smith chart for impedance and matching. |
| `MARKER` | Frequency marker for reading the value at the operating point. |
| `TDR` | Time-domain reflectometry: cable length and discontinuity check from reflections. |

## Mandatory calibration

Before measurements, perform SOLT calibration in the exact frequency range and with the same cables that will be used later:

1. `RESET` the previous calibration.
2. `OPEN` at the end of the PORT1 cable.
3. `SHORT` at the end of the PORT1 cable.
4. `LOAD` 50 Ω at the end of the PORT1 cable.
5. `ISOLN`: usually keep PORT1 terminated with LOAD and leave PORT2 open or terminated if the kit allows it.
6. `THRU`: connect PORT1 and PORT2 through the same cables and adapter.
7. Press `DONE` and save the calibration to a slot.

Important: if the cable, adapter or frequency range is changed after calibration, the measurement is no longer strict. State this explicitly in the lab report.

## Procedure

1. Power on the NanoVNA and set the sweep range, for example 50 kHz to 900 MHz or a narrower range around the SDR operating frequency.
2. Perform SOLT calibration for the selected range and the actual measurement cable set.
3. Configure at least four traces: `S11 LOGMAG`, `S11 SMITH`, `S21 LOGMAG`, `S21 PHASE` or `DELAY`.
4. Place markers at the bench operating frequencies, for example 10 MHz, 70 MHz, 144/433 MHz or the current AD936x/RTL-SDR experiment frequency.
5. Measure the `Short`, `Open`, `Load` and `Thru` standards on the RF Demo Kit.
6. Measure the `33 Ohm`, `75 Ohm`, `ATT -3 dB` and `ATT -10 dB` circuits.
7. Measure the `BSF 6.5 MHz`, `BPF 10.7 MHz`, `LPF 400 MHz` and `HPF 500 MHz` filters.
8. Save a screenshot or CSV/Touchstone file for each measurement.
9. Fill the result table and decide which board elements are useful as educational references for SDR measurements.

## Extension A — cable loss and TDR

This extension is useful before long Block 11 loopback experiments.

1. Calibrate the NanoVNA over a wide range up to the useful upper frequency of the instrument.
2. Connect the cable under test as a two-port network and measure `S21 LOGMAG`.
3. Record cable loss at the SDR experiment frequencies.
4. Connect one cable end to PORT1 and leave the far end `OPEN` or terminate it with `SHORT`.
5. Open TDR in NanoVNA-Saver and estimate cable length/discontinuities.
6. In the report, state where cable loss can no longer be ignored in the link budget.

## Extension B — L/C/resonance in practice

This extension connects Block 10 with filters, matching and parasitic effects.

1. Connect a small capacitor or inductor to PORT1 through a short SMA adapter.
2. Enable `S11 SMITH` and `S11 Serial L` or `S11 Serial C` if the firmware/software supports it.
3. Sweep several ranges and check how the L/C estimate depends on frequency.
4. Build a simple LC tank and find resonance from `|Z|` or from the S21 peak/notch.
5. Conclude where the component is still close to ideal and where parasitic effects dominate.

## Report table

| Object | Range | Trace to inspect | Expected behavior | Measured result | Conclusion |
|---|---:|---|---|---|---|
| Load 50 Ω | near operating frequency | S11, VSWR | low reflection |  |  |
| Open | full range | Smith chart | chart edge |  |  |
| Short | full range | Smith chart | opposite chart edge |  |  |
| Thru | full range | S21 | near 0 dB plus cable loss |  |  |
| ATT -3 dB | operating frequency | S21 | about -3 dB |  |  |
| ATT -10 dB | operating frequency | S21 | about -10 dB |  |  |
| LPF 400 MHz | 50 kHz…900 MHz | S21 | roll-off after cutoff |  |  |
| HPF 500 MHz | 50 kHz…900 MHz | S21 | rejection below cutoff |  |  |
| Cable | SDR bench frequencies | S21, TDR | frequency-dependent loss, main reflection at the far end |  |  |
| LC tank | near resonance | S11 \/ |Z| or S21 | pronounced resonance |  |  |

## Check questions

1. Why should calibration be performed at the ends of the same cables used for the DUT measurement?
2. Why do `S11` and `S21` answer different engineering questions?
3. How can a bad adapter damage BER even when the signal level looks normal?
4. Why is a Smith-chart trace more informative than a single VSWR number?
5. What changes when the sweep range is narrowed around the SDR operating frequency?
6. Why does cable loss increase with frequency?
7. Why do inductors and capacitors stop being ideal at high frequencies?
8. How do you distinguish a matching problem from a DSP synchronization problem?

## Connection to Zynq-SDR

After this lab, the student should be able to validate the passive part of the RF path before BER/SNR experiments: cable, attenuator, filter, adapter and load. This is especially important for Blocks 6, 10 and 11, where an RF-path error can masquerade as a synchronization issue, CFO, ADC overload or FPGA logic defect.

## Artifacts

- NanoVNA screenshots;
- CSV/Touchstone measurement files;
- NanoVNA-Saver file or screenshot;
- filled result table;
- short conclusion on which RF Demo Kit elements are suitable for the educational bench;
- separate cable conclusion: whether the current cables can be used in the selected range without a noticeable correction.

## Further reading

- “Векторный анализатор NanoVNA для радиолюбителей” on Habr: a practical overview of calibration, NanoVNA-Saver, Smith chart, L/C measurements and TDR.
