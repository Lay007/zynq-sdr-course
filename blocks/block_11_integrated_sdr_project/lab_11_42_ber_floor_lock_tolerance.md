# Lab 11.42 — The last few percent: a frame-sync false lock

## Goal

With the DC blocker fixed ([Lab 11.41](lab_11_41_dc_blocker_data_tracking.md)) the two-board Gardner
link is ~92% clean. Find what the remaining ~6–8% of frames are, and close it — or prove it cannot be
closed without an RTL change.

## The failures are bimodal

The first move is not to tune anything; it is to look at what the dirty frames actually are. Splitting
the locked frames by payload-error count:

- **~92%** decode perfectly;
- **~2–3%** carry a single wrong bit — ordinary channel noise, scattered across random indices;
- **~2–3%** carry **~117 of 256 bits wrong** — 46%.

46% is not marginal SNR. A frame that is genuinely near the noise floor loses a handful of bits, not
half of them. Half the bits wrong is a **discrete event**: the whole burst decoded in the wrong
constellation rotation. The two error populations need separate explanations; averaging them into one
"BER" hides the one that matters.

## Where the gross errors sit

A 90° rotation and a mid-frame carrier slip both produce ~50% BER, so the error *count* cannot tell
them apart. Their *position* can, and the `gp_ctrl[15]` telemetry reports it — which quarter fails
first, and the index of the first error. Measured over the gross frames:

- quarter 0 is clean in only ~1 of 17 gross frames;
- the first error is in payload bits 0–31 in ~16 of 17.

The corruption starts at **bit 0** and spans the whole frame. That rules out a mid-frame slip (which
would leave an early clean region) and fixes the mechanism as **a whole-burst wrong rotation from the
very first symbol**.

## Every runtime lever, falsified

The receiver already resolves the QPSK 90° ambiguity with a four-rotation frame sync, so a wrong
rotation means that resolution mis-fired. Before touching RTL, each runtime hypothesis was tested and
killed by data:

| Hypothesis | Lever | Result |
|---|---|---|
| inter-board CFO confuses acquisition | coarse CFO `gp_ctrl[13]` | **worse** — gross 5% → 16%, lock 100% → 84% |
| per-burst re-acquisition from reset | `costas_hold_phase` `gp_ctrl[11]` | no effect (3.0% → 3.3%) |
| a bad sampling phase | sweep `start_offset` 0–7 | flat; the earlier apparent correlation was noise |
| not enough SNR | TX −38…−22 dBm | **U-shaped**, minimum ~3% at −30 (noise below, compression above) |
| RX operating point | RX gain 30–70 | **U-shaped**, minimum ~3% at gain 30–50 |

Both power axes are U-shaped with a floor at the optimum, and no gate removes it. The floor is not a
channel condition and not a tuning; it is structural.

## The cause is arithmetic

The frame-sync arbitration (`qpsk_ber_counter`) is **first-past-the-post over a sliding 24-bit
correlation**: the first branch to find a window whose preamble mismatch is `≤ LOCK_ERR_TOL` owns the
burst, and branch A has priority. The module comment assumed a wrong quadrant "mismatches ~12 of the
24 preamble bits, far outside LOCK_ERR_TOL, so exactly one branch ever acquires." That is true *at the
true frame position*. It ignores the sliding search over the rest of the burst.

A wrong quadrant matches each preamble bit with probability ~½, so at any one of the ~140 sliding
positions the chance of a window with `≤ LOCK_ERR_TOL` mismatches is `C(24, ≤tol) / 2²⁴`. Over the
burst:

```
python lab_11_42_ber_floor_lock_tolerance.py --predict
   LOCK_ERR_TOL=3: per-position 1.4e-4 -> per-burst 1.9e-2
   LOCK_ERR_TOL=2: per-position 1.8e-5 -> per-burst 2.5e-3
   LOCK_ERR_TOL=1: per-position 1.5e-6 -> per-burst 2.1e-4
   LOCK_ERR_TOL=0: per-position 6.0e-8 -> per-burst 8.3e-6
```

At the shipped `LOCK_ERR_TOL=3` that is **~2% per burst** — a **false lock**, and it matches the
measured floor. The gross failures are branch A sliding over the noisy part of the burst and locking
on a chance window before the true frame arrives.

## The fix, and why it does not cost lock rate

Tighten `LOCK_ERR_TOL` to 1: the chance window drops ~100× to ~0.02% per burst. The obvious worry is
the other side of the trade — a *true* preamble carrying a couple of noise errors would now fail to
lock and the burst would be lost. Two things make that safe here:

- the true preamble matches near-perfectly (the clean bursts have zero preamble errors), so it locks
  with room to spare at tol=1;
- verified in simulation on the real self-OTA captures — both `tb_qpsk_rx_costas` and, crucially,
  `tb_qpsk_costas_stress` (which prepends **3000 noise samples** before the frame, exactly the
  false-lock scenario) decode at **BER 0/280** with `LOCK_ERR_TOL=1`. The tightened lock rejects the
  noise and still acquires the true frame.

Full block-5 suite: 35/35. The change is one parameter in the bridge instantiation, but it is backed
by the arithmetic above and by the stress bench, not by a guess.

## Hardware validation

_Pending the tol=1 rebuild and cold-boot redeploy; to be filled with the measured gross-failure rate._

## What this lab is really about

The DC-blocker bug was one block trusting a measurement taken in the wrong place. This one is one
comment trusting an assumption at a single point — "the wrong branch can't lock" — that held at the
true frame position and failed everywhere else the correlator looked. Both were closed the same way:
stop averaging, split the failure population, and follow the one that carries the signal. Here the
arithmetic of a sliding correlator predicted the exact floor before a single knob was turned.
