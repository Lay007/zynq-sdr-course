# Лабораторная 5.4 — Обёртка AXI-Stream для IQ-потока

## Цель

Перейти от учебного valid-only интерфейса к интерфейсу AXI-Stream, который ближе к реальному Vivado/Zynq потоку данных.

## Что выполняется

В работе студент:

1. изучает сигналы `tvalid`, `tready`, `tdata`, `tlast`;
2. разбирает упаковку IQ-отсчётов в 32-битное слово;
3. запускает RTL wrapper `axis_iq_passthrough`;
4. проверяет работу backpressure;
5. анализирует сохранение `tdata` и `tlast`.

## Результат

После выполнения работы должны быть получены:

- AXI-Stream style wrapper;
- self-checking testbench;
- VCD waveform;
- PASS/FAIL лог симуляции;
- понимание handshaking-правила `tvalid && tready`.

## Что приложить к отчёту

- таблицу AXI-Stream сигналов;
- формат упаковки IQ в `tdata`;
- пример backpressure;
- лог успешной симуляции;
- вывод о применимости wrapper для FIR/mixer блоков.

## Подробная техническая часть

--8<-- "blocks/block_05_fpga_hdl_flow/lab_5_4_axis_wrapper.md"
