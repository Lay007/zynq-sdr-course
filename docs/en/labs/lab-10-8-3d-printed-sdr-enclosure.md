# Lab 10.8 — CAD and 3D Printing an Enclosure for ZynqSDR and TFT

**Status:** design assignment only. No enclosure has been modelled from verified dimensions, printed or bench-tested. Never use image-derived dimensions for fabrication.

## Goal

Design a serviceable enclosure for a compact Zynq-7020 + AD9361 instrument with a 2.8-inch TFT, the adapter PCB from [Lab 10.7](lab-10-7-spi-tft-interface-pcb.md), power and RF connectors. Follow **measurement → parametric CAD → fit prototypes → printing → assembly → thermal/RF validation**.

## Tools and measured input

Use calipers, documentation for the actual boards, a parametric CAD system such as **FreeCAD** or **OpenSCAD**, a slicer, and an available FDM printer. Determine its material capabilities, nozzle and actual print tolerances.

Create a **single dimension table**: PCB outline and thickness, mounting-hole centres, component/heatsink heights, SMA projection, power/USB/Ethernet/SD locations, cable bend clearance and the LCD active/touch area. Record a consistent mechanical datum for every coordinate. Do not invent dimensions from photos.

## Stage 1: Mechanical and RF requirements

1. Plan TFT on the front face, Zynq inside and access to power, USB/Ethernet, SD, SMA and any needed UART/JTAG or buttons.
2. Retain heatsink clearance and effective ventilation. A plastic housing does not substitute for a thermal design.
3. Provide cable strain relief and sufficient structural support around SMA connectors; attaching RF cables must not stress PCB solder joints through a thin printed wall.
4. Route digital LCD/SPI wiring away from sensitive RF inputs where practical. **A plastic enclosure is not an RF shield**; shielding claims require measurements.
5. Allow nondestructive access for repair, using appropriate standoffs, screws and removable panels.
6. Protect the LCD glass without compressing it or obstructing touch input.

## Stage 2: Parametric CAD

1. Model the base, LCD bezel/front panel, cover and any separate brackets as simple individually printable parts.
2. Parameterize board dimensions, mounting centres, standoff height, wall thickness, clearances and connector/heatsink openings.
3. Import a KiCad PCB **STEP** model or construct measured clearance envelopes; inspect collisions and assembly sequence.
4. Confirm the 320×240 landscape LCD is readable, touch remains accessible and the adapter PCB can be replaced.
5. Check mounting hardware, print orientation and whether supports can actually be removed.

## Stage 3: Test prints and iteration

1. Select material according to the task: PLA may be convenient for first-fit tests, PETG may be considered for subsequent iterations. Verify thermal suitability under **measured** conditions, not by material name alone.
2. Record printer, slicer, filament, layer height, infill, orientation and supports. These are process variables, **not universal prescribed settings**.
3. Print small fit coupons first: LCD bezel, standoffs and sample SMA/USB cut-outs.
4. Measure achieved fit and shrinkage; revise CAD before printing the full set.
5. Fit parts without stressing LCD glass, PCB, cables or connectors.

## Stage 4: Assembled instrument validation

- confirm RF, power, SD and service-port access with the housing assembled;
- measure/compare temperature and stable operation against the same open-bench workload, keeping existing cooling effective;
- test LCD, Linux/IIO and AD9361 while looking for changes in spectrum, noise floor or spurs when the display is active;
- record actual material use/print time, assembly photos, revision and failures.

An enclosure that overheats, obstructs connectors, strains boards or introduces problematic RF interference does **not** pass.

## Deliverables and evidence

- parametric CAD source (`FCStd` or OpenSCAD script), `STEP` for PCB fit review and `STL`/`3MF` for printing;
- measurement table, hardware/mounting plan and mechanical fit review;
- slicer settings and photos of test prints and complete assembly **after they exist**;
- thermal, accessibility and RF comparison log with revision and remaining issues.

## Integration

Use the manufactured enclosure and verified adapter PCB in [Lab 11.53](lab-11-53-local-spi-display.md). A finished CAD model can be assessed without a printer, but does **not** prove a printed/validated device.
