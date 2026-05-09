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
