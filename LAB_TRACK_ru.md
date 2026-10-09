# Маршруты обучения

В курсе больше сотни лабораторных, а оборудование у всех разное. Выберите маршрут по тому, что у вас
есть; каждый маршрут входит в следующий, поэтому сделанное на раннем маршруте не пропадает.
Лабораторные выполняются в указанном порядке.

| Маршрут | Что нужно | Что покрывает |
|---|---|---|
| A. Только ноутбук | Python (`python tools/tasks.py install`); Icarus Verilog начиная с шага A5 | DSP, дискретизация, фиксированная точка, модуляция и синхронизация, симуляция RTL и реальные записи, которые лежат в репозитории |
| B. + RTL-SDR | приёмник RTL-SDR (примерно по цене учебника) и антенна | собственные записи эфира |
| C. + плата Zynq | плата Zynq-7020 + AD9363, кабели, аттенюаторы | передача, FPGA-приёмник на кристалле, линия между двумя платами |
| D. + измерительные приборы | NanoVNA, RF-аттенюаторы | S-параметры и измерения компонентов |

MATLAB / Simulink везде необязательны: лабораторные, где они упоминаются, выполняются и на Python. Единственное исключение — Лабораторная 4.4, это работа в Simulink; без лицензии её можно пропустить.

## Маршрут A — только ноутбук

**A0. Ориентация.** Прочитайте блок 1: [Введение в SDR](/zynq-sdr-course/ru/block01/01-theory-intro/), [Подготовка программного окружения](/zynq-sdr-course/ru/block01/02-software-setup/), [Аппаратная база курса](/zynq-sdr-course/ru/block01/03-hardware-overview/), [Мостик от модели к плате](/zynq-sdr-course/ru/block01/04-model-to-hardware-bridge/), [Метрики качества сигнала: FFT, SNR, EVM и BER](/zynq-sdr-course/ru/block01/15-signal-metrics/), [FFT и спектральный анализ](/zynq-sdr-course/ru/block01/16-fft-spectral-analysis/), [Энергетический бюджет радиолинии в SDR](/zynq-sdr-course/ru/block01/17-link-budget/), [Эффекты фиксированной точки в DSP и FPGA](/zynq-sdr-course/ru/block01/18-fixed-point-effects/).

**A1. Сигналы, дискретизация и спектры**

- [Лабораторная 2.1](/zynq-sdr-course/ru/labs/lab-2-1-sampling-axis-and-interpretation/) — Частотная ось дискретизации и интерпретация
- [Лабораторная 2.2](/zynq-sdr-course/ru/labs/lab-2-2-aliasing-sweep/) — Развёртка алиасинга
- [Лабораторная 2.3](/zynq-sdr-course/ru/labs/lab-2-3-iq-interpretation-and-mirroring/) — Интерпретация I/Q и mirrored spectrum
- [Лабораторная 3.1](/zynq-sdr-course/ru/labs/lab-3-1-fft-windows/) — Оконные функции БПФ и спектральная утечка
- [Лабораторная 3.2](/zynq-sdr-course/ru/labs/lab-3-2-fir-low-pass/) — FIR-фильтр нижних частот для IQ-данных
- [Лабораторная 3.3](/zynq-sdr-course/ru/labs/lab-3-3-digital-mixing/) — Цифровое смешение и перенос частоты
- [Лабораторная 3.4](/zynq-sdr-course/ru/labs/lab-3-4-decimation/) — Децимация с антиалиасинговым фильтром
- [Лабораторная 3.5](/zynq-sdr-course/ru/labs/lab-3-5-fft-complexity/) — Сложность FFT и selected-bin detection
- [Лабораторная 3.6](/zynq-sdr-course/ru/labs/lab-3-6-convolution-correlation/) — Свёртка и корреляция в SDR
- [Лабораторная 3.7](/zynq-sdr-course/ru/labs/lab-3-7-window-tradeoffs/) — Окна FFT и обнаружение слабых сигналов

**A2. Реальные записи без оборудования.** В репозитории лежат настоящие записи RTL-SDR и платы; эти лабораторные их читают.

- [Лабораторная 9.1](/zynq-sdr-course/ru/labs/lab-9-1-iq-file-format-and-metadata/) — Формат IQ-файла и metadata
- [Лабораторная 9.2](/zynq-sdr-course/ru/labs/lab-9-2-read-ci16-iq-and-analyze/) — Чтение CI16 IQ и анализ спектра
- [Лабораторная 9.3](/zynq-sdr-course/ru/labs/lab-9-3-multi-format-iq-reader/) — Мультиформатный IQ reader
- [Лабораторная 9.4](/zynq-sdr-course/ru/labs/lab-9-4-read-wav-iq-and-analyze/) — Чтение WAV IQ и офлайн-анализ
- [Лабораторная 9.5](/zynq-sdr-course/ru/labs/lab-9-5-synthetic-qpsk-replay-analysis/) — Synthetic QPSK replay and constellation analysis
- [Лабораторная 6.4](/zynq-sdr-course/ru/labs/lab-6-4-synthetic-rf-capture-analysis/) — Анализ синтетической RF IQ-записи
- [Лабораторная 6.7](/zynq-sdr-course/ru/labs/lab-6-7-zero-if-artifacts/) — Артефакты zero-IF: DC-составляющая, зеркальный канал и tune offset

**A3. Фиксированная точка**

- [Лабораторная 4.1](/zynq-sdr-course/ru/labs/lab-4-1-fixed-point-fir/) — FIR-фильтр в fixed-point арифметике
- [Лабораторная 4.2](/zynq-sdr-course/ru/labs/lab-4-2-fixed-point-digital-mixer/) — Цифровой смеситель в fixed-point арифметике
- [Лабораторная 4.3](/zynq-sdr-course/ru/labs/lab-4-3-bpsk-fixed-point-chain/) — BPSK-цепочка в фиксированной точке
- [Лабораторная 4.4](/zynq-sdr-course/ru/labs/lab-4-4-bpsk-simulink-and-ber/) — BPSK-цепочка в Simulink и идеальная кривая BER от SNR

**A4. Тракты TX/RX, модуляция и синхронизация**

- [Лабораторная 7.1](/zynq-sdr-course/ru/labs/lab-7-1-tx-rx-chain-architecture/) — Архитектура TX/RX-тракта
- [Лабораторная 7.2](/zynq-sdr-course/ru/labs/lab-7-2-duc-ddc-frequency-translation/) — Частотный перенос DUC/DDC
- [Лабораторная 7.3](/zynq-sdr-course/ru/labs/lab-7-3-tx-rx-loopback-metrics/) — Метрики TX/RX loopback
- [Лабораторная 7.4](/zynq-sdr-course/ru/labs/lab-7-4-packet-receiver-detection/) — Приёмная цепочка пакетов и обнаружение кадра
- [Лабораторная 7.5](/zynq-sdr-course/ru/labs/lab-7-5-cic-decimator/) — CIC-дециматор для SDR-приёмника
- [Лабораторная 8.1](/zynq-sdr-course/ru/labs/lab-8-1-cfo-estimation-correction/) — Оценка и компенсация частотного рассогласования CFO
- [Лабораторная 8.2](/zynq-sdr-course/ru/labs/lab-8-2-phase-offset-correction/) — Оценка и коррекция фазового смещения
- [Лабораторная 8.3](/zynq-sdr-course/ru/labs/lab-8-3-timing-recovery/) — Восстановление символьной синхронизации
- [Лабораторная 8.4](/zynq-sdr-course/ru/labs/lab-8-4-end-to-end-sync-chain/) — Полная цепочка синхронизации
- [Лабораторная 8.5](/zynq-sdr-course/ru/labs/lab-8-5-ofdm-mini-link/) — Мини-цепочка OFDM (CP, пилоты, синхронизация, эквализация)
- [Лабораторная 8.6](/zynq-sdr-course/ru/labs/lab-8-6-channel-coding-ber-comparison/) — Сравнение BER помехоустойчивого кодирования с перемежением
- [Лабораторная 8.7](/zynq-sdr-course/ru/labs/lab-8-7-snr-vs-ber-traps/) — SNR недостаточно: ловушки BER и EVM
- [Лабораторная 8.8](/zynq-sdr-course/ru/labs/lab-8-8-qpsk-modem-impairments/) — QPSK-модем, искажения и BER
- [Лабораторная 8.9](/zynq-sdr-course/ru/labs/lab-8-9-qpsk-carrier-recovery/) — Восстановление несущей QPSK (петля Костаса, управляемая решениями)
- [Лабораторная 8.10](/zynq-sdr-course/ru/labs/lab-8-10-ofdm-papr-clipping/) — OFDM: PAPR, ограничение амплитуды и расширение спектра
- [Лабораторная 8.11](/zynq-sdr-course/ru/labs/lab-8-11-16qam-tradeoffs/) — 16-QAM: BER, EVM и ограничения реализации
- [Лабораторная 8.12](/zynq-sdr-course/ru/labs/lab-8-12-gfsk-bt-ber/) — GFSK: BT, полоса и BER
- [Лабораторная 8.13](/zynq-sdr-course/ru/labs/lab-8-13-dsss-processing-gain/) — DSSS: захват и processing gain
- [Лабораторная 8.20](/zynq-sdr-course/ru/labs/lab-8-20-css-waveform/) — CSS: chirp-сигнал и кодирование символа
- [Лабораторная 8.21](/zynq-sdr-course/ru/labs/lab-8-21-css-dechirp-fft/) — CSS: dechirp и FFT-детектор
- [Лабораторная 8.22](/zynq-sdr-course/ru/labs/lab-8-22-css-packet-sync-per/) — Пакетная CSS-синхронизация и PER
- [Лабораторная 6.2](/zynq-sdr-course/ru/labs/lab-6-2-gain-staging-and-overload/) — Настройка усиления и контроль перегрузки
- [Лабораторная 6.5](/zynq-sdr-course/ru/labs/lab-6-5-rf-impairment-calibration/) — Калибровка RF-искажений приёмника (DC, дисбаланс IQ, утечка LO)

**A5. Симуляция RTL** (установите Icarus Verilog; Vivado не нужен)

- [Лабораторная 5.1](/zynq-sdr-course/ru/labs/lab-5-1-streaming-interface-and-testbench/) — Потоковый интерфейс и тестбенч
- [Лабораторная 5.2](/zynq-sdr-course/ru/labs/lab-5-2-fir-rtl-mapping/) — Отображение FIR-фильтра в RTL
- [Лабораторная 5.3](/zynq-sdr-course/ru/labs/lab-5-3-nco-mixer-rtl/) — RTL-смеситель IQ на основе NCO
- [Лабораторная 5.4](/zynq-sdr-course/ru/labs/lab-5-4-axis-wrapper/) — Обёртка AXI-Stream для IQ-потока
- [Лабораторная 5.5](/zynq-sdr-course/ru/labs/lab-5-5-float-fixed-rtl-comparison/) — Сравнение float, fixed-point и RTL
- [Лабораторная 5.6](/zynq-sdr-course/ru/labs/lab-5-6-bpsk-rrc-tx-fir-rtl/) — RTL FIR формирующего RRC-фильтра BPSK TX
- [Лабораторная 5.7](/zynq-sdr-course/ru/labs/lab-5-7-bpsk-upsampler-8x/) — BPSK-повышающий дискретизатор символов 8x
- [Лабораторная 5.8](/zynq-sdr-course/ru/labs/lab-5-8-bpsk-rx-bit-recovery/) — Согласованный фильтр BPSK RX и восстановление бит
- [Лабораторная 5.9](/zynq-sdr-course/ru/labs/lab-5-9-bpsk-framed-loopback/) — Кадровый BPSK TX/RX loopback верхнего уровня
- [Лабораторная 5.10](/zynq-sdr-course/ru/labs/lab-5-10-bpsk-zynq-ready-top/) — BPSK BER верхнего уровня, готовый для Zynq
- [Лабораторная 8.14](/zynq-sdr-course/ru/labs/lab-8-14-ofdm-rtl-chain/) — OFDM RTL: от mapper до эквализированного loopback

**A6. Системное проектирование и отчёты**

- [Лабораторная 10.1](/zynq-sdr-course/ru/labs/lab-10-1-rc-filter/) — Пассивный RC-фильтр
- [Лабораторная 10.2](/zynq-sdr-course/ru/labs/lab-10-2-attenuator-pad/) — Простой аттенюатор
- [Лабораторная 10.3](/zynq-sdr-course/ru/labs/lab-10-3-rf-measurement-safety-checklist/) — Checklist безопасности RF-измерений
- [Лабораторная 10.4](/zynq-sdr-course/ru/labs/lab-10-4-kicad-schematic-mini-project/) — Мини-проект схемы в KiCad
- [Лабораторная 11.1](/zynq-sdr-course/ru/labs/lab-11-1-project-requirements-and-architecture/) — Требования проекта и системная архитектура
- [Лабораторная 11.2](/zynq-sdr-course/ru/labs/lab-11-2-end-to-end-simulation-package/) — Сквозной пакет симуляции
- [Лабораторная 11.3](/zynq-sdr-course/ru/labs/lab-11-3-fpga-rf-integration-checklist/) — Чек-лист интеграции FPGA/RF
- [Лабораторная 11.4](/zynq-sdr-course/ru/labs/lab-11-4-final-measurement-report/) — Итоговый измерительный отчёт
- [Лабораторная 11.5](/zynq-sdr-course/ru/labs/lab-11-5-axi-dma-latency-jitter/) — Задержка и джиттер конвейера AXI DMA
- [Лабораторная 11.6](/zynq-sdr-course/ru/labs/lab-11-6-measurement-uncertainty-budget/) — Бюджет неопределённости измерений и отчётность
- [Проект 12.1](/zynq-sdr-course/ru/labs/project-12-1-qpsk-modem-final-project/) — Итоговый проект: QPSK-модем
- [Проект 12.3](/zynq-sdr-course/ru/labs/project-12-3-fpga-dsp-block-final-project/) — Итоговый проект: DSP-блок для FPGA

## Маршрут B — добавить RTL-SDR

Всё из маршрута A, плюс:

- [Лабораторная 1.0](/zynq-sdr-course/ru/labs/lab-1-0-first-rtl-sdr-observation/) — Первое наблюдение эфира через RTL-SDR
- [Лабораторная 6.1](/zynq-sdr-course/ru/labs/lab-6-1-frequency-plan/) — Частотный план RF-эксперимента
- [Проект 12.2](/zynq-sdr-course/ru/labs/project-12-2-rf-capture-analysis-final-project/) — Итоговый проект: анализ RF-захвата

Запишите собственный WAV в Лабораторной 1.0 и проанализируйте его скриптами Лабораторных 9.4 и 6.4 вместо записей из репозитория.

## Маршрут C — добавить плату Zynq

Всё из маршрутов A и B, плюс сама плата:

- [Лабораторная 1.1](/zynq-sdr-course/ru/labs/lab-1-1-controlled-zynq-tone-rtl-sdr/) — Управляемый DDS-тон Zynq с приемом на RTL-SDR
- [Лабораторная 6.3](/zynq-sdr-course/ru/labs/lab-6-3-ad9363-settings-iio-attr/) — Настройки AD9363 и iio_attr
- [Лабораторная 6.6](/zynq-sdr-course/ru/labs/lab-6-6-zynq-rx-only-observation/) — Zynq RX-only наблюдение на чистом образе
- [Лабораторная 6.8](/zynq-sdr-course/ru/labs/lab-6-8-zynq-ota-tone-observation/) — OTA DDS tone-наблюдение на stock-shell Zynq
- [Лабораторная 6.9](/zynq-sdr-course/ru/labs/lab-6-9-receiver-comparison/) — Сравнение RTL-SDR и AD936x: качество приёма и разрядность АЦП
- [Лабораторная 6.10](/zynq-sdr-course/ru/labs/lab-6-10-agc-phase-transition/) — Анализ фазового разрыва при переключении AGC/LNA
- [Лабораторная 6.11](/zynq-sdr-course/ru/labs/lab-6-11-tx-power-calibration/) — Калибровка мощности dBm и dBFS
- [Лабораторная 5.11](/zynq-sdr-course/ru/labs/lab-5-11-bpsk-axi-lite-control/) — Обёртка управления AXI-Lite для BPSK BER верхнего уровня
- [Лабораторная 5.12](/zynq-sdr-course/ru/labs/lab-5-12-zynq-ps-pl-mailbox/) — Почтовый ящик сообщений PS↔PL: первый осмысленный мост Zynq
- [Лабораторная 8.15](/zynq-sdr-course/ru/labs/lab-8-15-real-hardware-bpsk-metrics/) — BPSK на реальном железе: спектр, созвездие и SNR/EVM

Затем интегрированный проект блока 11 — основной путь от модема под управлением PS до линии между двумя платами:

- [Лабораторная 11.7](/zynq-sdr-course/ru/labs/lab-11-7-axi-lite-bpsk-bringup/) — Запуск BPSK через AXI-Lite со стороны PS
- [Лабораторная 11.14](/zynq-sdr-course/ru/labs/lab-11-14-stock-shell-bpsk-ota/) — Резервный путь BPSK OTA со стороны хоста в стоковом shell
- [Лабораторная 11.27](/zynq-sdr-course/ru/labs/lab-11-27-runtime-qpsk-digital-loopback/) — BER цифрового loopback QPSK в runtime
- [Лабораторная 11.28](/zynq-sdr-course/ru/labs/lab-11-28-rtl-sdr-ota-qpsk/) — Runtime QPSK через внешний RTL-SDR
- [Лабораторная 11.29](/zynq-sdr-course/ru/labs/lab-11-29-cold-boot-ber-campaign/) — Кампания надёжности BER при холодной загрузке
- [Лабораторная 11.30](/zynq-sdr-course/ru/labs/lab-11-30-two-board-cfo-validation/) — Оценщик грубого CFO на реальном двухплатном канале
- [Лабораторная 11.31](/zynq-sdr-course/ru/labs/lab-11-31-coarse-cfo-stress-sweep/) — Стресс-развёртка оценщика грубого CFO
- [Лабораторная 11.32](/zynq-sdr-course/ru/labs/lab-11-32-two-board-fabric-coarse-cfo/) — Двухплатный захват coarse-CFO внутри FPGA
- [Лабораторная 11.34](/zynq-sdr-course/ru/labs/lab-11-34-continuous-qpsk-timing-recovery/) — Непрерывное восстановление тактовой фазы QPSK
- [Лабораторная 11.38](/zynq-sdr-course/ru/labs/lab-11-38-hardware-tx-iq-capture-offline-rx/) — ZynqSDR TX → запись IQ → офлайн-приёмник
- [Лабораторная 11.45](/zynq-sdr-course/ru/labs/lab-11-45-differential-long-preamble/) — Дифференциальный QPSK + длинная преамбула: пол разворотов повержен
- [Лабораторная 11.46](/zynq-sdr-course/ru/labs/lab-11-46-two-board-console-message/) — Сообщение из консоли одной Zynq в консоль другой
- [Проект 12.4](/zynq-sdr-course/ru/labs/project-12-4-full-sdr-measurement-report/) — Полный измерительный отчёт по SDR

Остальные лабораторные блока 11 (11.8–11.26, 11.33, 11.35, 11.41, 11.42) — история запуска этого пути: каждая фиксирует один отказ, как его нашли и как исправили. Читайте их как разборы случаев, когда основной путь уже понятен: страница [Блок 11: разборы случаев отладки](/zynq-sdr-course/ru/block11-case-studies/) кратко описывает каждый как симптом, причину и урок.

## Маршрут D — добавить измерительные приборы

- [Лабораторная 10.5](/zynq-sdr-course/ru/labs/lab-10-5-nanovna-rf-demo-kit/) — NanoVNA и RF Demo Kit: S11/S21, КСВН и диаграмма Смита
- [Лабораторная 10.6](/zynq-sdr-course/ru/labs/lab-10-6-digital-attenuator-characterization/) — Цифровой RF-аттенюатор: проверка шага, диапазона и линейности

## Что предполагает каждый блок

| Блок | После чего | Новые инструменты |
|---|---|---|
| 1. Введение | — | Python, программа просмотра спектра |
| 2. Сигналы и дискретизация | блок 1 | — |
| 3. Основы DSP | блок 2 | — |
| 4. Фиксированная точка | блок 3 | (MATLAB / Simulink по желанию) |
| 5. FPGA / HDL | блоки 3–4 | Icarus Verilog; Vivado только для синтеза |
| 6. Радиотракт | блоки 2–3 | RTL-SDR или плата для живых частей |
| 7. Тракты TX/RX | блоки 3, 6 | — |
| 8. Модуляция и синхронизация | блок 7 | Icarus Verilog для 8.14 |
| 9. Запись и анализ | блок 2 | — |
| 10. Электроника и KiCad | блок 1 | KiCad; NanoVNA для 10.5–10.6 |
| 11. Интегрированный проект | блоки 5–8 | плата |
| 12. Итоговые проекты | пройденный маршрут | — |

## Формат отчёта
Каждый отчёт по лабораторной содержит цель, оборудование, параметры, порядок выполнения, графики или скриншоты и инженерный вывод с числами. См. [шаблон отчёта](/zynq-sdr-course/lab-report-template/) (на английском) и русские шаблоны в папке `reports/` каждого блока.
