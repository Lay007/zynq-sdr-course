# Lab 6.7 — Zero-IF artifacts: DC component, mirror and tune offset

## Goal

Understand why a real zero-IF SDR can show artifacts that are absent from an ideal DSP model.

The lab is performed first with a synthetic IQ signal. The same analysis pattern can later be applied to an AD9363/Zynq recording.

## What we model

| Artifact | Simple model |
|---|---|
| DC component | add a constant complex offset `I0 + jQ0` |
| IQ amplitude imbalance | multiply I and Q by different gains |
| IQ phase imbalance | add a small phase error between I and Q |
| Tune offset | shift the useful tone away from 0 Hz |

## Procedure

1. Generate a complex baseband tone.
2. Plot the ideal spectrum.
3. Add a DC component and plot the spectrum again.
4. Add IQ imbalance and identify the mirror component.
5. Shift the tone away from the spectrum center.
6. Compare what becomes easier to observe after tune offset.
7. Write a short engineering conclusion.

## Expected observations

- The DC component appears near 0 Hz.
- IQ imbalance creates a mirror component around the center.
- Tune offset does not fix the RF frontend, but it helps keep the useful signal away from the central artifact.
- Without metadata, repeated measurements cannot be compared honestly.

## Review questions

1. Why does the spectrum center become a special region in a zero-IF architecture?
2. How is a DC component different from a useful tone?
3. Why does IQ imbalance create a mirror component?
4. Which manifest fields are needed before a real AD9363 recording?
5. Why should gain and bandwidth settings be checked before judging BER/EVM?

## Mini report

A minimal report should include:

- tone frequency in normalized units or Hz;
- sample rate;
- DC component parameters;
- IQ imbalance parameters;
- two spectra: before and after tune offset;
- short conclusion about which artifact harms the measurement most.

## Hardware connection

When a real AD9363 recording is available, use the same analysis template:

```text
manifest -> spectrum -> artifact identification -> metric -> limitation -> next action
```

This lab prepares the student for Block 9 recording labs and Block 11 integrated SDR bring-up.
