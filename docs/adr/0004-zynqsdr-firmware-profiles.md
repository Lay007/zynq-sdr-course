# ADR 0004: ZynqSDR firmware profiles based on Pluto-compatible firmware

## Status

Accepted as an **architecture and documentation decision** on 2026-11-02.
**No new firmware has been tested or deployed by this ADR.**
Board-level validation is tracked in [issue #81](https://github.com/Lay007/zynq-sdr-course/issues/81).

## Context

The course uses two ZynqSDR boards (FISH Ball PlutoSDR Rev.A, Zynq-7020 + AD9361)
whose original software stack is Pluto-compatible. The stock platform exposes
the AD9361 control plane and sample buffers through Linux/IIO. Course experiments
also use custom PL designs to move DSP and packet processing from host software
into FPGA fabric.

The private [zynq-sdr-course-artifacts](https://github.com/Lay007/zynq-sdr-course-artifacts)
repository already contains vendor-era SD boot files, board-specific QSPI backups,
course boot sets, bitstreams, Vivado reports and SHA-256 manifests. These are
**historical artifacts**, not evidence that every image still boots today.

We should teach software SDR and FPGA SDR on **the same physical platform**, not
require a second ADALM-Pluto board. The Pluto chapter of
[PySDR](https://pysdr.org/content/pluto) is a useful teaching reference, but
examples must be adapted to the actual ZynqSDR board, transport and image.

## Decision

1. Treat **Pluto-compatible vendor software/IIO** as the *reference architecture*.
   Preserve a candidate vendor boot set and separately establish an actually
   boot-tested, known-good baseline for each physical board.
2. Support two primary learning modes:
   - **Software/IIO:** configure AD9361 and capture/transmit IQ through the
     available IIO transport; process samples in Python, MATLAB or C++ on the host.
   - **Course FPGA:** retain the required AD9361/clock/PS integration but run
     selected modem/DSP stages in custom PL. Use the verified image's actual
     capabilities; a custom image is not automatically fully Pluto-compatible.
3. Include *comparison experiments* (same waveform, sample rate, gains,
   acquisition method and metric definitions) for software versus PL QPSK.
   Report EVM, BER with bit count, CFO, throughput and latency separately from
   FPGA resource/timing numbers. Do not assert equivalence without measurements.
4. Keep **source, educational documentation, reproducible scripts and lightweight
   results public**. Keep **binary images, QSPI dumps and board-specific recovery
   evidence private**, under [ADR 0003](0003-binary-artifact-repository-boundary.md).
   Public simulations, documentation and HDL CI must remain usable without the
   private artifact repository.
5. The private artifact repository owns the exact **firmware profile registry**.
   A profile references existing SHA-256 manifests; it must not copy or create
   another binary simply to provide a convenient name.

## Profile taxonomy (do not confuse with deployment state)

| Logical profile | Existing archive candidate | Current evidence boundary |
| --- | --- | --- |
| `vendor-pluto` | `sd-images/sd-orig-v2/` | Vendor-era archive; baseline candidate, **not board-verified recovery** |
| `course-fpga` | `boot-sets/board-b-course/` | Historical board-B boot configuration, not a universal latest image |
| `qpsk-modem` | `bitstreams/issue70-listen-window/` | Archived modem bitstream, historically deployed on both boards (2026-10-17); not a complete boot set by itself |
| `display-demo` | None yet | Proposed SPI TFT/web display experiment; hardware electrical checks remain open |

The paths above are in the **private** repository. The full list of candidate
SD and FPGA images, provenance and file-level hashes stays there.

**Archive presence**, **boot validation**, **RF measurement**, and
**currently deployed** are independent fields. A manifest recording a past
deployment does not confirm the present board state.

## Switching and recovery constraints

- **Do not flash QSPI** or replace a deployed image just to exercise this ADR.
  First record the current boot mode and read-only identity for each board.
- Board A and board B have different QSPI states. Their dumps and fallback
  behavior must be checked separately; `switch to QSPI` is **not** yet a
  universal recovery procedure.
- The archived `boot-sets/board-b-course/README_ПРОЧТИ.txt` describes
  `uImage` as required, but the archived directory/manifest do not include it.
  Resolve that dependency before declaring the package self-contained.
- An earlier runtime PL reload did not establish a usable `sample_clk`.
  A boot-time PL load has been used in the course. Recheck clock/reset and
  AD9361/IIO/AXI behavior for **each specific image**, rather than assuming
  hot-swapping is safe.
- During checks keep transmitters in a documented safe, muted state until
  the attenuated RF path and gain plan are verified.

## Minimum promotion gate for a usable profile

For **each** physical board and image, record:

1. Board identifier, boot mode and boot logs; exact `BOOT.bin`, DTB, kernel/rootfs,
   PL file dependencies and their hashes (including absent external dependencies).
2. Linux version, device-tree identity, FPGA build/source commit, IIO devices
   and observed capabilities.
3. Read-only boot and RX/IQ capture smoke tests; TX safety defaults; clock and
   DMA readiness, plus PL modem smoke tests where applicable.
4. Controlled RF evidence with repeatable settings and measured metrics.
5. Dated evidence and a **board-specific, tested rollback method**.

Do not mark a profile `verified` based only on a JSON manifest or a previously
published performance result.

## Educational integration

Use the existing labs rather than introducing a redundant course block:

- **Block 6:** Labs 6.3 (IIO discovery) and 6.6 (RX-only capture) become
  software-route entry points with board-image metadata.
- **Block 7:** Lab 7.3 provides the reference QPSK metric definitions;
  a future host-IIO loopback can use the same inputs and report format.
- **Block 11:** Hardware QPSK and the two-board chat remain the PL route.
  Lab 11.5 provides a queueing/latency model; real IIO throughput/latency
  measurements must be a distinct experiment.
- **Lab 11.53:** The optional SPI display is a *future* profile extension,
  not a confirmed functioning peripheral.

Finish the read-only inventory and safe recovery plan in
[issue #81](https://github.com/Lay007/zynq-sdr-course/issues/81) before
introducing an image-switching tutorial or programming automation.
