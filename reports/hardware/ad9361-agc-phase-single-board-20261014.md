# AD9361 gain-control phase step on one board (#58), 2026-10-14

The two-board measurement ([`ad9361-agc-transient-20261014.md`](ad9361-agc-transient-20261014.md))
could not resolve the slow_attack phase step: over the 15 ms it takes to settle, the two boards'
oscillators wander against each other by 5-14 degrees RMS. Here one board transmits and receives,
so both LOs come from the same reference and that wander is gone.

Bench: board B TX1 -> variable attenuator (0 dB) -> 30 dB -> splitter -> board B RX1, both LOs at
915 MHz, 3.84 MS/s. Board B transmits a 300 kHz tone from its DAC DDS, set up by registers
because B has no DAC driver. It records 2,000,000 samples (0.52 s) in one `iio_readdev` buffer
while it steps its own TX gain between -30 and -10 dB. Script:
`blocks/block_11_integrated_sdr_project/python/single_board_agc_step_transient.py`. Raw results:
[`ad9361-agc-phase-single-board-20261014.json`](ad9361-agc-phase-single-board-20261014.json);
three repeats per case.

## Method

- The tone frequency is the FFT peak of the whole capture. It came out at exactly -300 000.00 Hz
  (within 0.02 Hz) in every run: TX and RX share the reference.
- The derotated tone is averaged over 1024-sample blocks.
- The block phases are fitted on a stable region before the step (60-20 ms before) and one after
  it (26-52 ms after), with one common slope and a jump at the step. The jump is the phase step.
- The excursion is the largest deviation of 256-sample block phases from that fit during the
  transient.
- A first version unwrapped the per-sample phase, as the two-board script does. Where the tone is
  weak (after a drop, before the gain control catches up) it slipped whole turns, so its results
  are not used.
- Floor: the same capture with no step.

## Results

| Case | RX gain before -> after | settling to 1 dB | phase step | largest excursion |
|---|---|---|---|---|
| no step (floor), manual 50 dB | 50 -> 50 | - | -0.7 .. +0.4° | ≤ 1.1° |
| TX step up 20 dB, manual 50 dB | 50 -> 50 | < 0.04 ms | +0.4 .. +0.5° | ≤ 0.6° |
| TX step down 20 dB, manual 50 dB | 50 -> 50 | < 0.04 ms | -0.3 .. -0.6° | ≤ 1.5° |
| up, slow_attack | 73 -> 60 | 8.2-8.6 ms | **-6.4 .. -6.7°** | 6.5-6.7° |
| down, slow_attack | 60 -> 73 | 6.2-6.7 ms | **+6.3 .. +6.7°** | 6.7-7.2° |
| up, fast_attack | 73 -> 60 (twice), 73 -> 65 | 0.04-0.05 ms | -6.4, -6.8; -5.5° | 5.7-6.8° |
| down, fast_attack | 60, 61, 64 -> 73 | 0.13-0.72 ms | +6.3, +6.8; +5.5° | 6.2-7.1° |

## What it means

- **Measured:**
  - The TX gain step itself moves the phase by about 0.5°, at the floor of the method.
  - Both gain control modes rotate the received signal by about 6.5° when the gain moves between
    73 and 60 dB, and by about 5.5° for 73 <-> 64-65 dB.
  - The rotation follows the gain change, not the mode. The modes differ only in how long it
    takes: 6-9 ms for slow_attack, 0.04-0.7 ms for fast_attack.
  - The excursion equals the step (within a degree): the phase moves monotonically to its new
    value without overshoot.
- **For a receiver:** a 6.5° step is small for QPSK (45° margin), but a carrier loop sees it as a
  phase error to track. Under slow_attack it is spread over 6-9 ms, as several gain-table steps;
  under fast_attack it arrives within a fraction of a millisecond.
- **Not measured here:**
  - steps larger than 20 dB at the input;
  - other carrier frequencies;
  - the phase step per gain-table index. The readbacks give only the gains before and after.
