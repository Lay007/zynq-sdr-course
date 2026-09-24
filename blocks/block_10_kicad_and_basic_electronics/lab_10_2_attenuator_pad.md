# Lab 10.2 — Simple Attenuator Pad

## Goal

Design a simple attenuation stage for safe SDR/RF experiments and document why attenuation is required before connecting transmitters and receivers.

## Engineering question

> How do we reduce signal level safely before an SDR receiver or measurement input?

## Basic idea

An attenuator reduces signal amplitude and protects sensitive inputs from overload or damage. In SDR experiments, attenuation is mandatory for direct TX-to-RX cable loopback.

## Simple voltage divider

```text
Vout = Vin * R2 / (R1 + R2)
```

Attenuation in dB:

```text
A_dB = 20*log10(Vout/Vin)
```

## Example

| Parameter | Value |
|---|---:|
| R1 | 9 kOhm |
| R2 | 1 kOhm |
| Voltage ratio | 0.1 |
| Attenuation | -20 dB |

## Practical steps

1. Select desired attenuation.
2. Calculate voltage ratio.
3. Choose resistor values.
4. Check load impedance effect.
5. Draw schematic.
6. Measure input and output levels.
7. Document safe operating range.

## Safety notes

!!! warning "RF safety"
    A simple voltage divider is educational. Real RF 50-ohm attenuators should be used for RF cable loopback measurements when power levels or impedance matching matter.

## Matched 50-ohm pi pad: reference calculation

The voltage divider above is not matched: it only works into a high-impedance load. For a 50 Ohm RF path use a symmetric pi pad. Generate its ideal values and the loaded-voltage budget:

```bash
python blocks/block_10_kicad_and_basic_electronics/python/lab_10_2_rf_passives_design.py \
  --attenuation-db 10 --impedance-ohm 50 --input-dbm -10
```

Expected for 10 dB: `Pi series resistor: 71.151 ohm` and `Pi shunt resistors: 96.248 ohm each`. The JSON budget gives -10 dBm = 70.7 mV rms in 50 Ohm at the input and -20 dBm = 22.4 mV rms at the output. Use available resistor combinations, then measure the assembled network; the ideal calculation is not an RF safety certificate.

## Exercises

1. Put the 9 kOhm / 1 kOhm divider from the example in front of a 50 Ohm input. The load is in parallel with R2, so the attenuation becomes -45.6 dB instead of -20 dB, and the source sees about 9048 Ohm instead of 50 Ohm (almost total reflection). This is why RF pads are designed for the system impedance.
2. Build the 10 dB pad from standard values. Calculated: 68 / 100 Ohm gives 9.66 dB and 50.3 Ohm input (return loss 49.6 dB); 75 / 100 Ohm gives 10.24 dB and 52.0 Ohm (34.2 dB); 68 / 91 Ohm gives 9.85 dB and 47.7 Ohm (32.6 dB). Which would you choose, and why is the input match often more important than 0.3 dB of attenuation?
3. Feed +10 dBm (10 mW) into the ideal 10 dB pad. The input shunt resistor dissipates 5.19 mW, the series resistor 3.29 mW, the output shunt 0.52 mW, and 1.00 mW reaches the load. Which resistor sets the power rating, and what rating would you need for a +30 dBm transmitter?

## Report checklist

- [ ] State desired attenuation.
- [ ] Calculate resistor values.
- [ ] Calculate expected voltage ratio.
- [ ] Convert attenuation to dB.
- [ ] Explain load impedance limitations.
- [ ] Explain whether this circuit is safe for the intended SDR experiment.

## Engineering conclusion template

```text
The attenuator uses R1 = ____ and R2 = ____, giving a voltage ratio of ____ and attenuation of ____ dB.
It is suitable / not suitable for the planned SDR experiment because ______.
```
