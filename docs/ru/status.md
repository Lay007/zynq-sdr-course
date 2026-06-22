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
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches + AXI-Lite-controlled Zynq-ready BPSK BER top-level + gpreg-based AD9361 overlay scaffolding + integrated CLG400 bitstream/XSA + живое доказательство того, что при внешнем `fpga load` clean-boot сейчас проходит только извлеченный partition payload `BOOT.bin::system_top.bit`, тогда как source-correlated no-OS reference payload все еще уводит AD9361 в timeout, а сохраненный snapshot `zc702.xpr` остается zero-drift editable XSA baseline, но не boot-safe RF shell | Ready | Hardware pending | HDL CI | Понять, почему stock partition переживает внешний load, и воспроизвести эти свойства в editable shell, прежде чем насаживать туда course overlay. |
| 06 | RF frontend и AD9363 | Ready | Executable | Analysis scripts + measured RX-only and OTA-tone captures | Ready | Hardware pending | Labs | Использовать measured RX-only FM и OTA-tone baseline для таблицы усиления/перегруза AD9361 RX, затем проверить безопасный cabled loopback. |
| 07 | TX/RX тракты | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Добавить пакет измерений RF loopback. |
| 08 | Модуляция и синхронизация | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Добавить sweeps по искажениям и дашборды BER/EVM. |
| 09 | Инструменты записи и анализа | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Обновить manifest датасета QPSK реальной checksum или синтетическим генератором. |
| 10 | KiCad и базовая электроника | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Добавить реальные фото макета и экспорты из KiCad. |
| 11 | Интегрированный SDR-проект | Ready | Executable | Simulation package + BPSK reference package + AXI-Lite helper + gpreg overlay tooling + historical `done+timeout` bring-up evidence + overlap contention probe + raw-clean-boot доказательство того, что кандидат `bridge_txrx_mux` действительно доходит до PL и открывает `axi_gpreg` по адресу `0x79040000`, хотя AD9361 все еще уходит в timeout, плюс manual-UART `fpga load` evidence того, что stock BOOT partition сейчас остается единственным boot-safe external PL payload, новое runtime `fpga_manager` evidence того, что corrected `bridge_txrx_mux` hot-load снова поднимает `axi_gpreg` и трехустройственный IIO context, но `iio_readdev` refill и `rx_valid_count` все еще остаются нулевыми, а также более строгий stock-vs-runtime comparison, доказывающий, что stock-shell host RX capture до reload еще работает, тогда как после runtime overlay ломаются оба host RX path, плюс новый host-driven stock-shell OTA BPSK fallback path, который уже дал живой `BER = 0` OTA прогон на `915 MHz` и теперь возвращает плату обратно в safe TX baseline после завершения | Ready | Hardware pending | Labs | Использовать уже доказанный stock-shell host-BPSK route как RF witness, вести работу по boot-safe editable shell отдельно и возвращать ту же waveform/measurement discipline обратно в PL overlay после устранения runtime RX starvation. |
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
| `hardware/7020_ad936x_sdr/boot/extract_stock_system_top_partition.py` | Воспроизводимый extractor для единственного известного сегодня boot-safe `system_top.bit` partition payload, который реально переживает внешний `fpga load`: встроенного в `boot/sd_image/BOOT.bin`. |
| `hardware/7020_ad936x_sdr/boot/build_system_bit_bin.py` | Воспроизводимый конвертер из raw Xilinx `.bit` в word-swapped `.bit.bin` payload, который принимает ручной путь U-Boot `fpga load` на этой плате. |
| `hardware/7020_ad936x_sdr/boot/validate_manual_uart_fpga_load.py` | Воспроизводимый helper, который останавливает autoboot по UART, запускает ручной `fpga load`, грузит Linux и показывает, пережил ли `.bit.bin` payload внешний PL-load на самом деле. |
| `hardware/7020_ad936x_sdr/compare_fpga_payloads.py` | Нормализует raw `.bit` во внутренний payload для ручного `fpga load` и показывает first-diff offsets относительно stock или course-кандидатов. |
| `hardware/7020_ad936x_sdr/rebuild_vendor_xpr_snapshot_mio_patch.tcl` | Одноразовый Vivado-flow, который патчит только `sys_ps7` MIO14/15 в сохраненном snapshot `zc702.xpr` перед synth/impl/export. |
| `docs/assets/lab112_clean_boot_pl_validation.json` | Постоянный артефакт с доказательством того, что raw `.bit` через `fpga loadb` действительно меняет PL, но для всех проверенных non-stock кандидатов все еще ломает AD9361, тогда как manual `.bit.bin` `fpga load` clean-boot сейчас проходит только для извлеченного stock BOOT partition payload. |
| `docs/assets/stock_vs_vendor_reference_fpga_payload_diff.json` | Артефакт с первым различием, показывающий, где извлеченный stock BOOT payload расходится с source-correlated vendor-reference payload для `fpga load`. |
| `docs/assets/stock_vs_bridge_txrx_mux_fpga_payload_diff.json` | Артефакт с первым различием, показывающий, где извлеченный stock BOOT payload расходится с corrected course `bridge_txrx_mux` payload для `fpga load`. |
| `docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_payload_diff.json` | Нормализованный payload-diff, доказывающий, что editable vendor snapshot после патча MIO14/15 побайтно совпадает с source-correlated vendor reference на пути manual `fpga load`. |
| `docs/assets/lab118_axi_gpreg_bringup_cleanboot_raw.json` | Прямой raw-clean-boot отчет по gpreg для кандидата `bridge_txrx_mux`: PL дошла до fabric, ID/signature совпали, `tx_valid_count` растет, а `rx_valid_count` остается нулевым. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_12_runtime_fpga_manager_reload.py` | Воспроизводимый host-side helper, который грузит проверенный `.bit.bin` payload по SSH, hot-load'ит его через Linux `fpga_manager`, а затем заново проверяет `axi_gpreg` и видимый с хоста IIO context. |
| `docs/assets/lab118_runtime_fpga_manager_reload_live.json` | Сводный runtime hot-load артефакт для corrected payload `bridge_txrx_mux`: на stock-shell baseline нет `axi_gpreg`, `fpga_manager` принимает reload, gpreg возвращается, и хост по-прежнему видит трехустройственный IIO context. |
| `docs/assets/lab118_axi_gpreg_bringup_runtime_20260623.json` | Post-reload gpreg burst-отчет, показывающий повторяемый runtime-паттерн `done + timeout`, `tx_valid_count = 2376`, `rx_valid_count = 0`, `received_bits = 0`. |
| `docs/assets/lab110_iio_burst_capture_runtime_20260623.json` | Post-reload timed burst-capture evidence того, что `iio_readdev` все еще возвращает refill timeout `Unknown error (110)` и не дает ни одного sample, хотя gpreg остается читаемым. |
| `docs/assets/lab119_rf_discovery_sweep_runtime_20260623.json` | Компактный safe-power RF sweep после runtime reload, подтверждающий, что варьирование `START_OFFSET`, RX gain и TX attenuation все еще оставляет `rx_valid_count = 0` и `RECEIVED_BITS = 0`. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_13_stock_vs_runtime_rx_compare.py` | A/B helper, который сначала доказывает, что stock-shell host RX capture еще работает, а затем hot-load'ит runtime overlay и повторяет те же host RX проверки вместе с gpreg и DMAC probe. |
| `docs/assets/lab113_stock_vs_runtime_rx_compare_live.json` | Live comparison report, доказывающий, что stock-shell `libiio` и `iio_readdev` работают до reload, тогда как runtime overlay оставляет `axi_gpreg` живым, но ломает оба host RX capture path. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_14_stock_shell_bpsk_ota.py` | Host-driven stock-shell AD9361 fallback, который передает детерминированный OTA BPSK burst через уже доказанный Linux TX/RX DMA path, считает BER/EVM и теперь еще принудительно возвращает safe TX state через SSH/sysfs после завершения. |
| `datasets/lab11_14_stock_shell_bpsk_ota/manifest_live_20260623d.yaml` | Первый успешный live manifest для stock-shell OTA BPSK: `915 MHz`, `3.84 MS/s`, `240 ksym/s`, `TX -50 dB`, `RX +35 dB`, frame detected, `BER = 0`. |
| `docs/assets/lab114_stock_shell_bpsk_ota_live_20260623d_metrics.json` | Живые метрики первого успешного stock-shell OTA BPSK fallback run: состояние платы до и после конфигурации, нулевой BER, EVM и амплитудные метрики захвата. |
| `hardware/7020_ad936x_sdr/ps/ad936x_no_os_reference/platform/hw/system_top.bit` | Source-correlated vendor reference bitstream, который по-прежнему доказывает, что raw `fpga loadb` реально доходит до PL, но все еще не сохраняет рабочий AD9361 на этой плате. |
| `hardware/7020_ad936x_sdr/compare_xsa_handoffs.py` | Детектор source-level drift между XSA/HWH пересобранных shell и vendor reference handoff. |
| `docs/assets/vendor_reference_vs_vendor_only_handoff_diff.json` | Постоянный diff-отчет, показывающий, что нормализованный pure-Tcl `vendor_only` теперь расходится только по `sys_ps7.PCW_S_AXI_HP0_FREQMHZ`, выбору DMA protocol и `axi_ad9361.SPEED_GRADE`. |
| `docs/assets/vendor_reference_vs_bridge_rx_only_handoff_diff.json` | Постоянный diff-отчет, показывающий, что именно intermediate overlay `bridge_rx_only` добавляет поверх еще не boot-safe vendor shell. |
| `docs/assets/vendor_reference_vs_vendor_xpr_snapshot_handoff_diff.json` | Постоянный diff-отчет, показывающий исторический drift непатченного snapshot `zc702.xpr` относительно vendor reference XSA только по полям направления `sys_ps7` MIO14/15. |
| `docs/assets/vendor_reference_vs_vendor_xpr_mio14_15_patch_handoff_diff.json` | Постоянный diff-отчет, показывающий, что rebuild сохраненного vendor snapshot `zc702.xpr` после патча MIO14/15 достигает нулевого drift по module/memrange/parameter относительно vendor reference XSA. |
| `datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454.yaml` | Первый аппаратный manifest CI16 для clean-image Zynq RX-only наблюдения. |
| `datasets/lab6_6_zynq_rx_observation/manifest_fm_103119454_live_20260622.yaml` | Повторный live manifest clean-image Zynq RX-only FM, снятый 2026-06-22, с новыми FFT/time plot и overlay `Zynq vs RTL`. |
| `blocks/block_06_rf_frontend_and_ad9363/python/lab_6_8_capture_zynq_ota_tone.py` | Воспроизводимый helper для stock-shell OTA DDS tone capture и первого host-driven TX-to-RX RF proof на Zynq AD9361. |
| `datasets/lab6_8_zynq_ota_tone_observation/manifest_tone_915MHz_700kHz_live_20260622.yaml` | Первый measured manifest stock-shell OTA tone-датасета с checksum, консервативными TX/RX настройками и окном поиска тона для офлайн-анализа. |
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
2. Расширить первые измерения на реальной плате для тракта Zynq/AD9363 до полного gain/loopback package.
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
