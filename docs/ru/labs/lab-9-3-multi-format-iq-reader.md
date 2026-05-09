# Лабораторная 9.3 — Мультиформатный IQ reader

## Цель

Научиться читать IQ-записи разных форматов (`ci16`, `cu8`, `cf32`) через единый metadata-driven pipeline.

## Что выполняется

В работе студент:

1. генерирует синтетические IQ-записи в трёх форматах;
2. создаёт metadata для каждого файла;
3. читает данные через общий dispatcher;
4. строит FFT-графики для каждого формата;
5. сравнивает peak frequency, SNR, DC offset и clipping fraction.

## Результат

После выполнения работы должны быть получены:

- три synthetic IQ capture files;
- metadata для каждого формата;
- FFT-графики `ci16`, `cu8`, `cf32`;
- общий metrics JSON;
- вывод о применимости форматов для дальнейшей обработки.

## Что приложить к отчёту

- список проверенных IQ-форматов;
- metadata examples;
- spectrum plots;
- таблицу peak/SNR/DC/clipping;
- инженерный вывод о предпочтительном формате.

## Подробная техническая часть

--8<-- "blocks/block_09_recording_and_analysis_tools/lab_9_3_multi_format_iq_reader.md"
