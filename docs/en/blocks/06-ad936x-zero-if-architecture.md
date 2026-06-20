# AD936x zero-IF architecture

This page connects the IQ-signal theory from the early course blocks with a real AD936x-class RF frontend.

The key idea is that AD936x devices use a zero-IF / direct-conversion architecture. The RF signal is translated directly into complex baseband, so effects that look ideal in a DSP model become visible around the center of the measured spectrum.

## Simplified RX path

```text
RF input
  -> input network and matching
  -> LNA / gain stages
  -> quadrature mixer
  -> analog low-pass filtering
  -> ADC
  -> digital filtering / decimation
  -> I/Q samples
  -> FPGA / PS / host analysis
```

## Simplified TX path

```text
I/Q samples
  -> interpolation / digital filtering
  -> DAC
  -> analog filtering
  -> quadrature modulator
  -> gain stages
  -> RF output
```

## Why the spectrum center matters

In an ideal DSP model, zero frequency in complex baseband is just another frequency bin. In a real zero-IF path, several artifacts can appear close to it:

| Effect | What appears in the spectrum | Practical meaning |
|---|---|---|
| DC component | spike or raised floor near 0 Hz | can hide a weak centered signal |
| LO leakage | residual carrier or tone close to the center | especially visible in TX or loopback work |
| IQ imbalance | mirror component | degrades image rejection and EVM |
| Gain / bandwidth mismatch | level and spectrum-shape changes | makes model-to-measurement comparison harder |

## Tune offset

A practical first-lab trick is to avoid placing the useful signal exactly at the baseband center. A small tuning or digital-frequency offset can move the signal away from the DC component.

```text
harder first observation:
useful signal near 0 Hz + DC component

easier first observation:
useful signal shifted away from 0 Hz
```

This does not replace calibration, but it makes early measurements easier to interpret.

## Course mapping

| Block | Where it is used |
|---|---|
| Block 2 | complex baseband, I/Q and mirrored spectrum |
| Block 3 | digital mixing and spectrum translation |
| Block 6 | AD9363 settings, gain staging and RF frontend behavior |
| Block 8 | CFO, phase offset, timing and EVM |
| Block 9 | IQ recording, metadata and replay |
| Block 11 | Zynq/AD936x bring-up and measured reports |

## Student outcomes

After this topic, a student should be able to:

1. explain why a zero-IF SDR produces complex I/Q samples;
2. distinguish a useful tone from a DC component;
3. recognize a mirror component caused by IQ imbalance;
4. record frequency, sample rate, bandwidth and gain in a manifest;
5. avoid judging the DSP model before checking RF/frontend settings.

## Mini exercise

For a synthetic IQ sequence:

1. generate a complex tone;
2. add a constant I/Q component;
3. add a simple amplitude mismatch between I and Q;
4. plot the spectrum;
5. shift the useful tone away from the center;
6. explain which artifacts disappeared and which only became easier to observe.
