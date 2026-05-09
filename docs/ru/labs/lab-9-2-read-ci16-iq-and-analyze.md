# Лабораторная 9.2 — Чтение CI16 IQ и анализ спектра

## Цель

Научиться читать бинарный CI16 IQ-файл по metadata JSON, строить спектр и выполнять базовые проверки качества записи.

## Что выполняется

В работе студент:

1. генерирует синтетический CI16 IQ-файл;
2. читает его как interleaved signed int16 I/Q;
3. переводит отсчёты в normalized complex samples;
4. строит FFT и time preview;
5. оценивает peak frequency, SNR, DC offset и clipping fraction.

## Результат

После выполнения работы должны быть получены:

- CI16 IQ-файл;
- spectrum plot;
- time-domain preview;
- metrics JSON;
- quality_pass вывод.

## Что приложить к отчёту

- metadata JSON;
- FFT-график;
- measured peak и frequency error;
- SNR estimate;
- DC/clipping checks;
- вывод о пригодности записи к синхронизации и демодуляции.

## Подробная техническая часть

--8<-- "blocks/block_09_recording_and_analysis_tools/lab_9_2_read_ci16_iq_and_analyze.md"
