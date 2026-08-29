# Student path

This page is the shortest reliable learning route through the course.

It is written for a student who wants to understand the engineering chain without getting lost in the full documentation tree.

## Stage 1. Understand the whole system first

Open these pages in order:

1. [Model → FPGA → RF → Measurement](model-to-measurement.md)
2. [Course status](status.md)
3. [Visual course map](course-map.md)

Goal: understand that the course is not just theory. Every important model decision should eventually connect to hardware, IQ capture, and measurable evidence.

## Stage 2. Build the DSP foundation

Use this track next:

1. [DSP foundation track](dsp-foundation-track.md)
2. Block 03 labs from [Lab index](lab-index.md)
3. [Reproducibility guide](reproducibility-guide.md)

Expected output:

- at least one generated plot;
- one short explanation of what the plot proves;
- one reproducible command path.

## Stage 3. Move into fixed-point and HDL

Open:

1. [DSP → FPGA Bridge](dsp-to-fpga.md)
2. [CIC fixed-point FPGA bridge](cic-fixed-point-fpga-bridge.md)
3. Block 04 and Block 05 labs through Lab 5.11

Expected output:

- one fixed-point note with assumptions;
- one HDL or simulation result;
- one comparison between model behavior and implementation behavior.

## Stage 4. Understand the Zynq PS/PL boundary

Do this **before** treating the board as a black-box SDR appliance:

1. [Zynq: where PS ends and PL begins](zynq-ps-pl-architecture.md)
2. [Lab 5.12 — PS↔PL message mailbox](en/labs/lab-5-12-zynq-ps-pl-mailbox.md)
3. Run the no-board console contract:

```bash
python tools/zynq_message_console.py --mock demo "Hello Zynq" --sequence 17
```

Expected output:

- explain which tasks belong in ARM/PS and which belong in FPGA/PL;
- explain the difference between AXI4-Lite, AXI4-Stream and DMA;
- show how four bytes become one little-endian 32-bit register word;
- understand `start`, `valid`, `ack` and a stable RX mailbox before adding RF.

The hardware form of this stage is intentionally simple:

```text
PS software → AXI-Lite mailbox → PL echo → AXI-Lite mailbox → PS console
```

## Stage 5. Touch RF hardware only with discipline

Before any real RF experiment, read:

1. [Hardware checklist](hardware-checklist.md)
2. [RF safety guide](rf-safety.md)
3. [IQ recording metadata guide](iq-recording-metadata.md)

Expected output:

- documented frequency plan;
- receiver and attenuation notes;
- one IQ capture or at least one synthetic replay package.

## Stage 6. Finish with an end-to-end story

Use one of these pages:

1. [End-to-end SDR demo roadmap](end-to-end-demo.md)
2. [End-to-end tone demo report](end-to-end-tone-demo-report.md)
3. [Course demo dashboard](demo-dashboard.md)

The preferred educational capstone is now a user-visible message path:

```text
Board A console
→ PS
→ PL QPSK modem
→ RF
→ PL QPSK receiver
→ PS
→ Board B console
```

Expected output:

- one end-to-end experiment summary;
- one figure or metric;
- one conclusion that connects model, implementation and measurement;
- for the two-board message demo, the transmitted text and the received text plus packet metadata.

## If you only have 10 minutes

Open just these pages:

1. [Model → FPGA → RF → Measurement](model-to-measurement.md)
2. [Zynq: where PS ends and PL begins](zynq-ps-pl-architecture.md)
3. [Course status](status.md)
4. [Demo dashboard](demo-dashboard.md)

That path gives the fastest high-level understanding of both the DSP workflow and the Zynq system architecture behind it.
