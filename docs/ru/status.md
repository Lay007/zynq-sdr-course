# Статус курса и матрица готовности

Эта страница служит верхнеуровневой инженерной сводкой по курсу. Она намеренно краткая: здесь видно, что уже сильное, что воспроизводимо, и где еще нужна аппаратная валидация.

## Легенда готовности

| Метка | Значение |
|---|---|
| `Ready` | Материал подходит для обучения и может использоваться как стабильная страница курса. |
| `Executable` | Для блока есть скрипты, тесты, сгенерированные графики или воспроизводимые проверки. |
| `Draft` | Структура уже есть, но блоку все еще нужны более глубокая теория, лабораторные или примеры. |
| `Hardware pending` | Учебный маршрут определен, но еще нужна проверка на реальной плате или реальные записи. |
| `Portfolio-ready` | У блока есть документация, воспроизводимые артефакты и понятные ревьюеру доказательства. |

## Матрица готовности блоков

| Блок | Тема | Теория | Лабы | Код / модели | Иллюстрации | Аппаратная часть | Покрытие CI | Следующее улучшение |
|---|---|---|---|---|---|---|---|---|
| 01 | Введение в SDR | Ready | Ready | Partial | Ready | Partial | Docs | Добавить первый подтвержденный пример захвата с RTL-SDR. |
| 02 | Сигналы и дискретизация | Ready | Executable | Python path | Ready | Not required | Labs | Добавить MATLAB/C++-варианты и пакет воспроизведения ошибок в метаданных. |
| 03 | Базовые DSP-операции | Ready | Executable | Python / MATLAB / C++ path | Ready | Not required | Labs | Добавить демонстрацию порога прямой свертки против FFT и больше эталонных результатов. |
| 04 | Simulink и fixed-point | Ready | Executable | Python / MATLAB references + executable BPSK `.slx` models | Ready | Not required | Labs | Сильнее ограничить BPSK-маршрут в Simulink под экспорт в HDL Coder и handoff в интеграцию. |
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches + AXI-Lite-controlled Zynq-ready BPSK BER top-level + gpreg-based AD9361 overlay scaffolding + integrated CLG400 bitstream/XSA + first live gpreg timeout evidence | Ready | Hardware pending | HDL CI | Дотюнить живой RF-тракт, чтобы discovery burst начал давать ненулевые биты, и затем зафиксировать BER. |
| 06 | RF frontend и AD9363 | Ready | Executable | Analysis scripts | Ready | Hardware pending | Labs | Собрать таблицу усиления/перегруза AD9361 RX на базе clean-image baseline. |
| 07 | TX/RX тракты | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Добавить пакет измерений RF loopback. |
| 08 | Модуляция и синхронизация | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Добавить sweeps по искажениям и дашборды BER/EVM. |
| 09 | Инструменты записи и анализа | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Обновить manifest датасета QPSK реальной checksum или синтетическим генератором. |
| 10 | KiCad и базовая электроника | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Добавить реальные фото макета и экспорты из KiCad. |
| 11 | Интегрированный SDR-проект | Ready | Executable | Simulation package + BPSK reference package + AXI-Lite helper + gpreg-based AD9361 burst helper + live `done+timeout` bring-up report + overlap contention probe | Ready | Hardware pending | Labs | Сохранить совместимость со штатной Linux DMA-обвязкой при clean-boot загрузке overlay, затем заново подтвердить совместную работу `iio_readdev` и `axi_gpreg`, и только после этого возвращаться к RF recovery и первым ненулевым `RECEIVED_BITS`. |
| 12 | Итоговые проекты | Ready | Draft | Templates + rubric | Partial | Depends on project | Docs | Использовать рубрику оценивания и каркас отчета на первом итоговом проекте. |

## Недавно добавленные артефакты для усиления курса

| Артефакт | Назначение |
|---|---|
| `docs/final-project-grading-rubric.md` | Единые критерии оценки для итоговых проектов Block 12. |
| `docs/end-to-end-qpsk-hardware-demo.md` | Чеклист флагманской демонстрации QPSK от модели до измерения. |
| `docs/end-to-end-bpsk-reference-report.md` | Исполнимый BPSK-маршрут от MATLAB-эталона к fixed-point и HDL handoff. |
| `docs/fpga-resource-report-template.md` | Контракт по FPGA-отчетности и ожидаемые поля. |
| `docs/block5-fpga-evidence.md` | Видимый в навигации конспект текущего пакета Vivado-доказательств для Block 5. |
| `docs/student-ci-grading-guide.md` | Процесс проверки студенческих веток и прохождения CI. |
| `docs/final-project-example-report.md` | Каркас portfolio-ready отчета по SDR-проекту. |
| `docs/hardware-validation-backlog.md` | Разделение чисто документальных задач и задач, требующих железо. |
| `docs/iq-demo-dataset-manifest.md` | Контракт на датасеты для QPSK replay/capture работ. |
| `datasets/demo_qpsk_capture/manifest.yaml` | Первый manifest-only пакет QPSK-датасета. |
| `hardware/7020_ad936x_sdr/boot/course_clean/autorun.sh` | Clean stock-image management overlay с фиксированным `eth0`, DHCP и безопасными TX-настройками. |
| `datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml` | Первый аппаратный manifest CI16 для clean-image Zynq RX-only наблюдения. |
| `templates/fpga_resource_report.template.md` | Переиспользуемый шаблон FPGA-отчета. |
| `templates/student_assignment.template.md` | Переиспользуемый шаблон студенческого задания. |
| `reports/fpga/z7020-resource-summary-template.md` | Первый вне-контекста-top-level FPGA summary для Z7020 с реальными числами. |
| `reports/fpga/block5-utilization-summary.md` | Сводка утилизации по модулям для четырех HDL-примеров Block 5. |
| `reports/fpga/block5-timing-summary.md` | Сводка timing по модулям на целевой частоте 100 МГц. |
| `reports/fpga/block5-latency-throughput-notes.md` | Заметки о латентности и throughput с проверкой тестбенчами. |

## CI и локальные quality gates

| Gate | Назначение | Ожидаемый сигнал для ревьюера |
|---|---|---|
| MkDocs build | Документация остается собираемой | Навигация и ссылки не ломаются незаметно. |
| Full course smoke | Репрезентативные лабы запускаются из чистого checkout | Сгенерированные артефакты воспроизводимы. |
| HDL smoke | Verilog-примеры компилируются и симулируются | FPGA-ориентированные примеры не сводятся к статическому тексту. |
| Block-specific checks | Ловят регрессии рядом с измененным материалом | Небольшие падения проще локализовать. |

## Контракт артефактов для зрелых лабораторных

Каждая зрелая лабораторная со временем должна включать:

- короткую постановку задачи;
- запускаемый скрипт, HDL-тестбенч или четко ограниченный ручной эксперимент;
- ожидаемые выходные файлы в `docs/assets`, `verification`, `datasets`, `reports` или документированный путь отчета;
- краткую интерпретацию, объясняющую, что именно доказывает график или таблица;
- локальные команды воспроизведения;
- CI-хук или smoke-test, когда это практично.

## Сильные стороны курса

- Репозиторий уже связывает теорию, DSP, fixed-point реализацию, HDL, RF, IQ-запись, анализ и отчетность.
- Сайт документации собран на MkDocs и структурирован для русскоязычных и англоязычных студентов.
- Несколько блоков уже исполнимы и поддерживаются воспроизводимыми скриптами, сгенерированными артефактами и CI workflow.
- Аппаратная история прозрачна: Zynq-7020 + AD9363/ADRV является целевой SDR-платформой, а RTL-SDR/HDSDR используется как независимый тракт наблюдения.

## Главные пробелы, которые нужно закрыть

1. Заменить manifest-only QPSK-датасет на маленький подтвержденный файл или внешнюю ссылку.
2. Добавить измерения на реальной плате для тракта Zynq/AD9363.
3. Повысить Block 5 OOC FPGA-отчеты до данных по top-level placed-and-routed дизайну.
4. Держать RU/EN страницы синхронными при добавлении новых лабораторных.
5. Довести один QPSK- или tone-сценарий до полного финального отчета с графиками и ограничениями.

## Приоритетные улучшения

1. Поднять один полный сценарий `Model -> FPGA -> RF -> Measurement` до статуса portfolio-ready.
2. Добавить небольшой публичный или синтетический IQ-датасет для лабораторных по записи и replay.
3. Использовать текущие отчеты Block 5 как baseline, затем добавить deltas по routed timing/resource для интегрированного дизайна.
4. Использовать рубрику оценивания итоговых проектов в преподавательской оценке.
5. Синхронизировать русскую и английскую навигацию при каждом повышении зрелости блока.

## Быстрый путь для ревьюера

Для быстрого обзора начните с:

1. `README_RU.md` или `README.md` для общего обещания курса.
2. `docs/model-to-measurement.md` для сквозного инженерного маршрута.
3. `docs/lab-index.md` для списка запускаемых лабораторных и отчетных работ.
4. `docs/reproducibility-guide.md` для инструкций по локальной пересборке.
5. `docs/reviewer-checklist.md` для проверок в формате pass/fail.
6. Этой статусной страницы для оценки готовности и оставшихся пробелов.

## Definition of done для нового блока

Блок считается готовым для курса, когда у него есть:

- четкая учебная цель;
- теоретическая страница на двух языках;
- хотя бы одна лабораторная или guided exercise;
- сгенерированные или воспроизводимые иллюстрации;
- ожидаемые результаты и заметки по валидации;
- ссылки на скрипты, шаблоны или тестовые векторы;
- заметки по аппаратной безопасности, если используется RF-оборудование;
- место в навигации `mkdocs.yml`.
