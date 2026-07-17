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

Verbatim from the script:

```text
board A transmitting: TX=-30.000000 dB at 915.000 MHz, DAC source=0x00000002 (DMA), LO_powerdown=0
receiver alive: capture rms = 253.5 counts
contiguity check: |autocorr| at the 32768-sample cyclic period = 0.9989

timing mu = 1.625 samples, |corr| = 35.6x
EVM       = 6.62 %
CFO       = -173.2 Hz (std 13.4 Hz) -> -0.189 ppm at 915 MHz
estimator float vs fixed(RTL): mean |diff| = 0.14 Hz, max 0.34 Hz
SER       = 0 / 15360 = 0.000000
```

| Metric | Value |
|---|---|
| Contiguity `\|autocorr\|` at the cyclic period | 0.9989 |
| Correlation peak | 35.6× above mean |
| EVM | 6.62 % |
| Inter-board CFO | −173.2 Hz, std 13.4 Hz (−0.189 ppm at 915 MHz) |
| **Estimator float vs fixed (RTL)** | **mean \|diff\| = 0.14 Hz, max 0.34 Hz** |
| **SER** | **0 / 15 360 symbols (30 720 bits)** |

Two independent TCXOs land ~0.2 ppm apart — a couple of hundred Hz at 915 MHz, stable to ~13 Hz
across the record. The estimator is unambiguous to ±60 kHz (±1/8 cycle/symbol at 480 kSym/s), so
the hardware sits inside its design range with more than two orders of margin, and the
fixed-point arithmetic that the RTL performs tracks the float reference to **fractions of a hertz
on a live signal**. An earlier interactive run of the same sequence gave EVM 6.59 %, CFO
−208.0 Hz and float-vs-fixed 0.09 Hz — the same numbers to within run-to-run drift.

The estimator comparison feeds **both** models the same symbols of the same (non-derotated)
segment. Handing the fixed model a derotated slice, or a different symbol count, measures the two
estimators' own variance instead of the arithmetic — it inflated this figure from 0.14 Hz to
66 Hz before it was fixed.

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

## Repeatability

The lab runs back-to-back with **no reboots between runs**. Verified with a **25-run unattended
series** (232 s), no failures:

| Over 25 runs | |
|---|---|
| Decoded | **768 000 bits, 0 errors → BER = 0** (0 / 384 000 symbols) |
| Inter-board CFO | mean −288.5 Hz, **σ 11.0 Hz** (min −311.5, max −262.0) |
| EVM | mean 7.35 % (6.65…8.27 %) |
| Correlation lock | ≥ 35.5× above mean; contiguity `\|autocorr\|` ≥ 0.994 every run |

Two things make that possible, and both were hard-won:

- **The receiver must be a board of the same class as the transmitter** (stock ADI/Pluto,
  Linux 5.15). The first receiver — a FishBall/ZynqSDR appliance on a frozen Linux 4.0 — had a
  driver that wedged its RX DMA after roughly one capture/reconfiguration per boot, ignored plain
  `reboot`, sometimes ignored sysrq, and occasionally needed a **physical power cycle**. Reflashing
  it with the same Pluto image the transmitter runs removed all of that: its RX now returns clean
  data on every run, and `reboot` works.
- **The transmitter's cyclic DMA is freed at the start of every run** by `reset_tx_dma()`. Left
  alone, `iio_writedev -c` gets stuck in an unkillable (uninterruptible-DMA) state holding the DAC
  buffer, so the next run fails with `Unable to allocate buffer: Device or resource busy` — and
  `pkill -9`, `SIGTERM` and a DDS-core RSTN toggle all fail to clear it. An **unbind+rebind of the
  `cf_axi_dds` driver** does. It re-registers the DDS core under a new `iio:deviceN`, which is why
  the lab addresses the transmitter and receiver by NAME and reads the DAC source by physical
  address — nothing depends on the DDS device number.

> **Recipe:** flash both boards with the bench image (see the per-board `README-bench.txt` on each
> SD card), then just run the lab — repeatedly, unattended. Run `--self-test` first if you have
> changed the host-side analysis.

**Still keep `-b` fixed within a session:** a capture with a different `-b` makes the driver
stitch the next one from stale chunks (`|autocorr|` collapses to ~0.02, i.e. trap 1). The lab uses
one buffer size (`--capture`) for its single read, so this only bites if you probe the receiver by
hand between runs — don't.

## A launch trap worth knowing

`ParamikoCommandRunner` wraps every command in `sh -lc '...; rc=$?; printf ...'` and reads the
channel to EOF. A background job started through it — even `nohup ... &` — is **torn down with
the wrapper**, silently and with an empty log. Measured side by side:

```text
start via ParamikoCommandRunner:  DAC source = 0x0 (DDS), writedev gone
start via a raw exec_command:     DAC source = 0x2 (DMA), writer alive
```

So the transmitter is launched on a raw session (`start_detached`). And because a *running*
`iio_writedev` still does not prove transmission, the lab reads the DAC source select back and
demands `0x2`; a channel left on the DDS with zero scale otherwise looks exactly like a dead
link — which is precisely how this was found.

## RF safety

This is a **conducted** lab: board A's TX1 reaches board B's RX1 through a cable and a 30 dB
attenuator, and nothing radiates. The default −30 dB TX is safe behind that attenuator. Over the
air the limit is **−50 dB** — do not raise power to "see the signal".

Board B's stock `rc.user` re-arms a **71 MHz transmitter at −10 dB on every boot**. This lab
kills it and forces −89.75 dB before touching anything else, and quiets both boards on exit —
including after a failure.
