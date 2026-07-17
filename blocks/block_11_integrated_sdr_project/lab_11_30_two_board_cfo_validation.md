# Lab 11.30 — Coarse-CFO estimator on a real two-board link

## Objective

The Block 05 coarse-CFO estimator (`qpsk_coarse_cfo.v`, modelled by `coarse_cfo_ref.py`) was
proven only against **synthetic** offsets: a float model, a fixed-point model that matches it
bit-exactly, and an RTL testbench fed a generated capture. Every one of those shares the same
assumption — that a real pair of AD9361s looks like the model.

One board cannot test it. `TX_LO` and `RX_LO` come from the same reference, so the CFO is ~0 and
there is nothing to estimate. This lab uses **two boards with independent references**, which is
the only configuration where a real carrier offset exists, and re-runs the very same float and
fixed-point estimators over the recovered symbols. The fixed-point path is the RTL's arithmetic,
so agreement here is evidence about the shipped HDL rather than about a simulation.

## Setup

```
board A  ──  cyclic QPSK out of the DAC via DMA (course RRC, SPS=8, 480 kSym/s, 3.84 MHz)
   │
   │   TX1 ──▶ 30 dB attenuator ──▶ RX1     (contained SMA cable, 915 MHz)
   ▼
board B  ──  raw IQ capture ──▶ SSH ──▶ host: estimator, EVM, SER
```

Board B is a second AD9361 board on its own subnet, so both can share one switch without an
address clash (`ZYNQ_SSH_HOST_B`, default `192.168.20.1`). The transmitted waveform is built
from the **same Q15 RRC taps the PL transmitter uses**, and the RRC is applied **circularly** —
the DMA replays the buffer end-to-start forever, and a linear convolution would leave a seam
that splatters the spectrum.

## Run

```bash
# ALWAYS first: the analysis chain against the generated waveform, no radio in the path.
python blocks/block_11_integrated_sdr_project/python/lab_11_30_two_board_cfo_validation.py --self-test

# then the real link
python blocks/block_11_integrated_sdr_project/python/lab_11_30_two_board_cfo_validation.py
```

Useful flags: `--carrier` (default 915e6), `--tx-gain` (default −30 dB, conducted), `--rx-gain`,
`--symbols`, `--capture`, `--window`, `--host-a/--host-b`.

## Result (2026-07-17, 915 MHz, −30 dB TX into 30 dB attenuator, RX gain 50 dB)

> **Provenance.** These are real hardware numbers from the conducted link described above, taken
> with the same command sequence this lab automates. They were captured interactively while the
> sequence was being worked out; the script's own end-to-end run has not yet reproduced them,
> because the receiver's DMA wedged (see *Known fragility*) and would not recover without a
> physical power cycle. The analysis chain itself is verified independently and repeatedly by
> `--self-test` (SER = 0, EVM 2.20 %, |corr| 36×). Re-run the script once the receiver is power
> cycled and replace this note with its output.

| Metric | Value |
|---|---|
| Contiguity `\|autocorr\|` at the cyclic period | 0.9944 |
| Correlation peak | 35–50× above mean |
| EVM | 6.59 % |
| Inter-board CFO | −208.0 Hz, std 4.2 Hz (−0.23 ppm at 915 MHz) |
| **Estimator float vs fixed (RTL)** | **mean \|diff\| = 0.09 Hz** |
| **SER** | **0 / 14 336 symbols (28 672 bits)** |

Two independent TCXOs land ~0.2 ppm apart — a few hundred Hz at 915 MHz. The estimator is
unambiguous to ±60 kHz (±1/8 cycle/symbol at 480 kSym/s), so the hardware sits inside its design
range with more than two orders of margin, and the fixed-point arithmetic that the RTL performs
tracks the float reference to **fractions of a hertz on a live signal**.

## Four traps this lab encodes

Each of these produced a convincing but entirely false "hardware defect". Three of the four were
the *measurement*, not the radio.

### 1. `iio_readdev` defaults to a 256-sample buffer

Without `-b <N>` the capture is stitched from `N/256` chunks **with dropped samples between
them**. Every chunk is valid, so the spectrum and EVM look perfectly reasonable — but the record
is not a contiguous time series. Symptoms: correlation never locks (5–8× instead of 20–70×), the
CFO appears to wander by tens of kHz, BER sticks near random.

Always size the buffer to the whole capture, and verify:

```text
|autocorr| at the cyclic buffer's period:   chunked ≈ 0.01      contiguous ≈ 0.99
```

CFO does not break this check — it only adds a constant phase — so it is a clean yes/no on
contiguity. The lab runs it automatically and warns.

### 2. A DDS tone does not power the TX synthesizer

With `adi,tx-lo-powerdown-managed-enable=1` the driver keeps `out_altvoltage1_TX_LO_powerdown=1`
until a real TX **stream** exists. A DDS-only tone is not a stream, so the synthesizer stays off
and **nothing leaves the SMA regardless of `hardwaregain`**. The signature is unmistakable once
you know it: *changing TX gain by 40 dB moves the received level by exactly nothing* — that is a
broken path, not a weak one. Don't chase cables.

A DMA buffer (what this lab uses) *is* such a stream and brings the LO up by itself. To bisect
digital-vs-analog when a link is silent, use the AD9361's own loopback — the debugfs attribute is
`loopback`, not `bist_loopback`:

```bash
echo 1 > /sys/kernel/debug/iio/iio:device0/loopback   # digital TX→RX inside the chip
```

A strong tone there with silence at `loopback=0` puts the fault in the analog/LO domain and
exonerates the firmware, the DDS core and every cable.

### 3. The EVM reference must be rotated by +45°

For QPSK `sym**4 = −1` always, so `angle(mean(sym**4))/4 = π/4` and the correction lands the
constellation **on the axes**, not at 45°. Compare it against `(±1±j)/√2` and you measure a
constant ≈54 % that no gain, timing or LO change will ever move. That immovability *is* the
clue: physics moves, a constant arithmetic error does not.

### 4. Correlation sign

`ifft(fft(a) * conj(fft(b)))` peaks at `off` meaning `a[n] ≈ b[n−off]`, so the aligned reference
is `np.roll(tx, +off)`. The wrong sign gives exactly the 0.75 SER of a random guess — while the
correlation still reports a perfect lock.

> **The rule all four teach:** run the whole analysis chain on a known signal with no radio in
> the path, and require SER = 0, *before* concluding anything about hardware. `--self-test` does
> exactly this in a few seconds.

## Known fragility

**The receiver used here (a FishBall/ZynqSDR appliance on Linux 4.0) is the weak link, and the
lab is shaped around it.** Its RX DMA wedges easily and then returns a zero-length read or an
all-zero buffer. Observed, in order of how quickly it bites:

- It survives roughly **one capture per boot** once its LO/sample rate have been reconfigured.
  This is why the lab performs **exactly one** `iio_readdev` and validates the *measurement*
  capture rather than taking a separate probe read — an earlier version probed first and the
  probe consumed the only good capture.
- A second read with a **different `-b`** makes the driver stitch the next capture from stale,
  smaller chunks — silently reintroducing trap 1 (`|autocorr|` collapses to ~0.02). Keep `-b`
  identical across every read in a session.
- Retuning far outside its native band wedges it outright (it died at 1800 MHz; its stock modem
  lives at 71/72 MHz).
- ENSM bounce, re-tune and even the AD9361 `initialize` do **not** clear a wedge.

Recovery: reboot it. Its Linux ignores plain `reboot`; sysrq usually works but **not reliably** —
during one session it stopped responding to sysrq entirely (uptime kept climbing) and only a
**physical power cycle** brought the receiver back.

```bash
echo 1 > /proc/sys/kernel/sysrq && echo b > /proc/sysrq-trigger   # or: reboot -f
```

Practical recipe: **power-cycle the receiver, then run the lab once.** If it reports a wedged
DMA or a failed contiguity check, power-cycle again rather than retrying — retries make it worse.

On the transmitter, a killed `iio_writedev` can leave the cyclic DMA buffer allocated; the next
run then fails with `Unable to allocate buffer: Device or resource busy`. The lab surfaces that
error explicitly; a reboot clears it.

A more robust receiver (a second board of the same class as the transmitter) would remove nearly
all of the above — the measurement itself is undemanding.

## RF safety

This is a **conducted** lab: board A's TX1 reaches board B's RX1 through a cable and a 30 dB
attenuator, and nothing radiates. The default −30 dB TX is safe behind that attenuator. Over the
air the limit is **−50 dB** — do not raise power to "see the signal".

Board B's stock `rc.user` re-arms a **71 MHz transmitter at −10 dB on every boot**. This lab
kills it and forces −89.75 dB before touching anything else, and quiets both boards on exit —
including after a failure.
