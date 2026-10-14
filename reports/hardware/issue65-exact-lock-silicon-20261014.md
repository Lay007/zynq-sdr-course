# Exact preamble lock through the correlator (#65) on silicon, 2026-10-14

Image: `zynq-sdr-course-artifacts/bitstreams/issue65-bpsk-exact-lock-correlator` (sha256 `8fb3a6a5...`,
source commit `e8a483a`, WNS +0.072 ns after a place/route variant), written to board B's SD card
and loaded by a warm `reboot` (the AD9361 probed and calibrated without errors). Raw results:
[`issue65-exact-lock-silicon-20261014.json`](issue65-exact-lock-silicon-20261014.json).

## BPSK start offset sweep, PL fabric loopback, 281-bit frame, preamble 24, exact lock

`start_offset: received / total errors`, decision mode 00. Mode 01 gives the same numbers with the
inverted lock flagged.

| Offset | 50 | 52 | 54 | 56 | 58 | 60 | 62 | 64 | 66 | 68 | 70 | 72 | 74 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Before (`95c5f010`) | 267/129 | 267/122 | 268/130 | 268/130 | 268/130 | 268/123 | 281/0 | 281/0 | 281/0 | 281/67 | 270/132 | 270/132 | 270/132 |
| After (`8fb3a6a5`) | **279/0** | 279/67 | **280/0** | **280/0** | **280/0** | 280/67 | 281/0 | 281/0 | 281/0 | 281/67 | 270/132 | 270/132 | 270/132 |

- At offsets 50-58 the sampler emits extra bits before the frame. The old sequential matcher
  walked past the true start and locked misaligned (about 130 errors). The correlator now finds
  the preamble and the frame decodes without errors. `received` is 279-280 rather than 281
  because the burst window ends at a fixed time, so the last bits fall outside it.
- Offsets 52, 60 and 68 give 67 errors in both images. They are 8 samples apart, the symbol
  period, so the sampler sits on the symbol edge. This is a sampling phase problem, not a lock
  problem, and #65 does not change it.
- Offsets 70-74 give 270/132 in both images: the sampler starts after the beginning of the
  preamble, and the counter later locks on a matching bit pattern inside the data. This is the
  random-data false lock that Lab 5.10 exercise 3 already discusses.

## Regression checks

PL fabric loopback, 40 bursts each: BPSK mode 00 40/40 clean (rotation 0), BPSK mode 01 40/40
clean (rotation 2), QPSK 40/40 clean (rotation 0). The same as on the #64 image.

Two-board link (board A TX1 -> 50 dB path -> board B RX1, 915 MHz, TX -10 dB, RX 50 dB), 200 frames each:

| Mode | Lost | Clean | Payload bit errors | Rotation of the clean frames |
|---|---:|---:|---:|---|
| Absolute QPSK | 23 | 150 | 3119 / 45312 | 0: 40, 1: 46, 2: 33, 3: 31 |
| Differential QPSK | 15 | 181 | 18 / 47360 | 0: 181 |

The QPSK counters use the sliding path (`LOCK_ERR_TOL > 0`), which #65 does not change. The link
numbers are close to the #64 run (absolute 160 clean, differential 180 clean with 2 errors).
Differential errors went from 2 to 18 bits; with one run of 200 frames each this difference is not
attributed to the new image.
