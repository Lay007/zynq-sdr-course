# Лабораторная 6.4 — Анализ синтетической RF IQ-записи

## Цель

Отладить pipeline анализа RF-захвата на синтетических IQ-данных до перехода к реальным записям с AD9363, RTL-SDR или HDSDR.

## Что выполняется

В работе студент:

1. читает metadata JSON;
2. генерирует синтетический IQ-сигнал;
3. строит FFT и временной график;
4. оценивает peak frequency, frequency error и SNR;
5. формирует metrics JSON и графики для отчёта.

## Результат

После выполнения работы должны быть получены:

- синтетический RF capture workflow;
- FFT-график;
- time-domain preview;
- metrics JSON;
- вывод о готовности анализа к реальным IQ-файлам.

## Что приложить к отчёту

- metadata JSON;
- FFT-график;
- measured peak и expected offset;
- оценку SNR;
- clipping/overload flag;
- инженерный вывод.

## Подробная техническая часть

--8<-- "blocks/block_06_rf_frontend_and_ad9363/lab_6_4_synthetic_rf_capture_analysis.md"
