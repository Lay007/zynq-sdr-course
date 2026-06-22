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
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches + AXI-Lite-controlled Zynq-ready BPSK BER top-level + gpreg-based AD9361 overlay scaffolding + integrated CLG400 bitstream/XSA + живое доказательство того, что standalone no-OS reference `system_top.bit` clean-boot проходит после преобразования в `system.bit.bin`, тогда как пересобранные vendor ZIP shell и pure-Tcl вариант `vendor_only` все еще расходятся с этой baseline | Ready | Hardware pending | HDL CI | Поднять validated пару no-OS reference `system_top.bit`/XSA до роли course PL baseline, а затем насаживать course overlay вокруг этого handoff, потому что pure-Tcl пересоздание `vendor_only` все еще оставляет read-only или disabled deltas. |
| 06 | RF frontend и AD9363 | Ready | Executable | Analysis scripts | Ready | Hardware pending | Labs | Собрать таблицу усиления/перегруза AD9361 RX на базе clean-image baseline. |
| 07 | TX/RX тракты | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Добавить пакет измерений RF loopback. |
| 08 | Модуляция и синхронизация | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Добавить sweeps по искажениям и дашборды BER/EVM. |
| 09 | Инструменты записи и анализа | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Обновить manifest датасета QPSK реальной checksum или синтетическим генератором. |
| 10 | KiCad и базовая электроника | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Добавить реальные фото макета и экспорты из KiCad. |
| 11 | Интегрированный SDR-проект | Ready | Executable | Simulation package + BPSK reference package + AXI-Lite helper + gpreg overlay tooling + historical `done+timeout` bring-up evidence + overlap contention probe + validated clean-boot baseline как из извлеченного stock BOOT.bin PL partition, так и из standalone no-OS reference `system_top.bit` | Ready | Hardware pending | Labs | Вернуть sample-domain gpreg bridge вокруг validated no-OS reference shell, заново подтвердить clean boot и только потом продолжать RF discovery к первым ненулевым `RECEIVED_BITS`. |
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
| `hardware/7020_ad936x_sdr/boot/course_clean/uEnv_course_bpsk_overlay.txt` | U-Boot boot overlay для загрузки course PL-образа и удаления устаревших Linux PL-узлов перед `bootm`. |
| `hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py` | Воспроизводимый extractor для known-good `system_top.bit` PL-partition, встроенного в `boot/sd_image/BOOT.bin`. |
| `hardware/7020_ad936x_sdr/boot/build_system_bit_bin.py` | Воспроизводимый Bootgen-wrapper для преобразования raw `.bit` в `system.bit.bin`, который ожидает clean boot overlay. |
| `docs/assets/lab112_clean_boot_pl_validation.json` | Постоянный артефакт с доказательством, что и извлеченный PL из `BOOT.bin`, и bootgen-преобразованный no-OS reference `system_top.bit` clean-boot проходят, а пересобранные vendor ZIP bitstream нет. |
| `hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit` | Source-correlated vendor reference bitstream, который теперь clean-boot проходит после преобразования в `system.bit.bin`. |
| `hardware/7020_ad936x_sdr/compare_xsa_handoffs.py` | Детектор source-level drift между XSA/HWH пересобранных shell и vendor reference handoff. |
| `docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json` | Постоянный diff-отчет, показывающий, что нормализованный pure-Tcl `vendor_only` теперь расходится только по `sys_ps7.PCW_S_AXI_HP0_FREQMHZ`, выбору DMA protocol и `axi_ad9361.SPEED_GRADE`. |
| `docs/assets/vendor_reference_vs_bridge_rx_only_handoff_diff.json` | Постоянный diff-отчет, показывающий, что именно intermediate overlay `bridge_rx_only` добавляет поверх еще не boot-safe vendor shell. |
| `docs/assets/vendor_reference_vs_vendor_xpr_snapshot_handoff_diff.json` | Постоянный diff-отчет, показывающий, что сохраненный vendor snapshot `zc702.xpr` является самым близким surviving source witness: от vendor reference XSA его отделяют только поля направления `sys_ps7` MIO14/15. |
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
