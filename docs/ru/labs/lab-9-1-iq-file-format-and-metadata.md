# Лабораторная 9.1 — Формат IQ-файла и metadata

## Цель

Научиться оформлять воспроизводимый пакет IQ-записи: бинарный файл отсчётов и metadata JSON с параметрами чтения и интерпретации.

## Что выполняется

В работе студент:

1. выбирает формат IQ-записи;
2. фиксирует sample rate и center frequency;
3. задаёт порядок I/Q и endian;
4. описывает gain settings и expected signal offset;
5. проверяет полноту metadata.

## Результат

После выполнения работы должны быть получены:

- описание формата IQ;
- metadata JSON;
- checklist воспроизводимости;
- вывод о готовности записи к анализу.

## Что приложить к отчёту

- metadata JSON;
- формат файла и scaling rule;
- sample count и expected duration;
- expected signal offset;
- инженерный вывод.

## Подробная техническая часть

--8<-- "blocks/block_09_recording_and_analysis_tools/lab_9_1_iq_file_format_and_metadata.md"
