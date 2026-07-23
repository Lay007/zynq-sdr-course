# Lab 11.41 — The DC blocker was following the data

## Goal

Find why the receiver deterministically produces a wrong bit at payload index 189, when every
measurement of the delivered signal at that symbol says it is healthy — and fix it.

Prerequisites: [Lab 11.35](lab_11_35_paired_timing_ab.md), which localised the failure and proved
the reported index is correct.

## Where the previous five labs went wrong

The state at the end of Lab 11.35 was a genuine paradox. The decoded-bit readout had established
that the chip really does get payload bit 189 wrong — 10 of 10 flagged frames disagree with the ROM
at exactly frame bit 213 and nowhere else. Yet the capture tap said the decision margin at that
symbol was healthy, the offline model said the transmitted waveform never makes that bit fail first,
and the failure was invariant to start offset and to carrier.

The resolution is not in any of those measurements. It is in what they measured.

> The capture tap records `core_rx` — the **input** of the receive chain. The DC blocker is the
> first block after it. Every "the signal there is healthy" result was blind to the DC blocker by
> construction, not by accident.

The tap was built to answer *what does the AD9361 deliver*. It was then used, for five labs, to
answer *what does the decision stage see*. Those are different questions, and the difference between
them is exactly the block that was causing the failure.

## Why the DC blocker fits every fact

Once the suspect is named, the facts that had no other explanation all follow at once:

| Observation | Why the DC blocker explains it |
|---|---|
| invariant to carrier phase and frequency (910/915/920 MHz alike) | the filter is linear and identical on I and Q, so `dcb(x·e^{jθ}) = dcb(x)·e^{jθ}` — its distortion rotates **with** the signal |
| fabric loopback decodes the same frame at BER 0 | `gp_ctrl[9]` enables the blocker only on the RF path; the loopback runs with it off |
| capture tap shows a healthy margin at symbol 106 | it is healthy there — the damage happens downstream |
| deterministic, frame after frame | the distortion is a function of the frame data, which is fixed |
| invariant to `start_offset` | the transmitter replays cyclically, so the estimate is in cyclic steady state |

The mechanism is the time constant. The blocker is a leaky integrator whose accumulator holds
`mean << K`; the original fixed `K=6` gives tau = 64 samples = 8 symbols at SPS=8. That is short
enough to follow the modulation: a run of identical symbols on one axis drags the estimate toward
that run, and the sample that loses the most is the one at the **end** of the run.

Symbol 106 is the last of a four-symbol Q run immediately before a sign change.

## Measure it

`dc_blocker_margin.py` replays the RTL bit-exactly over the real frame and ranks every payload
decision by margin.

```bash
cd blocks/block_11_integrated_sdr_project/python
python dc_blocker_margin.py
```

| Configuration | margin at bit 189 | rank in frame |
|---|---|---|
| no blocker, DC-free input (the fabric loopback, and the ideal) | +0.976 | 17 of 256 |
| **fixed K=6 — the configuration that fails** | **+0.336** | **1 of 256** |
| running average, K_MAX=10 — the current module | +0.913 | 23 of 256 |

The blocker removes two thirds of the margin and turns an unremarkable 17th-ranked decision into the
**weakest of all 256**, at 0.336 against a median of 0.99.

### The check that makes this a cause rather than a story

Four earlier explanations were also plausible. The test that distinguishes them is whether the model
predicts the **whole** live histogram, not just bit 189. Over the campaign the single-bit errors fell
at three indices and no others:

| payload index | live frames | rank predicted by the model |
|---|---|---|
| 189 | 37 | **1** of 256 |
| 2 | 2 | **3** of 256 |
| 173 | 1 | **23** of 256 |

All three sit in the predicted weak tail, ordered by how often they failed. Nothing else about the
frame distinguishes those three bits.

The module's own comment had carried the warning all along — *"K=4 still tracks the modulation and
errs; K>=6 is clean"*. "Clean" had been validated on one high-SNR capture, where a 0.336 margin still
decodes at zero errors. The two-board link had less to spare. The comment described the failure mode
exactly; what was wrong was the assumption that 6 was far from the edge.

## The first fix is wrong, and worth understanding

The blocker is reset every frame (`qpsk_rx_bit_recovery_chain` wires `.rst(rst || frame_start)`), so
it must converge from zero inside each burst. That rules out simply making K larger. The obvious
answer is the pattern `qpsk_costas` already uses: acquire fast, then gear down — `K_ACQ` until
converged, then `K_TRACK`.

It passes a synthetic bench and restores bit 189. It also regresses
`tb_qpsk_timing_recovery_retained`, a bench built on a real two-board capture.

The reason is worth keeping. In that capture the true DC is tiny — the mean over all 2600 samples is
4.5+1.1j against an rms of 377. But the mean of the **first 192 samples** is 79+44j. Over a short
window the modulation's own local imbalance is the dominant term, so the acquisition window measures
the wrong DC — and gearing down then freezes that error into a slowly-decaying offset across the
whole frame.

> A fast wrong estimate is self-correcting. A slow wrong estimate is not.

The attempt to remove the ripple would have made it permanent. Only the bench built on real data
caught it; neither the model nor the synthetic stimulus did.

## The fix that works

The estimate is now a **running average of every sample since reset**: `K` grows as `floor(log2 n)`
up to `K_MAX`, and only then becomes a leaky integrator with tau = 2^K_MAX. While K grows this is
exactly the mean of all n samples so far — the best estimate available at every instant, with the
modulation averaging down as the window widens. There is no arbitrary transition instant and no
ripple to freeze.

The accumulator holds `mean << K`, so each step re-scales it by one left shift. Miss that and the
estimate halves at every step.

## Verify

```bash
python tools/run_block5_hdl_smoke.py --test tb_dc_blocker_gear
python tools/run_block5_hdl_smoke.py          # full suite: 35/35
```

`tb_dc_blocker_gear` holds the module against a behavioural twin of the **original** fixed-K
algorithm rather than against an ideal, so the comparison is with the code that shipped. Three
numeric checks:

- the injected DC still goes (residual 0 of 5000 injected);
- steady-state data tracking is at least 4× smaller — measured **15.8×**, against 2⁴ = 16× from
  theory, and that agreement is itself evidence the mechanism is understood;
- the estimate beats the original over the **first frame** too. That check exists specifically so the
  gear-at-a-fixed-count regression cannot return silently.

On the retained two-board capture the clean sampler phases go from **1 of 8 to 3 of 8**.

### One test was relaxed — deliberately

`tb_qpsk_phase_picker` asserted that its two real captures decode cleanly at exactly the same set of
sampler offsets. After the fix both masks **widened**, and the extra marginal offsets appeared
asymmetrically: four for one capture, three for the other.

Both captures improved; only the equality broke. Mask equality was a brittle proxy that held only
while both sat at the same margin. The picker's actual contract is to remove the dependence on
arrival phase — the two must be clean on a **common** set, centred on offset 0 — and that is what is
asserted now. The check that the masks *disagree* with the picker bypassed is untouched; without it
the bench would prove nothing.

## What this lab is really about

Five labs were spent measuring the right quantity in the wrong place. The instrument was correct, the
readings were correct, and the conclusion drawn from them — "the signal is healthy, so the fault must
be in the decision logic" — was wrong, because the sentence omitted *where*.

When a measurement and a symptom contradict each other, the schematic between the probe and the
symptom is a suspect too.

No PI gain was ever swept across the whole investigation. A deterministic defect has a cause, not a
tuning.
