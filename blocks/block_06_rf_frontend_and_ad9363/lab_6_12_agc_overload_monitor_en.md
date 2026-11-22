# Lab 6.12 — AD9361 Overload Detectors and AGC Response (Two ZynqSDR Boards)

## Purpose and prerequisites

Measure **why** AD9361 AGC responds to an RF level change, not just how fast the output IQ settles. Use two Zynq-7020 + AD9361/AD9363-compatible SDR boards: board A transmits, board B receives. Compare manual, slow_attack and fast_attack; examine large LMT, large ADC, small ADC and low-power outputs. The advanced path instruments the signals in PL and reads event counters through AXI-Lite.

Prerequisites: Labs 6.2, 6.3 and 6.10, safe cabled RF practice, IIO, basic RTL and AXI-Lite. The AD9363-compatible course images may expose device name ad9361-phy; check the actual chip and receive-channel support. The **two-board RF test is the primary route**. A Rohde & Schwarz SMU200A and ATT6000 are optional calibration/independent-stimulus instruments.

This lab extends existing real measurements, particularly reports/hardware/ad9361-agc-transient-20261014.md and ad9361-agc-phase-single-board-20261014.md. Previously measured timing and phase are baseline evidence, **not new results of this lab**.

## RF bench and safety

~~~text
Board A: ZynqSDR TX1 (915 MHz, +300 kHz complex tone or framed IQ)
   -> 30 dB verified fixed RF attenuator
   -> [optional additional variable attenuator / splitter, terminated unused ports]
   -> Board B: ZynqSDR RX1, 915 MHz, 3.84 MS/s
   -> RX IIO capture + AD9361 CTRL_OUT[7:0] -> Zynq PL -> PS
~~~

Start with the TX LO off, TX at its maximum attenuation, RX at low manual gain and output disabled. Verify the attenuator's rated power, total attenuation, connector/cable condition, frequency and input limits **before** enabling TX; never connect TX directly to RX. Establish a safe input-power budget from measured/verified TX output and passive-path loss; the IIO TX attenuation setting alone is not the absolute RF output level. Disable the TX on every exit, including errors. Use an isolated conducted path, not over-the-air transmission, for initial tests.

Record in a manifest: board IDs/images, RX/TX LO, sample rate, RF bandwidth, port, TX attenuation, RX gain mode/value, waveform amplitude and crest factor, all passive S21 losses, antenna/termination state, IQ format and checksum. The existing bench measured 915 MHz, 3.84 MS/s, a +300 kHz tone and a 20 dB TX step; other profiles must be documented, not assumed. See docs/rf-safety.md and docs/iq-dataset-manifest.md.

## 1. Detecting overload: analog vs digital

- **Large LMT overload:** a peak indication from the LNA/mixer/TIA chain. An analog blocker may trip LMT even when the filtered output IQ does not clip.
- **Large/small ADC overload:** two peak thresholds in the ADC path, not interchangeable with saturation of the final 12-bit IQ words.
- **Low power:** a separate receiver signal-level condition, used in gain control.
- A flag can drop immediately after a gain change because the peak detector is reset for the configured peak-wait interval. Do **not** interpret every falling edge as an RF blocker disappearing.

According to AD9361 UG-570, setting control-output selector register 0x035 to **0x03** assigns:

| CTRL_OUT bit | RX1/RX2 event |
|---|---|
| 7 | RX1 ADC low power |
| 6 | RX1 large LMT overload |
| 5 | RX1 large ADC overload |
| 4 | RX1 small ADC overload |
| 3 | RX2 low power |
| 2 | RX2 large LMT overload |
| 1 | RX2 large ADC overload |
| 0 | RX2 small ADC overload |

Register 0x036 is the output-enable mask. An RX1-only mask is 0xF0. For RX1 AGC state and gain lock **together with the four RX1 indications**, selector 0x07 repurposes CTRL_OUT[3:0] as AGC state[2:0] and gain lock. A gain-change pulse is available under selector 0x05 (RX1 at bit 6) or 0x08 (RX1 at bit 4), but **not simultaneously with all four RX1 overload flags** using selector 0x03. Do separate repeated runs or instrument a suitable additional reference. Gain-change pulses can be tens of nanoseconds long; Linux polling cannot count them reliably.

References: [AD9361 UG-570](https://www.analog.com/media/en/technical-documentation/user-guides/AD9361_Reference_Manual_UG-570.pdf), Control Outputs, and [ADI AD9361 Linux driver](https://developer.analog.com/docs/linux/drivers/iio-transceiver/ad9361/).

## 2. Discovery and IIO-only baseline

Run on board B (adjust the IIO device name if necessary):

~~~bash
iio_info -s
iio_attr -i -c ad9361-phy voltage0 gain_control_mode
iio_attr -i -c ad9361-phy voltage0 hardwaregain
iio_reg ad9361-phy 0x035
iio_reg ad9361-phy 0x036
~~~

Save the original two register values, list the available gain-control modes and verify the RX clock/bandwidth. Read and restore gains and registers **after each run**. Configure three runs, keeping the stimulus and passive path unchanged:

~~~bash
iio_attr -i -c ad9361-phy voltage0 gain_control_mode manual
iio_attr -i -c ad9361-phy voltage0 hardwaregain 50
# Repeat with gain_control_mode slow_attack, then fast_attack.
~~~

50 dB is a previous bench reference, **not a universal safe starting gain**. Start with low gain and low input level. A readback of RX gain or RSSI is not direct evidence that LMT or ADC detected an overload. The standard IIO PHY attributes do not expose an event counter for each internal peak detector.

Use existing, non-duplicated two-board tools:

- blocks/block_11_integrated_sdr_project/python/two_board_agc_step_transient.py: continuous tone, TX attenuation step, amplitude/phase settling and IQ clipping.
- blocks/block_11_integrated_sdr_project/python/two_board_agc_ber.py: BER under static and dynamic gain changes.
- blocks/block_11_integrated_sdr_project/python/two_board_agc_frame_step.py: waveform-domain amplitude step at a specified symbol position.

First inspect each tool's --help and bench-specific IP/firmware assumptions. The TX attenuation change via Linux is not sample-synchronous; the waveform-embedded level step is reproducible by sample index. In all cases, distinguish the transmitter's own transient from the receiver AGC response using the manual-gain control run.

## 3. Verify CTRL_OUT routing before enabling it

**Do not assume a ZC702 pin map matches the custom ZynqSDR PCB.** The stored ZC702 reference HDL has gpio_status[7:0] and the XDC assigns those nets to FPGA pads, but a board-specific schematic, constraint file and loaded bitstream must establish the physical path. Inspect whether each AD9361 CTRL_OUT pin reaches Zynq PL, GPIO bank voltage, pull-ups and tri-state direction. Never assign arbitrary PS GPIO numbers based only on a reference board.

The ADI FMCOMMS2/ZC702 HDL reference maps gpio_status[7:0] to EMIO[39:32] (software GPIO 93:86 in its legacy numbering). On another board the Linux gpiochip numbering and PL wiring may differ. The reference system_top.v routes the captured status through gpio_i[39:32].

When the physical route is confirmed, capture/restore original registers and select the monitor with explicit operator approval:

~~~bash
iio_reg ad9361-phy 0x035             # save original index
iio_reg ad9361-phy 0x036             # save original output mask
# Only after verifying pins, bank voltage, and conflicts:
iio_reg ad9361-phy 0x035 0x03
iio_reg ad9361-phy 0x036 0xF0
# Restore ORIGINAL values after the experiment; do not guess them.
~~~

A control-output register read shows the **selector**, not the current hardware event levels. If the pins are not routed, record this as hardware-unavailable, complete the IIO/IQ baseline and the RTL simulation, and do not claim measured LMT/ADC flags.

## 4. Extended PL monitor

The synthesizable core in rtl/ad9361_overload_monitor.v samples eight asynchronous CTRL_OUT inputs through two flip-flops, detects rising edges, increments saturating counters and records sticky flags and last-event timestamps. rtl/ad9361_overload_monitor_axi.v provides a 32-bit AXI-Lite readout; tb/tb_ad9361_overload_monitor_axi.sv is the deterministic simulation.

| Byte offset | Access | Purpose |
|---|---|---|
| 0x00 | R | sticky event bits [7:0] |
| 0x04 | R | free-running PL clock counter |
| 0x08 | W | write bit 0 to clear event counters/sticky bits |
| 0x0C | R | synchronized current CTRL_OUT levels |
| 0x20..0x3C | R | 8 edge counters (bit 0 through 7) |
| 0x40..0x5C | R | last rising-edge timestamps (PL ticks) |

The module reports **rising transitions**, not total time over a threshold. Saturating counters do not wrap. Events initially high after reset can be counted once. Very short pulses can escape a two-flop synchronizer: characterize minimum pulse width, PL clock rate and pulse-capture requirements before claiming complete event coverage. Do not silently replace the direct monitor by a Linux GPIO polling loop.

To integrate: tap the board-verified input side of gpio_status in PL; connect clock/reset, add AXI-Lite to a spare address range through the PS AXI interconnect, assign an actual address in Vivado and record the bitstream hash. The monitor has **no hard-coded FPGA pads or AXI base address**. Do not rebuild the unrelated main modem image merely to add these experimental probes.

~~~bash
iverilog -g2012 -o /tmp/lab612_tb \
  blocks/block_06_rf_frontend_and_ad9363/rtl/ad9361_overload_monitor.v \
  blocks/block_06_rf_frontend_and_ad9363/rtl/ad9361_overload_monitor_axi.v \
  blocks/block_06_rf_frontend_and_ad9363/tb/tb_ad9361_overload_monitor_axi.sv
vvp /tmp/lab612_tb
~~~

## 5. Experiments and interpretation

1. **MGC baseline:** vary safe RF level gradually; record RX gain, IQ RMS/peak, clipping/SFDR and (if routed) LMT/ADC event counts. Repeat tone away from DC.
2. **Step response:** transmit a deterministic 10–20 dB waveform-domain step. Record IQ and event counters for each AGC mode, repeated at least three times. Report detection-to-gain-response only if their timestamps share a verified clock or synchronization reference.
3. **Blocker without IQ clipping:** move a strong tone towards/outside the useful digital channel (but inside the analog front-end passband); test whether LMT asserts while final IQ remains clean. Compare detector counters, peak/rms/SFDR and gain. This is a **hypothesis to test**, not a guaranteed result.
4. **Modem extension:** reuse the QPSK frame-step and BER tests from Block 11; optionally compare a CSS/LoRa-like burst, keeping detection/decoding metrics separate.

For a receiver-local timestamp log, use columns tick,source, where source is step, lmt, large_adc, small_adc, low_power or gain_change. The tick for step must be produced in **the same receiver clock domain**, e.g. by a documented local envelope comparator. Host-side commands on board A do not establish this. An event-only log remains useful for event counts without a step marker.

~~~bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_12_analyze_events.py --self-test
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_12_analyze_events.py \
  --events measurements/lab612_events.csv --clock-hz 100000000 \
  --json-out measurements/lab612_summary.json
~~~

## Report and acceptance

Include RF path/attenuation safety, board/firmware and HDL revisions, IIO settings, saved/restored CTRL_OUT registers, event-to-pin map backed by PCB evidence, TX waveform and exact level-step method, gain/RSSI and IQ capture metadata, plots of gain and IQ amplitude versus time, event table (or not-routed explanation), and an uncertainty/clock-alignment section. Distinguish **synthetic**, **RTL simulation**, **on-board logical level**, and **measured RF** results.

Acceptance: IIO-only baseline and no-hardware self-test pass; hardware flags may only be marked measured when physical routing is verified; RTL testbench passes before bitstream integration; no numerical hardware results are invented. The extended goal is to decide experimentally whether fast_attack protects against an observed overload without unacceptable modem degradation.

## Questions

1. Why can LMT indicate overload when output IQ has no clipping?
2. Why may an LMT/ADC flag drop before the blocker is gone?
3. Why cannot selector 0x03 expose both RX1 Gain Change and all RX1 overload flags simultaneously?
4. What uncertainty does TX-side Linux gain switching introduce?
5. How would you redesign the monitor to capture 30 ns pulses at a slower PL clock?

**Related:** Lab 6.2 (static gain/overload), Lab 6.3 (IIO), Lab 6.10 (AGC phase transition), Lab 6.11 (dBm/dBFS), and Block 11 two-board QPSK measurements.
