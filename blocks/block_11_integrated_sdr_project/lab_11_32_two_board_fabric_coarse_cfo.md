# Lab 11.32 — Two-board coarse-CFO acquisition in the FPGA fabric

## Objective

Demonstrate that the shipped `qpsk_coarse_cfo.v` block acquires a live QPSK frame inside the PL
across a controlled 0–55 kHz inter-board carrier offset. The comparison keeps the RF path, frame,
attempt budget and timing-phase sweep identical and changes only `gp_ctrl[13]`: coarse correction
enabled versus Costas-only reception.

This is an **acquisition-range experiment**, not a long-duration BER claim. A zero-error frame at
one timing phase proves that the carrier loop can acquire that CFO. Repeatability is reported
separately as clean-attempt rate, lock rate and aggregate BER over full frames.

## Conducted setup

```text
board A: vendor image, cyclic DMA TX at 915 MHz + Δ
    TX1 ── 30 dB attenuator ── SMA cable ── RX1
board B: course bitstream, fabric RX + optional coarse-CFO + Costas + BER counter
```

| Parameter | Value |
|---|---:|
| Carrier | 915 MHz |
| Symbol/sample rate | 480 ksym/s / 3.84 Msps |
| Frame | 140 QPSK symbols, 280 scored bits |
| TX gain | −30 dB |
| RX gain | 50 dB |
| Start offsets | 0…7 |
| Attempts | 3 per offset and mode, 24 per CFO and mode |
| CFO sweep | 0…55 kHz in 5 kHz steps |

The transmitter replays a bit-exact frame reconstructed from `bpsk_frame_bits.mem` and the course
QPSK mapper. The receiver and BER counter run in the course bitstream. Both boards are forced to
−89.75 dB before setup and in `finally`, including after an exception.

## Metric contract

| Metric | Meaning |
|---|---|
| `reached_zero` / `best_ber` | At least one full 280-bit frame was decoded without errors; evidence of acquisition. |
| `clean_attempt_rate` | Zero-error full frames divided by every attempt, including no-lock attempts. |
| `lock_rate` | Attempts that returned all 140 symbols divided by every attempt. |
| `aggregate_ber` | BER over full frames only; no-lock attempts are not silently counted as zero errors. |
| Wilson interval | 95% interval for lock and clean-attempt proportions. |

The JSON retains every attempt, so the headline can be regenerated without selecting rows by hand.

## Measured result

Measured 2026-07-20 over the conducted 30 dB path. Coarse correction acquired at BER=0 at **12/12
CFO points** and produced **75/288 clean attempts (26.0%)**. Costas-only produced **0/216 clean
attempts** at the nine discriminating points from 15 to 55 kHz.

![Two-board in-fabric coarse-CFO acquisition](/zynq-sdr-course/assets/lab1132_two_board_fabric_coarse_cfo.png)

| CFO, kHz | Coarse clean | Coarse lock | Coarse aggregate BER | Costas best BER | Costas clean | Costas lock |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 7/24 | 50.0% | 0.175 | 0 | 8/24 | 66.7% |
| 5 | 6/24 | 70.8% | 0.267 | 0.400 | 0/24 | 70.8% |
| 10 | 6/24 | 79.2% | 0.302 | 0.464 | 0/24 | 83.3% |
| 15 | 5/24 | 66.7% | 0.245 | 0.493 | 0/24 | 25.0% |
| 20 | 9/24 | 79.2% | 0.203 | no lock | 0/24 | 0% |
| 25 | 7/24 | 83.3% | 0.227 | no lock | 0/24 | 0% |
| 30 | 7/24 | 70.8% | 0.232 | 0.439 | 0/24 | 12.5% |
| 35 | 8/24 | 87.5% | 0.276 | 0.468 | 0/24 | 25.0% |
| 40 | 2/24 | 58.3% | 0.395 | 0.443 | 0/24 | 16.7% |
| 45 | 3/24 | 58.3% | 0.361 | 0.514 | 0/24 | 4.2% |
| 50 | 10/24 | 70.8% | 0.136 | 0.454 | 0/24 | 4.2% |
| 55 | 5/24 | 66.7% | 0.171 | no lock | 0/24 | 0% |

The result validates the **CFO acquisition range**: the in-fabric estimator finds a clean frame at
every tested CFO while Costas alone does not at 15–55 kHz. It does not yet validate a robust
continuous link. The 26% clean-attempt rate and high conditional aggregate BER show the remaining
sample-clock/timing-phase problem clearly; the next receiver improvement is continuous timing
recovery or a disciplined burst-phase search.

## Reproduce

First check the bit-exact host waveform without radio:

```bash
python python/lab_11_32_two_board_fabric_coarse_cfo.py --self-test
```

Then run the measured sweep from the repository root:

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py \
  --host-a 192.168.40.1 --host-b 192.168.20.1 \
  --cfo-start 0 --cfo-stop 55000 --cfo-step 5000 \
  --retries-per-offset 3
```

The canonical machine-readable result is
[`docs/assets/lab1132_two_board_fabric_coarse_cfo.json`](/zynq-sdr-course/assets/lab1132_two_board_fabric_coarse_cfo.json).
The command exits non-zero unless coarse correction reaches BER=0 at every CFO point and
Costas-only reaches none of the points with `|CFO| ≥ 15 kHz`.

## RF safety

Use only the contained cabled path with the 30 dB attenuator. Do not attach antennas with these
settings. Do not raise TX power to compensate for a weak link; inspect the cable, attenuator and RX
gain instead. On interruption, verify both boards are back at −89.75 dB before disconnecting them.
