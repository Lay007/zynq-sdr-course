# Lab 11.3 — FPGA/RF Integration Checklist

## Goal

Prepare a checklist for moving from simulation/RTL to a safe RF experiment with an SDR board.

## Engineering question

> What must be checked before connecting FPGA-generated samples to the RF frontend and recording the result?

## Integration checklist

| Check | Why it matters |
|---|---|
| RTL testbench passes | avoids debugging hardware with broken logic |
| Fixed-point scaling documented | prevents clipping and level mismatch |
| AXI/stream interface verified | prevents sample loss |
| RF frequency plan written | avoids wrong spectral location |
| Gain/attenuation selected | protects receiver and improves reproducibility |
| Metadata template ready | makes IQ capture usable |
| FFT sanity check prepared | first validation after capture |
| Rollback plan defined | safe recovery from bad settings |

## Minimum evidence

- testbench PASS log;
- fixed-point error summary;
- RF settings table;
- attenuator/safety checklist;
- metadata JSON;
- first FFT screenshot or generated plot.

## Report checklist

- [ ] Attach RTL simulation result.
- [ ] Attach fixed-point scaling table.
- [ ] State RF settings.
- [ ] State attenuation and gain.
- [ ] Attach capture metadata.
- [ ] Include first FFT sanity check.
- [ ] State whether the integration is safe to continue.

## Engineering conclusion template

```text
The FPGA/RF integration is ready / not ready. The RTL status is ______, fixed-point scaling is ______,
RF plan is ______ and safety status is ______. The next action is ______.
```
