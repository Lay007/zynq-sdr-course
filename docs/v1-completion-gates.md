# v1.0 completion gates / Критерии завершения v1.0

Review baseline: `c7d5542`, 2026-09-19. This is a candidate completion plan,
not a released version. The existing v0.1.0 release instructions remain separate.
The five issues remain open until their hardware acceptance criteria are met.

| Issue | Software/docs/RTL evidence already available | Concrete remaining gate |
|---|---|---|
| [#48 OFDM](https://github.com/Lay007/zynq-sdr-course/issues/48) | Lab 8.14, shared fixed-point vectors, mapper/allocator, FFT/IFFT, CP, extractor, equalizer, digital loopbacks | Pilot-driven channel/phase estimation, AXI packaging/controls; synthesis resource/timing/latency report, fabric then attenuated RF loopback with BER/count, EVM/CFO, clipping and spectrum |
| [#29 gain/overload](https://github.com/Lay007/zynq-sdr-course/issues/29) | Lab 6.2 sweep analyzer, manifest/report templates and tests | Capture a controlled gain/input-level sweep, record actual RFIC, gain mode, sample rate, bandwidth, TX setting, attenuation, IQ hash and clipping/EVM; derive safe settings only from the measured range |
| [#37 NanoVNA](https://github.com/Lay007/zynq-sdr-course/issues/37) | RU/EN Lab 10.5/10.6 navigation and report templates | Replace placeholder with real bench photos; export Open/Short/Load/Thru, pads, filters and cable S-parameters with calibration/reference plane; fill SDR-frequency markers and link RF-path loss to Block 11 BER/SNR |
| [#58 AGC](https://github.com/Lay007/zynq-sdr-course/issues/58) | RU/EN Lab 6.10, IQ analyzer and synthetic controls | Fixed-gain baseline then real gain transitions; tone/data-wiped phase versus CFO, repeated phase/amplitude events, separate modem EVM/BER/PER and carrier-loop recovery with finite counts |
| [#55 mailbox](https://github.com/Lay007/zynq-sdr-course/issues/55) | Lab 5.12 / 11.38 / 11.46, mock console, AXI mailbox RTL, packet v1/CRC bridge, offline IQ RX | Address Editor base address and bitstream identity, one-board Linux echo, real uncropped IQ replay, then two-board text+sequence+CRC and at least 100 messages with failures/timeouts/PER |

## Repeatable offline preflight

```bash
python -m pytest -q
python -m ruff check blocks tools tests
python -m mkdocs build --strict
python tools/run_ofdm_rtl.py
python tools/run_block5_hdl_smoke.py
```

`run_local_ci.py` now includes all committed OFDM benches, so local preflight
covers the same datapath family as the OFDM workflows. Tests demonstrate models
and RTL simulation; they cannot substitute for synthesis timing or a board run.

## Правило закрытия

Для каждого аппаратного шага сохранить commit/bitstream hash, конфигурацию,
сырые данные с контрольными суммами, число всех попыток и причины потерь.
Не закрывать issue по synthetic self-test, констелляции без счётчиков или старой
серии от другого битстрима. Не добавлять новые крупные блоки до этих пяти этапов.
MATLAB-проверки отмечать отдельно от Python/RTL; отсутствие лицензии оставлять
явным ограничением, а не заменять неподтверждённым результатом.
