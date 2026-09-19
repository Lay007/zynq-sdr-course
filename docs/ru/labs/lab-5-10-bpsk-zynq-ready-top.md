# Лабораторная 5.10 — BPSK BER верхнего уровня, готовый для Zynq

## Цель

Обернуть детерминированную кадровую BPSK-цепочку в управляющий верхний уровень, который намного ближе к будущему пути интеграции с Zynq:

```text
start -> источник бит кадра -> кадровая цепочка TX -> внешняя граница отсчётов TX
                                                   -> внешняя граница отсчётов RX -> восстановление RX -> счётчик BER -> done
```

Работа оставляет источник BPSK-кадра и проверку BER внутри логики, обращённой к FPGA, и выводит наружу границу TX/RX в домене отсчётов для будущего подключения AD9363, FIFO или DMA.

## Исполняемый HDL-пакет

| Файл | Назначение |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bit_source.v` | детерминированный источник кадра на ROM с семантикой `start/busy/done` |
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_ber_counter.v` | сравнивает восстановленные биты с тем же ROM кадра и считает полный/payload BER |
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_zynq_ber_top.v` | обёртка верхнего уровня вокруг источника, цепочек TX/RX и проверки BER |
| `blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.v` | самопроверяющийся testbench loopback верхнего уровня |

Запуск из корня репозитория:

```bash
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_framed_loopback_vectors.py
python blocks/block_05_fpga_hdl_flow/python/generate_bpsk_rrc_tx_fir_vectors.py

iverilog -g2012 \
  -o blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.out \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_mapper.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_upsampler_8x.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_tx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rrc_rx_fir.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_symbol_timing_sampler.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_hard_decision.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_framed_tx_chain.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_rx_bit_recovery_chain.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bit_source.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_ber_counter.v \
  blocks/block_05_fpga_hdl_flow/rtl/bpsk_zynq_ber_top.v \
  blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.v

vvp blocks/block_05_fpga_hdl_flow/tb/tb_bpsk_zynq_ber_top.out
```

Ожидаемый результат:

```text
PASS: bpsk_zynq_ber_top completed without errors
```

## Контракт верхнего уровня

Новый верхний уровень намеренно невелик, но ориентирован на железо:

| Группа сигналов | Роль |
|---|---|
| `start`, `busy`, `done` | однократный запуск кадра и статус завершения |
| `frame_bit_count`, `preamble_count`, `start_offset` | детерминированные управляющие входы, выведенные из общего пакета Блока 11 |
| `tx_valid`, `tx_i`, `tx_q` | поток отсчётов TX к будущему ЦАП, FIFO или тракту TX AD9363 |
| `rx_valid`, `rx_i`, `rx_q` | поток отсчётов RX от будущего АЦП, FIFO или тракта RX AD9363 |
| `received_bits`, `total_errors`, `payload_errors` | компактный интерфейс результата BER |

## Почему этот этап важен

Предыдущий testbench loopback доказал, что DSP-цепочка работает. Эта работа добавляет системную структуру, необходимую, прежде чем проект платы сможет её использовать:

1. детерминированный источник кадра вместо прямого цикла стимулов в testbench;
2. счётчик BER, который позже можно отобразить в память или отдать в ПО;
3. чистый шов в домене отсчётов, к которому подключатся AD9363 или AXI/DMA;
4. явная семантика завершения верхнего уровня для автоматизированных аппаратных тестов.

## Общий контракт кадра

Верхний уровень использует:

| Общий артефакт | Роль |
|---|---|
| `blocks/block_05_fpga_hdl_flow/rtl/bpsk_frame_bits.mem` | детерминированные биты кадра для источника и для проверки BER |
| `blocks/block_05_fpga_hdl_flow/tb/bpsk_framed_loopback_meta.txt` | начальное смещение, число бит, число символов преамбулы и допущения об очистке |

Так биты источника, эталон BER и метаданные тайминга остаются синхронизированными между отдельным loopback и верхним уровнем, готовым для Zynq.

## Стратегия testbench

Самопроверяющийся testbench соединяет:

```text
выходы отсчётов TX верхнего уровня -> входы отсчётов RX верхнего уровня
```

Затем проверяет:

- `start` запускает ровно один кадр;
- `busy` становится активным на время прогона и сбрасывается в конце;
- `done` устанавливается только после завершения всего пакета;
- счётчики BER сообщают ноль полных и payload-ошибок.

## Первая интерпретация с точки зрения железа

Этот верхний уровень всё ещё синтетический, но теперь структурно совпадает с будущим трактом платы:

```text
источник кадра / управление -> отсчёты TX -> AD9363 TX -> RF-тракт -> AD9363 RX -> отсчёты RX -> счётчики BER
```

Именно сюда на следующем шаге подключаются регистры AXI-Lite, DMA, управление BRAM или специфичная для платы логика тактов и сброса.

## Чек-лист отчёта

- [ ] Объяснено значение `start`, `busy` и `done`.
- [ ] Показано, как задаются `frame_bit_count`, `preamble_count` и `start_offset`.
- [ ] Показаны выведенные границы отсчётов TX и RX.
- [ ] Приведены итоговые значения счётчиков BER.
- [ ] Указан следующий шаг интеграции: регистры AXI-Lite, подключение DMA или соединение с AD9363.

## Шаблон инженерного вывода

```text
Детерминированная цепочка BPSK-модема теперь имеет верхний уровень, готовый для Zynq, с однократным интерфейсом запуска, явным статусом завершения и счётчиками BER.
Источник кадра и проверка BER используют один и тот же ROM с битовой последовательностью, поэтому тест остаётся детерминированным.
Это правильный якорь интеграции перед подключением проекта к управлению AXI, DMA или тракту отсчётов AD9363.
```
