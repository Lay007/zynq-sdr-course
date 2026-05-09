# Lab 10.3 — RF Measurement Safety Checklist

## Goal

Create a practical safety checklist for connecting SDR boards, receivers, attenuators, cables and simple electronics during RF experiments.

## Engineering question

> What must be checked before connecting a transmitter, receiver and measurement chain?

## Safety checklist

| Check | Why it matters |
|---|---|
| External attenuation installed | protects receiver input |
| TX gain starts low | avoids overload and damage |
| RX gain is manual | improves reproducibility |
| Frequency plan documented | avoids transmitting/receiving in wrong band |
| Cable and connectors inspected | avoids intermittent measurements |
| 50-ohm assumptions checked | avoids incorrect level interpretation |
| DC path considered | protects RF inputs from unwanted DC |
| Spectrum monitored first | detects overload and spurs |

## First-connection procedure

1. Turn TX off.
2. Insert attenuator.
3. Set TX gain to minimum.
4. Set RX gain to low/manual.
5. Confirm frequency plan.
6. Enable RX and observe noise floor.
7. Enable TX at low level.
8. Increase level only if spectrum remains clean.
9. Record metadata and measurement conditions.

## Overload symptoms

| Symptom | Possible cause |
|---|---|
| Flat spectral top | ADC or RF overload |
| Many harmonics | nonlinear stage or clipping |
| Noise floor rises with signal | gain compression or AGC |
| Signal level stops changing | saturation |
| Receiver becomes unstable | excessive input or poor grounding |

## Report checklist

- [ ] Draw connection diagram.
- [ ] State attenuation value.
- [ ] State TX/RX gain.
- [ ] State frequency plan.
- [ ] State load/cable assumptions.
- [ ] Include spectrum screenshot or generated FFT.
- [ ] Conclude whether the setup was safe and reproducible.

## Engineering conclusion template

```text
The measurement chain used ____ dB external attenuation and TX/RX gain settings ____.
No overload / overload was observed. The setup is safe / unsafe for further experiments because ______.
```
