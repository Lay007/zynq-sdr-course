# Contents — Block 10. KiCad and Basic Electronics

## Theory track
1. KiCad interface and project structure
2. reading and releasing schematics
3. power, decoupling, and wiring
4. breadboard work and simple generators
5. connectors, matching, and input protection
6. NanoVNA RF measurements: `S11`, `S21`, VSWR, and Smith chart
7. passive RF path checks: cables, loads, filters, and attenuators
8. documentation and BOM preparation

## Practical track
1. opening and reviewing an existing schematic
2. creating a simple helper-circuit schematic
3. preparing a breadboard implementation
4. performing SOLT calibration at the measurement-cable ends
5. measuring the RF Demo Kit with NanoVNA: reflection, transmission, VSWR, and Smith chart
6. characterizing a digital RF attenuator with `S21`
7. linking the results to SDR experiments, SNR/BER, and safe RF loopback

## Review and discussion questions
1. Which limitations or tradeoffs are central to this block?
2. How should the model, experiment, and analysis tools be linked in this block?
3. Which parameters must be documented for reproducible results?
4. Why does a good SNR value not guarantee a correct RF path?
5. How do `S11`/`S21` measurements help find a problem before running an AD9363 loopback?

## NanoVNA/RF labs
- Lab 10.5 — NanoVNA and RF Demo Kit: `S11`/`S21`, VSWR, and Smith chart.
- Lab 10.6 — Digital RF attenuator: step, range, and linearity check.

## Expected block outputs
- schematic or schematic fragment;
- bill of materials;
- photos of the assembly and measurement setup;
- `S11`/`S21`, VSWR, attenuation, and error tables;
- NanoVNA screenshots or CSV/Touchstone exports;
- report on the electrical and RF parts of the experiment.
