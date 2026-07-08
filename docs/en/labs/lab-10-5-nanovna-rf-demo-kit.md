# Lab 10.5 — NanoVNA and RF Demo Kit: S11/S21, VSWR and Smith Chart

## Goal

Learn to use a NanoVNA-H4 and an RF Demo Kit as a safe bridge between RF theory and SDR bench measurements. The lab helps the student see not only a spectrum in SDR software, but also real matching, reflection, transmission and passive-network frequency response.

## Equipment

- NanoVNA-H4 or a compatible VNA.
- RF Demo Kit for NanoVNA-F or a similar educational board with SMA/IPX ports.
- SOLT calibration kit: Short, Open, Load, Thru.
- SMA/IPX adapters and short cables.
- 3–10 dB attenuator for input protection when the connection is uncertain.

## Safety

A NanoVNA is a small-signal instrument. Do not connect it to a Zynq/AD936x transmitter output, signal generator or amplifier without a power budget and a protective attenuator. Before connecting an unknown circuit, check that there is no DC voltage and no external RF source on the port.

## Short theory

A VNA measures complex S-parameters. For this lab two quantities are enough:

- `S11` — input reflection. It is used to estimate matching, VSWR and the point on the Smith chart.
- `S21` — forward transmission through a two-port network. It is used to measure the frequency response of a filter, cable, attenuator or thru path.

The SDR connection is direct: poor matching and unexpected `S21` notches may look like poor SNR, although the root cause is in the RF path, cable, adapter or filter rather than in DSP.

## Procedure

1. Power on the NanoVNA and set the sweep range, for example 50 kHz to 900 MHz or a narrower range around the SDR operating frequency.
2. Perform SOLT calibration for the selected range and the actual measurement cable set.
3. Measure the `Short`, `Open`, `Load` and `Thru` standards on the RF Demo Kit.
4. Measure the `33 Ohm`, `75 Ohm`, `ATT -3 dB` and `ATT -10 dB` circuits.
5. Measure the `BSF 6.5 MHz`, `BPF 10.7 MHz`, `LPF 400 MHz` and `HPF 500 MHz` filters.
6. Save a screenshot or CSV/Touchstone file for each measurement.
7. Fill the result table and decide which board elements are useful as educational references for SDR measurements.

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

## Check questions

1. Why should calibration be performed at the ends of the same cables used for the DUT measurement?
2. Why do `S11` and `S21` answer different engineering questions?
3. How can a bad adapter damage BER even when the signal level looks normal?
4. Why is a Smith-chart trace more informative than a single VSWR number?
5. What changes when the sweep range is narrowed around the SDR operating frequency?

## Connection to Zynq-SDR

After this lab, the student should be able to validate the passive part of the RF path before BER/SNR experiments: cable, attenuator, filter, adapter and load. This is especially important for Blocks 6, 10 and 11, where an RF-path error can masquerade as a synchronization issue, CFO, ADC overload or FPGA logic defect.

## Artifacts

- NanoVNA screenshots;
- CSV/Touchstone measurement files;
- filled result table;
- short conclusion on which RF Demo Kit elements are suitable for the educational bench.
