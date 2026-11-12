# ADR 0005: OpenWiFi as an optional PHY/MAC engineering track

## Status

**Accepted as a course architecture and documentation decision: 2026-11-12.**
**Hardware, software porting, radio operation and performance remain unverified on the course's ZynqSDR boards.**

Implementation is tracked in [issue #92](https://github.com/Lay007/zynq-sdr-course/issues/92).

## Context

The twelve-block `zynq-sdr-course` already includes QPSK and OFDM modeling, fixed-point design, RTL and RF measurement. The [OpenWiFi](https://github.com/open-sdr/openwifi) ecosystem offers an advanced open SDR-based Linux/mac80211 and FPGA PHY/lower-MAC case study. It supports OFDM-based 802.11a/g and a limited 802.11n mode in its documented open implementation, with no legacy 802.11b PHY support.

Upstream lists multiple Zynq-7020/AD936x reference boards. The course uses FISH Ball PlutoSDR Rev.A (Zynq-7020 + AD9361); device similarity alone does not establish pin-, clock-, boot-, kernel-, or FPGA-image compatibility. Earlier course board experiments exposed AD9361 calibration failures with some rebuilt PL payloads.

## Decision

1. **Do not add a thirteenth mandatory block.** Publish a bilingual optional **OpenWiFi PHY/MAC Engineering Track** and reuse existing Blocks 4/5 (fixed point and RTL), 7/8 (PHY), 9 (capture/CSI), 11 (integration) and 12 (capstone).
2. Define planned elective units `WIFI-1` ... `WIFI-6`: OFDM PHY, packet RX, fixed-point/RTL verification, board porting, real Wi-Fi MAC/RF metrics, and CSI-based sensing. These are **planning IDs**, not completed or registered course labs.
3. Keep **offline PHY and self-checking tests** independent of the vendor toolchain and hardware. Preserve model -> fixed-point -> RTL -> FPGA -> RF -> measurement and distinguish evidence levels.
4. Establish a **board feasibility and recovery gate** before touching the deployed FPGA/firmware. A hypothetical `openwifi-experimental` image is not added to the verified firmware profile registry until validated per physical board according to [ADR 0004](0004-zynqsdr-firmware-profiles.md).
5. Keep upstream revisions pinned when implementing labs and cross-check feature claims against those revisions. Do not equate 802.11a/g/n support with full Wi-Fi 4/6 or state upstream best-case throughput as course-board evidence.
6. Keep original course scripts, small test vectors and reports public; keep board-specific boot binaries and proprietary IP artifacts segregated under [ADR 0003](0003-binary-artifact-repository-boundary.md). OpenWiFi software/RTL license conditions (AGPL-3.0-or-later and third-party terms) require review before source redistribution or derivative integration into the MIT course.
7. Use conducted/cabled measurements only with verified RF power budget, attenuation, gain plan, spectral compliance and logging. Do not infer high-accuracy ranging from 20 MHz CSI alone.

## Consequences

- The original 12-block learning path stays unchanged.
- Upstream reference designs can inform architecture and verification without forcing vendor tools on ordinary CI.
- Linux/mac80211, lower-MAC timing, OFDM packet decoding, CSI and interoperable networking become available as **future** hands-on topics.
- Board support is a separate, potentially high-effort research task; a fully reproducible offline track can be finished first.
- No claim of working Wi-Fi, timing closure, packet decoding or CSI on the user's board is made by this decision.

## Evidence gates

| Gate | Required evidence |
| --- | --- |
| Feasibility | Pinned upstream SHAs; board/FPGA/PS/kernel/clock/IP-license comparison; documented risks and restore process |
| Offline PHY | Deterministic IQ vectors, reference packets and FCS, unit tests, BER/PER/EVM/CFO definitions |
| RTL | Self-checking tests, fixed-point error bounds, tool/IP versions, utilization and timing reports |
| Board | Boot and AD9361 calibration logs, verified `sdr0`, board identity, image hashes, rollback proof |
| RF + MAC | Safe RF chain, captured association and packet exchange, throughput/PER/latency/retries with setup metadata |
| CSI | Packet-correlated timestamped channel estimates, stable baseline, uncertainty and limitations |

## Documents

- [English engineering track](../en/openwifi-engineering-track.md)
- [Russian engineering track](../ru/openwifi-engineering-track.md)
- [Tracking issue #92](https://github.com/Lay007/zynq-sdr-course/issues/92)
- [OpenWiFi software](https://github.com/open-sdr/openwifi)
- [OpenWiFi FPGA](https://github.com/open-sdr/openwifi-hw)
