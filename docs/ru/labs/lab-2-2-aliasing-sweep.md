# Лабораторная 2.2 — Aliasing sweep

## Цель

Понять, как тоны выше Nyquist складываются обратно в наблюдаемую полосу и почему без модели aliasing нельзя корректно интерпретировать спектр.

## Что выполняется

В работе студент:

1. задаёт реальный sampler с `Fs = 1.0 MHz`;
2. строит alias map для широкого диапазона входных частот;
3. сравнивает спектры для тонов ниже и выше Nyquist;
4. проверяет measured alias frequency против аналитического расчёта.

## Результат

После выполнения работы должны быть получены:

- карта aliasing `input -> observed`;
- примерные спектры для трёх тестовых тонов;
- metrics JSON с expected alias и max alias error;
- вывод о требованиях к anti-alias filtering или выбору `Fs`.

## Что приложить к отчёту

- значение `Fs` и Nyquist frequency;
- график `lab22_aliasing_map.png`;
- график `lab22_aliasing_examples.png`;
- таблицу expected vs measured alias frequencies;
- инженерный вывод о том, как избежать неправильной частотной интерпретации.

## Подробная техническая часть

--8<-- "blocks/block_02_signals_and_sampling/lab_2_2_aliasing_sweep.md"
