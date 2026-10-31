# Lab 10.7 — Design a ZynqSDR-to-SPI-TFT Interface PCB in KiCad

**Status:** design brief only. The actual Zynq pin mapping, spare GPIO availability, logic voltages, TFT controller and photographed wiring are not yet validated. No PCB has been manufactured or tested.

## Goal

Replace the temporary wire harness between a Zynq-7020 + AD9361 and a 2.8-inch 240×320 SPI TFT with a reproducible adapter board. Follow **requirements → schematic → PCB → manufacturing files → assembly → verification**. The resulting board must not interfere with AD9361 control and must fit the enclosure designed in [Lab 10.8](lab-10-8-3d-printed-sdr-enclosure.md).

## Establish the inputs

Record from **the actual hardware**, not a similar board:
- pinout and bank voltages of accessible Zynq PS/PL GPIOs; their Linux/FPGA routing;
- TFT connector pin order: VCC, GND, LCD_CS, DC, RESET, SCK, SDI/MOSI and LED; optional MISO, TOUCH_CS, TOUCH_IRQ and SD_CS;
- LCD power and I/O requirements, backlight current and intended driving circuit;
- mounting-hole centres, board outline, connectors, height and enclosure clearances;
- proposed connectors and SPI speed.

**SPI0 currently controls the AD9361.** Select and validate a separate interface (verified GPIO/software SPI or explicitly routed SPI1/EMIO/PL); never guess a spare header pin.

## Stage 1: Requirements and schematic

1. Create a traceable signal table: TFT signal → translator/buffer pin → Zynq connector pin → bank voltage → direction → evidence.
2. Decide whether logic level shifting is required. If so, select a device compatible with the intended **push-pull SPI** directions and clock; do not assume a generic MOSFET-style bidirectional breakout meets the timing.
3. Add proper grounds, local supply decoupling, power sequencing and prevention of back-powering. Size a backlight driver from actual current requirements; do not power the backlight directly from GPIO without justification.
4. Document LCD reset and power-up behaviour.
5. Expose test points for GND, supplies, CS, SCK, MOSI, DC and RESET. Optional series damping requires a measured rationale.
6. Complete annotated KiCad schematic and **ERC** review.

## Stage 2: PCB and manufacturing data

1. Exchange measured mounting dimensions, connector heights and keep-out zones with the CAD enclosure in Lab 10.8.
2. For a basic adapter, evaluate a two-layer board with a consistent GND reference, short SPI traces and decoupling at each active component.
3. Check power/backlight current, track width, clearances, connector orientation, pin 1 and accessible mounting screws.
4. Run **DRC**, verify the pin-to-pin netlist against the signal table, then review fabrication output with an independent Gerber viewer.
5. Export KiCad project, schematic, PCB, Gerber, drill, BOM and any needed position/assembly files.

## Stage 3: Assembly and hardware evidence

1. Before ordering, verify the intended GPIOs, logic levels and LCD test pattern with the documented safe prototype from [Lab 11.53](lab-11-53-local-spi-display.md). Postpone fabrication if critical assumptions are unknown.
2. With power disconnected, inspect soldering and check for shorts on assembled PCB.
3. Power up with suitable current limiting; check supply and clock levels, SPI timing and display updates if measurement equipment is available.
4. Confirm AD9361 and Linux/IIO initialization still work unchanged.
5. Compare wiring harness and PCB for repeatability, connection count, reliability and mechanical fit.

## Deliverables and acceptance

Provide `*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb`, traceable pin table, measured voltage record, ERC/DRC results, manufacturing package, BOM, documented mechanical interface and **only after fabrication** actual photos and test results.

A checked design is not a tested board. Claim a successful electrical build only after measured voltages, working LCD patterns and unchanged AD9361/IIO operation.

## Questions

1. Why is a physical header pin not automatically a usable Linux GPIO?
2. How do LCD supply power and I/O logic levels differ?
3. Why must PCB connector placement be coordinated with mechanical CAD before manufacture?
