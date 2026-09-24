# Lab 7.5 — CIC decimator for SDR receiver chains

This lab strengthens the DSP → fixed-point → FPGA bridge in the course. It is not a notebook exercise: it is a deterministic script-driven lab that generates figures and machine-readable metrics for CI.

## Goal

Model a CIC decimator as a hardware-oriented multirate block and measure:

- CIC frequency response;
- decimation behavior;
- blocker aliasing after rate change;
- passband droop;
- accumulator bit growth;
- fixed-point implications for RTL implementation.

## Why CIC matters

A CIC decimator is useful in SDR receiver chains because it can reduce a high input sample rate with adders, subtractors and delays instead of multipliers. This makes it a natural bridge from DSP theory to FPGA implementation.

Typical receiver placement:

```text
RF frontend / ADC stream -> CIC decimator -> compensation FIR -> channel filter -> demodulator
```

## Run command

From the repository root:

```bash
python blocks/block_07_tx_rx_chains/python/lab_7_5_cic_decimator.py
```

Or run the whole executable course smoke path:

```bash
python tools/run_all_labs.py
```

## Generated artifacts

| Artifact | Purpose |
|---|---|
| `docs/assets/lab75_cic_response.png` | CIC magnitude response and wanted-tone droop. |
| `docs/assets/lab75_cic_decimation_spectrum.png` | Input spectrum vs decimated output spectrum. |
| `docs/assets/lab75_cic_bit_growth.png` | Required accumulator width vs stage count. |
| `docs/assets/lab75_cic_metrics.json` | Sample rates, decimation factor, bit growth and measured peak metrics. |

## Engineering questions

1. Why is CIC attractive for high-rate decimation in FPGA logic?
2. What is the expected bit growth for `N` stages, decimation factor `R` and differential delay `M`?
3. What happens to a blocker after decimation?
4. Why is passband droop important for EVM/SNR-sensitive SDR chains?
5. Where would you place a compensation FIR after this CIC block?

## What to expect

Default CIC: `R = 8`, `N = 4` stages, `M = 1`, 16-bit input, 9.6 MS/s in, 1.2 MS/s out; wanted tone
220 kHz, blocker 1.85 MHz.

```text
CIC decimation: 9600000 -> 1200000 Hz
Recommended accumulator width: 28 bits
Wanted-tone droop: -1.913 dB
Measured output peak: 219982.910 Hz
```

- **Bit growth is `N * log2(R * M) = 4 * 3 = 12` bits**, so a 16-bit input needs 28-bit integrators.
  Integrators are allowed to wrap: with two's-complement arithmetic and enough width, the combs
  undo the wrap exactly.
- **Droop −1.913 dB at 220 kHz** follows from `|sin(pi*f*R/fs)/(R*sin(pi*f/fs))|^N`. Near the edge
  of the output band this passband tilt is what a compensation FIR after the CIC corrects.
- **The 1.85 MHz blocker aliases to −550 kHz** at the output (1.85 − 2 × 1.2 MHz), attenuated by
  about 53 dB by the CIC response. CIC nulls sit only at multiples of the output rate; between them
  the rejection is modest.

## Exercises

1. Change `stages` from 4 to 3 and to 5. How do the droop, the blocker rejection and the required
   accumulator width change?
2. Move the blocker to 2.4 MHz (a multiple of the output rate). What rejection do you get, and why?
3. Design the droop compensation: what gain in dB does a compensation FIR need at 220 kHz?

## Report checklist

- CIC parameters: `R`, `N`, `M`.
- Input and output sample rates.
- Recommended accumulator width.
- Passband droop at the wanted signal.
- Blocker alias frequency after decimation.
- Generated plots.
- Notes on fixed-point scaling and overflow behavior.

## Next RTL step

A future FPGA lab should map the same structure to:

```text
integrator stages -> decimation enable -> comb stages -> output valid
```

and compare RTL output against the Python fixed-point-style model.

See also: [CIC, fixed-point and FPGA bridge](../../cic-fixed-point-fpga-bridge.md).
