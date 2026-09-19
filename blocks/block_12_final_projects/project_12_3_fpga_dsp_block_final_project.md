# Project 12.3 — FPGA DSP Block Final Project

## Goal

Implement or extend one DSP block for FPGA use, verify it with a self-checking testbench and compare it against a reference model.

## Why this project matters

Anyone can write a filter that simulates. The engineering content of an FPGA block is in the
decisions a simulation hides: how many bits each wire needs, where rounding and saturation
happen, how many clocks the result is late, what happens when the downstream block is not
ready, and whether the design still meets timing when routed. This project asks you to make
those decisions explicitly, defend them with numbers, and prove that the RTL does exactly what
the model says.

## Candidate blocks

| Block | Suggested evidence |
|---|---|
| FIR filter | coefficient table, fixed-point error, RTL PASS |
| NCO mixer | phase accumulator settings, spectrum, RTL PASS |
| AXI-Stream wrapper | backpressure test, latency, handshake evidence |
| Decimator | anti-aliasing response, output-rate verification |

Pick a block that is small enough to finish and verify. A modest block with a complete evidence
package beats an ambitious block that only partly works.

## Minimum deliverables

- reference model;
- fixed-point specification;
- RTL module or RTL extension;
- self-checking testbench;
- waveform or PASS log;
- error analysis;
- final report.

## Success criteria

| Criterion | Target |
|---|---:|
| Testbench status | PASS |
| Max error | defined by student |
| Latency documented | required |
| Fixed-point format documented | required |

Fix the error tolerance in the proposal **before** simulating. "Bit-exact against the fixed-point
model" is a stronger and more useful target than "close to the float model"; state which one
you are claiming and why.

## Freeze the proposal

| Field | Required content |
|---|---|
| block and purpose | what it does and where it sits in a chain |
| reference model | Python/MATLAB, float and fixed-point, with the exact arithmetic rules |
| number formats | input, coefficient, product, accumulator, output; rounding and saturation rule |
| interface | ports, valid/ready or AXI-Stream semantics, reset behaviour |
| latency and throughput | clocks of delay, samples per clock |
| acceptance gate | numeric tolerance and the test vectors that must pass |
| stop rule | when the block is finished |

## Verification gates

1. **G0 — contract:** the proposal, number formats and interface are written down and committed.
2. **G1 — reference:** the fixed-point model matches the float model within the stated tolerance on
   impulse, constant, tone and random inputs.
3. **G2 — vectors:** deterministic input and expected-output vector files are generated from the
   model, not written by hand.
4. **G3 — RTL:** the self-checking testbench compares every output sample with the expected
   vector and ends with an unambiguous `PASS` line; a deliberately broken run fails.
5. **G4 — corner cases:** saturation, reset in the middle of a stream, and (for streaming blocks)
   downstream backpressure each have a directed test.
6. **G5 — implementation evidence:** utilization, latency and, if the tool is available, routed
   timing are reported; if Vivado is not available to you, say so instead of estimating.
7. **G6 — reproduction:** a clean checkout runs the documented commands and gets the same result.

## Design pitfalls to test for explicitly

| Pitfall | Symptom | Test that catches it |
|---|---|---|
| accumulator too narrow | wrap-around on a full-scale input | full-scale sinusoid and step inputs |
| rounding mismatch | model and RTL differ by 1 LSB on some samples | random vectors compared bit-exactly |
| latency off by one | outputs shifted by one sample | impulse input; compare against expected position |
| output not held under backpressure | lost or duplicated samples | testbench that deasserts `ready` at awkward moments |
| reset ignored mid-stream | stale data after reset | reset in the middle of a burst |
| testbench that cannot fail | always prints PASS | inject a wrong expected value and confirm FAIL |

## Evidence package

```text
project_12_3/
├── proposal.md
├── model.py               # float + fixed-point reference
├── generate_vectors.py    # writes input/expected vectors deterministically
├── rtl/
├── tb/
├── vectors/
├── reports/               # normalized utilization / timing summaries
├── metrics.json
└── report.md
```

## CI-safe starting point

The course already contains a canonical HDL smoke run. From the repository root:

```bash
python tools/run_block5_hdl_smoke.py --no-generate
```

Read one finished block end to end before designing yours: the 4-tap FIR
([Lab 5.2](/zynq-sdr-course/en/labs/lab-5-2-fir-rtl-mapping/)), the AXI-Stream wrapper
([Lab 5.4](/zynq-sdr-course/en/labs/lab-5-4-axis-wrapper/)), the 65-tap RRC FIR
([Lab 5.6](/zynq-sdr-course/en/labs/lab-5-6-bpsk-rrc-tx-fir-rtl/)) and the float/fixed/RTL comparison
([Lab 5.5](/zynq-sdr-course/en/labs/lab-5-5-float-fixed-rtl-comparison/)). Do not put a Vivado
rebuild in the only reproduction path: commit normalized utilization and timing reports so a
reviewer without the licensed tool can still read your result.

## Final acceptance checklist

- [ ] Proposal, number formats and tolerance predate the final simulation.
- [ ] The RTL is compared against the model on committed, generated vectors.
- [ ] The testbench fails on a deliberately wrong expectation.
- [ ] Saturation, reset and (if streaming) backpressure each have a directed test.
- [ ] Latency and the fixed-point formats are documented.
- [ ] Utilization and timing are reported, or their absence is stated.
- [ ] A clean-checkout command reproduces the PASS.
- [ ] The conclusion says whether the block **is** or **is not** ready for integration, and why.

Grade with the [final-project grading rubric](/zynq-sdr-course/final-project-grading-rubric/).

## Report conclusion template

```text
The FPGA DSP block implements ______. The RTL testbench status is ____ and max error is ____.
The block is / is not ready for integration because ______.
```
