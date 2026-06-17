# Лабораторная 2.3 — Интерпретация I/Q и mirrored spectrum

## Цель

Понять разницу между корректной complex I/Q-записью, перестановкой каналов I/Q и real-valued захватом, который даёт зеркальный спектр.

## Что выполняется

В работе студент:

1. формирует комплексный тон в baseband;
2. сравнивает correct complex IQ, swapped I/Q и real-only capture;
3. измеряет peak positions для положительной и отрицательной частей спектра;
4. проверяет, как потеря порядка I/Q или imaginary channel меняет физический смысл спектра.

## Результат

После выполнения работы должны быть получены:

- временной график компонентов I/Q;
- спектральное сравнение correct/swapped/real capture;
- metrics JSON с положением пиков и проверкой зеркальности;
- инженерный вывод о важности правильного порядка I/Q в SDR pipeline.

## Что приложить к отчёту

- график `lab23_iq_components_time.png`;
- график `lab23_iq_interpretation_spectra.png`;
- measured peaks для correct, swapped и mirrored cases;
- краткое объяснение, почему complex baseband различает знак частоты;
- note о том, как ошибка перестановки I/Q проявится в реальной IQ-записи.

## Подробная техническая часть

--8<-- "blocks/block_02_signals_and_sampling/lab_2_3_iq_interpretation_and_mirroring.md"
