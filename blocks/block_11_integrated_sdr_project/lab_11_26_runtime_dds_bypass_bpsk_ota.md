# Lab 11.26 - Runtime PL BPSK OTA: DDS-bypass fix and first air-path validation

## Objective / Цель

**EN:** Identify why the runtime PL BPSK signal was not detectable by the external
RTL-SDR despite `tx_valid_count > 0`, apply the DDS-bypass fix, and confirm the
first OTA BPSK frame over the PL-owned AD9361 TX path.

**RU:** Установить, почему сигнал PL BPSK не обнаруживался RTL-SDR несмотря на
ненулевой `tx_valid_count`, применить исправление DDS-bypass и подтвердить
первый OTA BPSK-кадр через путь AD9361 TX, управляемый PL.

---

## Background / Предпосылки

**EN:**
Previous RTL-SDR captures (labs 11.22–11.23) showed consistent BER ≈ 35–40%
(near-random) with EVM > 500 % for all runtime PL BPSK attempts, even after:
- AXI DDS repair (`cf_axi_dds` rebind + `RATECNTRL = 3`)
- ADC driver rebind
- Fine CFO search at ±12 kHz

A preamble-correlation diagnostic confirmed no BPSK signal was present:
- Stock-shell capture: correlation ratio ≈ 5.2 (clear peak) → BER = 0
- Runtime PL captures: correlation ratio ≈ 3.5 (below the ≈ 4.7 noise threshold
  for 60 000 positions) → no signal at any coarse frequency

The strongest spectral peak at −316 kHz was identified as interference/spurious
(3 dB bandwidth did not match the expected ≈ 648 kHz BPSK occupied bandwidth).

**RU:**
Все предыдущие захваты RTL-SDR (lab 11.22–11.23) показывали BER ≈ 35–40%
(случайный уровень) при EVM > 500 % даже после:
- DDS-ремонта AXI (`cf_axi_dds` перепривязка + `RATECNTRL = 3`)
- Перепривязки драйвера АЦП
- Точного поиска CFO ±12 кГц

Диагностика корреляции преамбулы подтвердила отсутствие сигнала BPSK:
- Stock-shell захват: отношение корреляции ≈ 5.2 (чёткий пик) → BER = 0
- Захваты runtime PL: отношение ≈ 3.5 (ниже порога шума ≈ 4.7) → сигнал
  отсутствует на любой несущей

Доминирующий пик на −316 кГц идентифицирован как помеха/спур (полоса 3 дБ не
соответствует ожидаемым ≈ 648 кГц для 480 кбит/с BPSK с rolloff 0.35).

---

## Root Cause / Причина

**EN:**
After `fpga_manager` overlay reload the `cf-ad9361-dds-core-lpc` DDS core
re-initialises in **DDS-only mode** (driver default). In this mode the PL
AXI-Stream TX data path is disconnected from the AD9361 DAC: only the DDS tone
(amplitude zero by default, or whatever was last configured) is forwarded to the
DAC. The PL BPSK chain asserts `tx_valid` (counted by `axi_gpreg`), but those
samples never leave the FPGA fabric.

**RU:**
После перезагрузки оверлея `fpga_manager` ядро `cf-ad9361-dds-core-lpc`
инициализируется в режиме **DDS-only** (поведение по умолчанию драйвера). В этом
режиме путь данных AXI-Stream PL TX отключён от ЦАП AD9361: в ЦАП поступает
только выход DDS-тона (амплитуда 0 по умолчанию, или последнее конфигурированное
значение). Цепь PL BPSK подтверждает `tx_valid` (считается `axi_gpreg`), но эти
отсчёты никогда не покидают логику FPGA.

---

## Fix / Исправление

**EN:**
Call `disable_dds_tones(dds)` after connecting to the IIO context and before
starting the BPSK bringup. This writes `raw = 0` and `scale = 0` to every DDS
output channel, muting the DDS and switching the hardware mux to pass PL
AXI-Stream data through to the AD9361 DAC.

**RU:**
Вызвать `disable_dds_tones(dds)` после подключения к IIO-контексту и до запуска
BPSK. Функция записывает `raw = 0` и `scale = 0` во все выходные каналы DDS,
заглушая тон и переключая мультиплексор на передачу данных PL AXI-Stream в ЦАП
AD9361.

Files modified / Изменённые файлы:
- `lab_11_19_runtime_bridge_txrx_self_timed_bringup.py` — `disable_dds_tones`
  + DDS/ADC rebind args added
- `lab_11_22_capture_runtime_pl_rtl_monitor_wav.py` — `disable_dds_tones` added

---

## Procedure / Порядок выполнения

### Prerequisites / Предварительные условия

- Zynq SDR board at `192.168.40.1`, SSH root/analog
- RTL-SDR V3 Pro tuned to 915 MHz, gain 20–40 dB, SDR++ recording
- TX antenna and RX antenna ≤ 3 m apart, no external attenuator
- TX attenuation: −45 dB (default, RF-safe)

> **RF Safety / Безопасность:** не увеличивать TX мощность ради «увидеть сигнал».
> Для первого OTA-обнаружения использовать минимальную мощность TX.
> RX gain — ручной, AGC выключен. Burst короткий.

### Step 1 — Capture RTL-SDR monitor WAV with DDS bypass

```bash
# Start SDR++ recording at 915 MHz, 2.4 MS/s
# Then in a separate terminal:
python blocks/block_11_integrated_sdr_project/python/lab_11_22_capture_runtime_pl_rtl_monitor_wav.py \
    --rebind-runtime-dds-driver \
    --rebind-runtime-adc-driver \
    --runtime-dds-ratecntrl 3
```

**What to expect / Ожидаемый результат:**
- `disable_dds_tones: {"status": "ok"}` в выходном JSON
- `tx_valid_count > 0` (PL цепь работает)
- Сигнал BPSK должен появиться вблизи DC (≈ +2.4 кГц, как у stock-shell)

### Step 2 — Offline BER analysis

```bash
python blocks/block_11_integrated_sdr_project/python/lab_11_20_read_rtl_wav_ota_bpsk_ber.py \
    --manifest datasets/lab11_22_runtime_pl_rtl_monitor/<new_manifest>.yaml \
    --run-tag dds_bypass_v1
```

**Success criterion / Критерий успеха:**
- Отношение корреляции преамбулы > 5.0 (сигнал обнаружен)
- BER < 10 % → первое подтверждённое OTA BPSK через PL-путь
- BER = 0 → полный успех (как у stock-shell)

### Step 3 — If BER > 10 % after DDS fix

| Symptom | Likely cause | Next action |
|---|---|---|
| Signal at DC, BER 5–20 % | Residual CFO or low SNR | Increase RTL gain; try `--fine-search-hz 20000` |
| Signal at DC, BER > 30 % | Wrong waveform params | Check `symbol_rate_hz`, `samples_per_symbol` in manifest |
| No signal at DC, BER random | DDS still blocking | Check `disable_dds_tones` JSON field; try `--rebind-runtime-dds-driver` again |
| Signal off-frequency | AD9361 LO mismatch | Verify `center_frequency_hz = 915000000` in IIO |

---

## Evidence template / Шаблон доказательства

After a successful run, record the following metrics in
`docs/assets/lab1126_runtime_dds_bypass_bpsk_ota_<timestamp>_metrics.json`:

```json
{
  "lab": "11.26",
  "date": "2026-XX-XX",
  "disable_dds_tones_status": "ok",
  "selected_coarse_frequency_hz": "...",
  "total_frequency_shift_hz": "...",
  "bit_errors_total": "...",
  "bit_errors_payload": "...",
  "ber_total": "...",
  "evm_percent": "...",
  "conclusion": "First confirmed OTA BPSK frame via PL TX path"
}
```

---

---

## Follow-up diagnosis (2026-06-25) / Дополнительная диагностика

### FIFO→DAC data path verification

After applying the DDS-bypass fix, the next diagnostic confirmed the full FIFO→DAC
data path using a DMA sinusoidal tone:

**DMA tone test** (`voltage0/voltage1`, 200 kHz at full scale ±32767):

```python
# Correct IIO buffer write API (must use channel.write, not buf.read/modify):
voltage_chs = [ch for ch in dac.channels if ch.output and ch.id.startswith('voltage')]
buf = iio.Buffer(dac, N_BUF, cyclic=True)
payloads = [tone_i, tone_q, zero, zero]
for ch, samples in zip(voltage_chs, payloads):
    ch.write(buf, bytearray(samples.tobytes()), raw=True)
buf.push()
# Then set dac_data_sel=2 via devmem
```

Result: 200 kHz tone visible at **87.6 dB above RTL-SDR noise floor**, power=1663
(vs baseline 1.5). FIFO→DAC path confirmed.

**Critical API bug found:** `'voltage' in ch.id` also matches `altvoltage0..7` (DDS
control channels). Must use `ch.id.startswith('voltage')` to select only the four
sample data channels `voltage0..3`.

**Frequency inversion:** Tone appears at −197 kHz (not +200 kHz) — this is expected.
The −200 kHz convention plus the +2.7 kHz AD9361/RTL LO beat gives −197.27 kHz.

### Cyclic zero DMA buffer requirement

Setting `dac_data_sel=2` with no prior DMA data causes `util_rfifo` BRAM to output
initialization garbage → wideband noise (RTL power: 1.5 → 233, ×155 increase).

Fix: push a cyclic zero IIO buffer **before** setting `dac_data_sel=2`:

```python
zero = np.zeros(N_BUF, dtype='<i2')
buf = iio.Buffer(dac, N_BUF, cyclic=True)
for ch in voltage_chs:
    ch.write(buf, bytearray(zero.tobytes()), raw=True)
buf.push()
set_dac_sel(2)  # now safe — FIFO filled with zeros, power stays at 1.5
```

### BPSK burst confirmed reaching DAC

Burst-synchronized RTL-SDR power trace (100 μs windows):

```text
Baseline (sel=2, zero DMA): power = 1.35
Burst window (637 μs):       power = 67..225  (rising edge + burst)
Post-burst tail-loop:         power = 225..232 (273 ms)
Expected burst power:         ~249  (RRC FIR peak 12695/32767 = 38.7% -> bits[15:4]=793 DAC units)
```

**Conclusion:** BPSK signal IS reaching the DAC at the expected power level.

### RX idle timeout mechanism (explains long-window FFT miss)

`RX_IDLE_TIMEOUT_CYCLES = 1 048 576` in `bpsk_zynq_ber_top.v`. At 3.84 MHz sample
clock this is **273 ms**. `tx_path_active` stays HIGH from burst start until either:

1. BER counter receives all 306 bits (loopback/OTA with AD9361 RX active → ~1 ms)
2. OR RX idle timeout fires (no AD9361 RX data → 273 ms)

During the 273 ms window after the 637 μs burst, `bpsk_valid=0` but
`select_bpsk=1`. The `util_rfifo` FIFO (256 entries, 2^8) was overwritten 9× during
the burst; the last 256 BPSK tail samples cycle at 66.7 μs period for 273 ms.

**Why long-FFT analysis missed the signal:**

- With AD9361 RX active: tx_path_active ≈ 1 ms, so burst duty cycle = 1/150 = 0.7%
  → time-averaged RTL power increases from 1.5 to ~3.2 (indistinguishable)
- BPSK spread across 480 kHz bandwidth: in a per-bin FFT the signal is −65 dB below
  its total power → below the RTL noise floor per bin

**Correct detection method:** burst-synchronized power trace (100 μs windows) shows
clear 260 ms elevated window ≈ 273 ms RX timeout. The first 637 μs is the real BPSK
signal; the remainder is tail-loop artifact.

### `din_enable_X` architecture clarification

A previous hypothesis that `upack/fifo_rd_enable → axi_ad9361_dac_fifo/din_enable_X`
was blocking BPSK writes is incorrect. In `util_rfifo.v`:

- `din_enable_X` is an **OUTPUT** from the FIFO (backpressure to upack)
- `din_valid_in_X` is the **INPUT** write enable (driven by mux `fifo_valid`)
- For `M_MEM_RATIO=1`: `din_wr = din_valid_in_0` (write gate, not din_enable_X)

The TCL overlay correctly disconnects and reconnects `din_valid_in_0..3` via the mux.
`din_enable_X` is not disconnected (it stays as backpressure signal to upack).

### Evidence

`docs/assets/lab1126_bpsk_dac_path_confirmed_20260625.json`

---

---

## First OTA RF evidence via antennas (2026-06-25) / Первое подтверждение сигнала через антенны

### Setup / Установка

- Run tag: `diag_overlay` (`--no-reboot-after`; board kept in overlay state)
- TX: Zynq AD9361 → TX1A antenna, attenuation −50 dB (safe floor)
- RX: RTL-SDR V3 Pro → RX antenna, gain 20 dB (gain10=200), 2.4 MS/s, center 915 MHz
- Distance TX→RX: free air (same room), no cable / no attenuator
- Board config: `configure_ad9361_bpsk` OK, `disable_dds_tones` OK, `dma_zero_buffer` OK (65 536 samples)
- 3 BPSK bursts, 100-poll × 30 ms gap ≈ 3.1 s between each

### Power trace confirms BPSK reaching the air / Трассировка мощности подтверждает выход BPSK в эфир

RTL-SDR WAV (10.81 s, 2.4 MS/s):

| Event | Time, s | Power (ADC²) | Elevation vs baseline |
| --- | --- | --- | --- |
| Baseline (silence) | 0–0.90 | 46 000 | — |
| Burst 1 window | 0.95–1.22 | 474 000 | +10.1 dB |
| Burst 2 window | 4.30–4.55 | ~474 000 | +10 dB |
| Burst 3 window | 7.70–7.95 | ~474 000 | +10 dB |

Each elevated window is ≈ 250 ms ≈ `RX_IDLE_TIMEOUT_CYCLES / 3.84 MHz` = 273 ms (RX
idle timeout; burst itself is 637 μs). Burst-start resolved to t = 0.951 s (1 ms
resolution scan).

### Spectrum analysis / Спектральный анализ

After coarse −2 800 Hz shift and DC-offset removal (`analysis_capture -= mean`):

- RRC-shaped spectrum visible at ±250 kHz bandwidth
- Rolloff visible matching α = 0.35, symbol rate 480 kHz
- BPSK signal ≈ **+10 dB above noise floor**
- LO carrier residual at +2.8 kHz: **48.9 dB above noise** (AD9361 × RTL-SDR LO beat)

### Why BER demodulation fails via RTL-SDR / Почему BER через RTL-SDR не работает

```text
Burst duration:          637 μs = 2 448 samples @ 3.84 MHz
RX idle tail-loop:       273 ms = 1 047 552 samples
Tail/burst ratio:        430×
LO carrier at 2.8 kHz:  48.9 dB above noise (in-band, beats preamble correlator)
```

`crop_active_window` always selects the 273 ms tail-loop (highest sustained power,
same level as burst but 430× longer). Even with `--force-analysis-window-start` to
pin the window to t = 0.951 s, the 637 μs burst is 0.23 % of any reasonable analysis
window → preamble correlator fails. RTL-SDR hardware BER counter is not available.

**Conclusion:** RTL-SDR confirms BPSK signal exists in the air (spectrum shape, power
elevation). Quantitative BER via RTL-SDR with this architecture is inconclusive
(BER ≈ 36 %, preliminary). Final BER measurement requires AD9361 RX loopback.

### Evidence files / Файлы доказательств

- `docs/assets/lab1122_runtime_pl_rtl_monitor_diag_overlay.json` — runtime JSON (3 bursts OK, timed_out_observed=True)
- `docs/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_diag_overlay_ota_carrier_removed_metrics.json` — spectrum after carrier removal (BER 35.6 %, EVM 602 %)
- `docs/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_diag_overlay_ota_carrier_removed_baseband_spectrum.png` — RRC spectrum shape visible

### Next step / Следующий шаг

Run with AD9361 RX loopback (TX antenna → RX antenna close-range, or short cable) so
the hardware BER counter closes the loop in ≈ 1 ms instead of 273 ms. This eliminates
the tail-loop problem and allows proper preamble correlation.

---

---

## Hardware BER counter root cause and RTL fix (2026-06-25)

### Symptom / Симптом

After switching to the AD9361 RX loopback (TX1/RX1 antennas touching on the board),
the PL hardware BER counter consistently reported **BER ≈ 46–50 %** across all runs
with `start_offset` 59–66 and both OTA and digital loopback modes:

```text
v1:  281 bits, 131 errors, BER = 46.6 %,  rx_valid_count = 2982
v3:  281 bits, 141 errors, BER = 50.2 %,  rx_valid_count = 2982
dig: 281 bits, 131 errors, BER = 46.6 %,  capture_peak  = 1126
```

### Root cause / Причина

`bpsk_ynq_ber_gpreg_bridge.v` passes `capture_in_valid` **ungated** to the timing
sampler:

```verilog
// BUG — before fix:
.rx_valid(capture_in_valid),   // always 1 from ADC streaming
```

The `capture_in_valid` signal from the AD9361 ADC block-design path is **always
asserted** as soon as the ADC driver is active (continuous streaming). As a result,
`sample_index` inside `bpsk_symbol_timing_sampler` starts counting from the moment
the ADC driver is rebound — **seconds before the frame_start pulse**.

At `frame_start`, `sample_index` ≈ `T_config × 3 840 000 mod 65 536` ≈ 63 488 (for
`T_config ≈ 5 s`). The timing sampler condition
`((sample_index − start_offset) % SPS == 0)` is already satisfied immediately, so
all 281 symbol samples are emitted within the first ≈ 300 µs after frame_start —
**before any TX output can propagate to the RX chain**. The BER counter receives 281
near-zero (silence) samples → hard decisions are random → BER ≈ 50 %.

Key facts:

- `3 840 000 mod 8 = 0`, so `sample_index mod SPS` is **constant** across all runs
  regardless of ms-level Python timing jitter → changing `start_offset` by 1..7
  moves the phase but cannot escape the pre-TX firing window.
- `rx_valid_count = 2982` reflects the time from `frame_start` to TX completion
  (~2248 BPSK samples + TX pipeline), not RX preamble reception.
- `frame_bit_count_cfg` is latched **only** at `start_edge`, so before the first
  start pulse `symbol_count = 0` (safe: timing sampler never fires before the first
  frame_start). The bug triggers because `sample_index` has advanced to ~63 488 by
  then, so all 281 firings happen in the pre-TX silence window.

### RTL fix applied / Применённое RTL-исправление

Gate `rx_valid` with `tx_path_active_sample` in
`hardware/7020_ad936x_sdr/hdl/course_bpsk_fmcomms2_zc702/bpsk_ynq_ber_gpreg_bridge.v`:

```verilog
// FIXED (one line change):
.rx_valid(capture_in_valid && tx_path_active_sample),
```

`tx_path_active_sample` is set to 1 at `start_edge` (same cycle as
`start_pulse_sample`) and cleared when `core_done` or `core_timed_out`. After ADC
rebind, `sample_resetn` clears `tx_path_active_sample` to 0. Therefore:

- Before `frame_start`: `rx_valid = 0` → `sample_index` stays at 0 regardless of
  how long Python waits between rebind and start pulse.
- At `frame_start`: `tx_path_active_sample = 1` → `rx_valid = 1` →
  `sample_index` starts from 0, exactly as in the testbench
  (`LOOPBACK_SAMPLE_DELAY = 24`, `start_offset = 62`, BER = 0 %).

With this fix the required `start_offset` satisfies `start_offset ≈ D_total`, where
`D_total` is the combined TX + propagation + RX pipeline sample delay. The
testbench uses `start_offset = 62` with a 24-sample loopback; for OTA with adjacent
antennas, `start_offset = 62` should also work, with fine-tuning ±8 if needed.

### Rebuild and test / Пересборка и тест

The fix requires a Vivado bitstream rebuild (Vivado 2021.1 at `g:/Xilinx/Vivado/`).
After rebuild:

1. Convert output `.bit` to word-swapped `.bit.bin`:

   ```bash
   python hardware/7020_ad936x_sdr/boot/build_system_bit_bin.py \
       tmp/vendor_xpr_course_overlay/zc702/zc702.runs/impl_1/bridge_txrx_mux.bit \
       --output tmp/bridge_txrx_mux.wordswap.bit.bin
   ```

2. Run OTA BER test with TX1/RX1 antennas adjacent:

   ```bash
   python blocks/block_11_integrated_sdr_project/python/lab_11_22_capture_runtime_pl_rtl_monitor_wav.py \
       --rebind-runtime-adc-driver \
       --start-offset 62
   ```

3. Expected outcome: `received_bits = 281`, `total_errors = 0`, `payload_errors = 0`,
   BER = 0 %. If BER > 0 %, scan `start_offset` in ±8 increments to find
   the correct OTA pipeline delay alignment.

Evidence files will be saved to `docs/assets/lab1122_runtime_bridge_txrx_*_ber0*.json`.

---

## Resolution and remaining limit (2026-06-26) / Итог и оставшееся ограничение

The 2026-06-25 "rebuild and test with `start_offset = 62`" plan above did not work as
written, and the reason turned out to be a build-flow defect that invalidated every
prior OTA result:

1. **Stale block design (the real blocker).** The deployed bitstream
   (`tmp/bridge_txrx_mux.wordswap.bit.bin`, old md5 `020dd715…`) was built from a
   `system.bd` that predated the bridge RTL refactor. Its `axi_gpreg` wiring used the
   *old* interface (separate `gp_payload_errors`, no `gp_adc_input_debug`/
   `gp_capture_debug`), so the host register decode never matched the silicon — that
   is why earlier runs reported impossible values like `total_errors=0, payload_errors=148`.
   The out-of-context IP checkpoint cache also hid the RTL fixes: `reset_run synth_1`
   reused the cached `.dcp`, so neither fix ever reached hardware. Rebuilding the BD from
   the current `course_overlay_injection.tcl` (global synthesis, IP cache disabled)
   produced a correct bitstream (new md5 `fb6a0119…`).

2. **Timing-sampler single-shot bug (fixed).** `bpsk_zynq_ber_top` reset the RX matched
   filter + timing sampler only on the global `rst`, so after one frame the sampler
   stayed exhausted (`emitted_symbols == symbol_count`) and back-to-back attempts
   recovered zero symbols. Fixed with `rx_chain rst = rst || frame_start`; guarded by
   `tb_bpsk_zynq_ber_top_multiframe.v` in the Block-5 smoke suite.

3. **Sample-format handling (corrected).** `cf-ad9361-lpc` reports
   `in_voltageN_type = le:S12/16>>0` — the fabric tap is already signed two's-complement,
   so the bridge now feeds `capture_in_*` straight to the RX chain (the old
   offset-binary conversion was wrong for a signed tap).

**Result after all three fixes:** the PL BER path is now alive — it locks and counts
full 281-bit frames OTA and in AD9361 coherent digital loopback (previously it only
timed out or returned stale garbage). But BER does **not** reach 0: sweeping
`start_offset` 20–220 × decision-mode {I, Q} bottoms out at ≈ 39–42 %
(`total_errors ≈ 110–117 / 281`) with a broad shallow minimum near `start_offset ≈ 150–175`
and **no sharp alignment dip**.

Two candidate causes were ruled out: carrier offset (coherent loopback has none, same
floor) and sample format (the fix above was BER-neutral). A broad shallow minimum with no
sharp dip looked like a small samples-per-symbol error / timing drift over the 281-symbol
burst, which a fixed-phase decimator cannot track.

**A Gardner timing-recovery loop was therefore built, verified and tested — and it does
NOT fix the floor.** The loop (sign-Gardner TED + linear interpolator + decrementing NCO +
PI filter, `blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_timing_recovery.v`, enabled via
`bpsk_rx_bit_recovery_chain TIMING_RECOVERY=1`) reaches BER 0 in full-chain simulation on a
deliberately drifted SPS=8.03 burst where the fixed-phase sampler floors at 15 errors, and
it closes hardware timing (multicycle-path in `course_overlay_timing.xdc`). But on the
board the loopback BER floor is **unchanged at ~42 %** (best te≈119/281 at offset 149),
with `recovered_valid_count = 281` (the loop does run and emit symbols). So the dominant
hardware impairment is **not** a samples-per-symbol/timing drift after all — most likely
AD9361 DAC/ADC FIR-chain ISI / RRC pulse distortion (or a digital-loopback artifact).

Pinning it down is still blocked by instrumentation: the `cf-ad9361-lpc` RX DMA refill
fails (`[Errno 110]`) under the `bridge_txrx_mux` overlay, and the RTL-SDR witness sees only
noise at the RF-safe −50 dB TX. **BER = 0 needs a working raw-RX capture** (fix the overlay
RX DMA, add an in-fabric raw-sample debug tap, or a cabled attenuator + stronger TX for the
RTL-SDR) **to measure the actual distortion**, then likely an AD9361 FIR-passthrough or an
equaliser — tracked as follow-up work. The Gardner timing-recovery block is kept (it is the
correct receiver and tracks genuine clock drift; see Lab 5.8b), just not the fix here.

---

## Related labs / Связанные лабораторные работы

- [Lab 11.19](lab_11_19_runtime_bridge_txrx_self_timed_bringup.md) — Runtime self-timed bring-up (DDS bypass now included)
- [Lab 11.22](lab_11_22_capture_runtime_pl_rtl_monitor_wav.md) — RTL-SDR monitor capture (DDS bypass now included)
- [Lab 11.24](lab_11_24_capture_dds_tone_rtl_monitor_wav.md) — DDS tone reference (confirms DDS repair)
- [Lab 11.25](lab_11_25_stock_vs_runtime_dds_tone_sweep.md) — DDS isolation evidence
