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
| AXI-Lite register map verified | prevents PS-side control mistakes before RF bring-up |
| AXI/stream interface verified | prevents sample loss |
| RF frequency plan written | avoids wrong spectral location |
| Gain/attenuation selected | protects receiver and improves reproducibility |
| No-attenuator fallback is explicitly limited | keeps a first OTA trial short, low-power and non-quantitative |
| Metadata template ready | makes IQ capture usable |
| FFT sanity check prepared | first validation after capture |
| Rollback plan defined | safe recovery from bad settings |

## Minimum evidence

- testbench PASS log;
- fixed-point error summary;
- register map and one successful `ID` register readback;
- RF settings table;
- antenna spacing and minimum TX gain note for any no-attenuator OTA trial;
- attenuator/safety checklist;
- metadata JSON;
- first FFT screenshot or generated plot.

## First discovery-burst profile

For the first no-attenuator handoff to AD9363, use a deliberately conservative profile:

| Item | First setting |
|---|---|
| Burst type | one short deterministic BPSK frame |
| TX gain | minimum available setting |
| RX gain | low manual gain |
| AGC | disabled |
| RF goal | detect the burst and confirm no overload |
| Success signal | visible burst at the expected frequency and no obvious clipping/splatter |

## Repository handoff path

Use the repository in this order:

1. Verify the AXI-Lite register contract with Lab 5.11 and confirm one `ID` readback plus one simulated burst.
2. Probe the board with `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py`.
3. Freeze the first RF settings using the Lab 6.3 manual-gain checklist.
4. Launch one deterministic burst from the PS through the AXI-Lite wrapper.
5. Observe the burst either with the Zynq RX chain or with RTL-SDR as an external monitor.

This separates three concerns cleanly: PS control, AD9363 RF configuration, and waveform visibility.

## Report checklist

- [ ] Attach RTL simulation result.
- [ ] Attach fixed-point scaling table.
- [ ] Attach register map or PS control summary.
- [ ] State RF settings.
- [ ] State attenuation and gain.
- [ ] If no attenuator is available, state that the first OTA trial is discovery-only, short-burst and minimum-power.
- [ ] Attach capture metadata.
- [ ] Include first FFT sanity check.
- [ ] State whether the integration is safe to continue.

## Engineering conclusion template

```text
The FPGA/RF integration is ready / not ready. The RTL status is ______, fixed-point scaling is ______,
RF plan is ______ and safety status is ______. The next action is ______.
```
