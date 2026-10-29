# v1.0 completion gates

Evidence snapshot: 2026-10-29, based on the committed reports linked below. This
updates the completion plan originally reviewed at `c7d5542` on 2026-09-19.
It does not establish the current GitHub issue state or announce a release.
The existing v0.1.0 release instructions remain separate.

| Workstream | Evidence already recorded | Remaining acceptance or follow-up |
|---|---|---|
| [#48 OFDM](https://github.com/Lay007/zynq-sdr-course/issues/48) | Fixed-point models, RTL and implementation reports; [DMA fabric loopback on a board](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/ofdm-dma-fabric-loopback-20261014.md): 0 errors in 3,072,000 bits. The radio image has been built. | Run the radio image through a protected, attenuated RF loopback, then two boards; report BER/counts, detection failures, EVM/CFO, clipping and spectrum. Fabric loopback does not qualify the RF receiver. |
| [#29 gain/overload](https://github.com/Lay007/zynq-sdr-course/issues/29) | [Two-board overload grid](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/ad9361-two-board-overload-20261013.md) and [gain steps at 433/915/2400 MHz](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/ad9361-gain-steps-20261014.md). Levels are relative. | Measure the complete passive path S21 with its reference plane and uncertainty before converting settings to absolute input power or claiming connector-to-connector limits. |
| [#37 NanoVNA](https://github.com/Lay007/zynq-sdr-course/issues/37) | RU/EN Labs 10.5/10.6, parsers and templates. The [conducted-tone report](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/ad9361-conducted-loopback-20260715.md) records a subsequent 30 dB attenuator check from 50 MHz to 1 GHz. | Archive the calibration, photos and Touchstone/CSV exports; measure cable and splitter loss as well. An attenuator check alone does not calibrate the complete path. |
| [#58 AGC](https://github.com/Lay007/zynq-sdr-course/issues/58) | [Two-board gain transitions](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/ad9361-agc-transient-20261014.md) and [frame-aligned level steps](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/ad9361-agc-frame-step-20261014.md) compare manual, slow and fast gain modes. | The slow-attack phase step still needs a common-reference measurement. Keep RFIC gain behavior separate from the modem's level-drop failure and its [DC-blocker follow-up](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/dc-blocker-persist-silicon-20261014.md). |
| [#55 mailbox](https://github.com/Lay007/zynq-sdr-course/issues/55) | The [message modem report](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/message-modem-20261015.md) records the mapped mailbox, board images, one-board use and two-board mailbox reception: 498/500 messages at the stated operating point, no wrong payload accepted. [Chat/ARQ](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/two-board-arq-20261017.md) and [fragmentation](https://github.com/Lay007/zynq-sdr-course/blob/588aeba/reports/hardware/two-board-link-layer-20261017.md) extend the measured path. | The original message-delivery target has recorded board evidence. Verify deployed-image RX_STOP/turnaround and chat/fragment latency for the later [#71 change](https://github.com/Lay007/zynq-sdr-course/issues/71); the older mailbox measurements do not validate that change. |

The [course status](status.md) summarizes block readiness. This table tracks the
acceptance workstreams; the linked reports retain the configurations, counts and
limitations of individual experiments. Historical reports are not rewritten as
though their measurements used a later image.

## Repeatable offline preflight

For environment setup on Windows and Linux, use the [reproducibility guide](reproducibility-guide.md).
Choose the checks that match the change:

```bash
python tools/run_local_ci.py --software-only
python tools/tasks.py docs
python tools/run_local_ci.py --hdl-only
```

The default `python tools/run_local_ci.py` also rebuilds representative Python
labs. HDL checks cover the canonical Block 5 suite, CSS and default OFDM benches
with radio parameter variants. Separate Actions workflows cover additional
OFDM configurations. These commands run software or simulations, not a board.

## Closing rule

For every hardware step keep the commit/bitstream hash, configuration, raw-data
checksums, number of all attempts and reasons for losses. Compare evidence with
the exact acceptance criteria before closing a workstream. A synthetic self-test,
a constellation without counters or a series from another image is insufficient.
Mark MATLAB checks separately from Python/RTL and state missing licences or
artifacts explicitly. Complete these acceptance steps before expanding the PHY.
