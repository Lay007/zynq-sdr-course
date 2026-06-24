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

## Быстрые расшифровки

| Термин | Что это значит здесь |
|---|---|
| `stock-shell` | Штатная vendor-конфигурация платы после обычной загрузки Linux и PL, до runtime-подгрузки course overlay. |
| `OTA` | `Over the air`, то есть передача по эфиру через антенны, а не по кабелю. |
| `BPSK` | `Binary phase-shift keying`, двоичная фазовая манипуляция: один бит на символ. |
| `evidence` | Воспроизводимый артефакт: manifest, JSON-отчет, график или лог, который доказывает реальный результат на стенде. |

## Матрица готовности блоков

| Блок | Тема | Теория | Лабы | Код / модели | Иллюстрации | Аппаратная часть | Покрытие CI | Следующее улучшение |
|---|---|---|---|---|---|---|---|---|
| 01 | Введение в SDR | Ready | Ready | Partial | Ready | Реальные RTL-SDR записи + управляемый DDS-тон Zynq | Docs | Добавить короткий учебный отчет, сравнивающий пассивный эфирный захват с новым управляемым DDS-тоном Zynq, и проверить публикационный/юридический статус узкополосной off-air записи. |
| 02 | Сигналы и дискретизация | Ready | Executable | Python path | Ready | Not required | Labs | Добавить MATLAB/C++-варианты и пакет воспроизведения ошибок в метаданных. |
| 03 | Базовые DSP-операции | Ready | Executable | Python / MATLAB / C++ path | Ready | Not required | Labs | Добавить демонстрацию порога прямой свертки против FFT и больше эталонных результатов. |
| 04 | Simulink и fixed-point | Ready | Executable | Python / MATLAB references + executable BPSK `.slx` models | Ready | Not required | Labs | Сильнее ограничить BPSK-маршрут в Simulink под экспорт в HDL Coder и handoff в интеграцию. |
| 05 | FPGA / HDL flow | Ready | Executable | Verilog testbenches + AXI-Lite-controlled Zynq-ready BPSK BER top-level + gpreg-based AD9361 overlay scaffolding + integrated CLG400 bitstream/XSA + живое доказательство того, что при внешнем `fpga load` clean-boot сейчас проходит только извлеченный partition payload `BOOT.bin::system_top.bit`, тогда как source-correlated no-OS reference payload все еще уводит AD9361 в timeout, а сохраненный snapshot `zc702.xpr` остается zero-drift editable XSA baseline, но не boot-safe RF shell, плюс новый timing-clean rebuild `bridge_txrx_mux`, где FPGA BER path теперь использует latched frame config, delayed/inverted loopback regression benches и coarse acquisition prefix, который все еще проходит implementation timing (`WNS = +0.176 ns`) | Ready | Hardware pending | HDL CI | Зафиксировать timing-clean BER core как новый baseline, а затем заменить coarse acquisition prefix на более избирательный, но все еще timing-safe frame detector. |
| 06 | RF frontend и AD9363 | Ready | Executable | Analysis scripts + measured RX-only and OTA-tone captures | Ready | Hardware pending | Labs | Использовать measured RX-only FM и OTA-tone baseline для таблицы усиления/перегруза AD9361 RX, затем проверить безопасный cabled loopback. |
| 07 | TX/RX тракты | Ready | Executable | DUC/DDC demos | Ready | Hardware pending | Labs | Добавить пакет измерений RF loopback. |
| 08 | Модуляция и синхронизация | Ready | Executable | Synchronization demos | Ready | Optional | Sync CI | Добавить sweeps по искажениям и дашборды BER/EVM. |
| 09 | Инструменты записи и анализа | Ready | Executable | IQ readers | Ready | Hardware pending | Recording CI | Обновить manifest датасета QPSK реальной checksum или синтетическим генератором. |
| 10 | KiCad и базовая электроника | Ready | Draft | Calculators / templates | Partial | Bench pending | Docs | Добавить реальные фото макета и экспорты из KiCad. |
| 11 | Интегрированный SDR-проект | Ready | Executable | Simulation package + BPSK reference package + AXI-Lite helper + gpreg overlay tooling + historical `done+timeout` bring-up evidence + overlap contention probe + raw-clean-boot доказательство того, что кандидат `bridge_txrx_mux` действительно доходит до PL и открывает `axi_gpreg` по адресу `0x79040000`, хотя AD9361 все еще уходит в timeout, плюс manual-UART `fpga load` evidence того, что stock BOOT partition сейчас остается единственным boot-safe external PL payload, новое runtime `fpga_manager` evidence того, что corrected `bridge_txrx_mux` hot-load снова поднимает `axi_gpreg` и трехустройственный IIO context, но `iio_readdev` refill и `rx_valid_count` все еще остаются нулевыми, более строгий stock-vs-runtime comparison, доказывающий, что stock-shell host RX capture до reload еще работает, тогда как после runtime overlay ломаются оба host RX path, более узкий `bridge_rx_only` runtime witness, показывающий, что даже при host-driven stock TX BPSK после reload нулевыми остаются не только `rx_valid_count`, но и весь сырой RX-tap `CAPTURE_DEBUG`, еще более точный input-side witness, доказывающий, что после runtime reload сырой RX debug со стороны `axi_ad9361` остается в reset (`adc_input_reset_asserted_current = 1`, heartbeat стоит на нуле, `adc_valid_i0` ни разу не поднимается), новый runtime RX-common re-init witness, доказывающий, что возврат stock `rx_common_ctrl_req = 0x3` оживляет ненулевую RX clock/status активность и снимает сырой input-side reset, хотя оба host RX capture path все еще не восстанавливаются, reinit-assisted host-TX witness, доказывающий, что тот же runtime overlay снова поднимает `rx_valid_count`, видит сырой capture-valid и уже принимает полный кадр длиной `281 бит`, raw-sign witness и разбор ADI HDL, показывающие, что bridge tap все еще подавал в BER core offset-binary выборки AD9361, локальный bridge-side format fix, который возвращает на живом железе отрицательные решения и recovered `1` bits, улучшенные runtime sweep'ы, которые доводят лучший известный live point до `281 / 127 / 114`, новый self-timed helper для `bridge_txrx_mux`, который уже доводит PL-owned TX/RX path до полного кадра, новый timing-clean rebuild от `2026-06-24`, показывающий, что strict full-preamble live lock для эфира все еще слишком жесткий, тогда как coarse 4-bit acquisition prefix уже возвращает стабильный full-frame self-timed runtime прием на `neg-q` при `start_offset = 58..60` с лучшей сохраненной точкой `281 / 141 / 132`, новый управляемый внешний DDS-tone witness, доказывающий, что stock-shell тракт по-прежнему излучает ожидаемый `200 kHz` тон, тогда как на настоящем runtime overlay доминирующий внешний пик схлопывается почти к DC, более сильная матрица локализации runtime-shell, показывающая тот же near-DC collapse уже на `vendor_only`, `gpreg_only`, `bridge_rx_only` и `bridge_txrx_mux`, то есть блокер сидит в editable non-stock runtime shell path, и подтвержденный runtime repair path, показывающий, что `cf_axi_dds` rebind плюс восстановление `RATECNTRL = 3` возвращают внешний тон `200 kHz` не только на `vendor_only`, но и на полном payload `bridge_txrx_mux` | Ready | Hardware pending | Labs | Применить уже проверенный post-reload AXI DDS repair (`cf_axi_dds` rebind + `RATECNTRL=3`) ко всем runtime BPSK helper'ам, добавить ADC-side re-init там, где он нужен, и затем заново прогнать OTA BER-sweep уже на repaired runtime shell. |
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
| `datasets/lab1_0_rtl_sdr_observation/` | Реальные пассивные RTL-SDR off-air записи из первой сессии SDR++, сохраненные как WAV IQ через Git LFS вместе с manifest, SHA256, параметрами приема и командами повтора. |
| `datasets/lab11_24_dds_tone_rtl_monitor/manifest_live_20260624_stock_dds_tone_ref_a.yaml` | Первый управляемый Zynq-to-RTL-SDR WAV IQ датасет для Block 1 с известным stock-shell DDS-тоном `915 MHz + 200 kHz` и прямыми командами повтора для WAV-анализатора. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_24_capture_dds_tone_rtl_monitor_wav.py` | Helper, который записывает внешний RTL-SDR WAV monitor при передаче DDS-тона платой в режимах `stock` и `runtime`, а затем сразу пишет manifest для офлайн-анализа. |
| `docs/assets/lab11_24_dds_tone_rtl_monitor_live_20260624_stock_dds_tone_ref_a_metrics.json` | Live-метрики управляемого stock-shell tone witness: пик около `200 kHz`, `SNR ≈ 66.4 dB`, без clipping, quality gate `PASS`. |
| `docs/assets/lab11_24_dds_tone_rtl_monitor_live_20260624_runtime_dds_tone_ref_a_metrics.json` | Парный runtime-overlay witness, показывающий, что ожидаемый внешний тон `200 kHz` схлопывается почти к DC, то есть текущая проблема Block 11 локализуется уже в TX-path visibility, а не только в BER-демодуляции. |
| `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_vendor_only_dds_tone_a.json`, `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_gpreg_only_dds_tone_a.json`, `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_bridge_rx_only_dds_tone_a.json` | Дополнительные управляемые runtime tone-witness'ы, показывающие, что тот же near-DC collapse уже присутствует на минимальных editable shell-вариантах, еще до полной course TX/RX bridge-логики. |
| `docs/assets/lab1125_stock_vs_runtime_dds_tone_sweep_live_20260624_sync_arm_test_a.json` | Повторный stock-vs-runtime DDS-tone comparison, показывающий, что даже явная попытка runtime `sync_start_enable=arm` оставляет stock около ожидаемого пика `200 kHz`, тогда как runtime по-прежнему схлопнут почти к DC. |
| `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_vendor_only_dds_tone_rebind_dds_a.json` | Промежуточный runtime repair witness: один только post-reload `cf_axi_dds` rebind уже возвращает сильный внешний тон, но примерно на `800 kHz`, что локализует еще один недостающий элемент состояния в DDS rate-control register. |
| `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_vendor_only_dds_tone_rebind_dds_rate3_a.json` и `docs/assets/lab1124_dds_tone_rtl_monitor_live_20260624_bridge_txrx_mux_dds_tone_rebind_dds_rate3_a.json` | Финальные repaired runtime tone-witness'ы, показывающие, что `cf_axi_dds` rebind плюс `RATECNTRL = 3` восстанавливают чистый внешний тон `200 kHz` и на минимальном editable shell, и на полном course overlay `bridge_txrx_mux`. |
| `docs/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_live_20260624_runtime_pl_rebind_a_metrics.json` | Первый внешний runtime/PL BPSK monitor rerun после переноса нового AXI DDS/ADC re-init path в живой helper; это новый BER-baseline для repaired runtime shell. |
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
| `blocks/block_11_integrated_sdr_project/python/runtime_rx_common.py` | Общий helper для чтения и восстановления stock RX common control request после runtime reload overlay. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_15_runtime_bridge_rx_host_tx_probe.py` | Runtime helper для промежуточного `bridge_rx_only`: hot-load'ит overlay, делает один idle gpreg witness, а затем повторяет тот же probe при активной stock host TX передаче общего детерминированного BPSK burst, теперь декодируя и сырое input-side слово `ADC_INPUT_DEBUG`, и RX-tap слово `CAPTURE_DEBUG`; при необходимости может принудительно вернуть stock RX common control request через `--rx-common-reinit`. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_16_runtime_rx_common_reinit_probe.py` | A/B helper, который hot-load'ит runtime overlay, фиксирует отказ host RX capture, восстанавливает stock RX common control request и проверяет, восстанавливается ли вместе с fabric-side RX еще и host libiio/DMAC capture. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_17_runtime_rx_common_reinit_start_offset_sweep.py` | Helper для sweep по `start_offset`, который hot-load'ит runtime overlay, восстанавливает stock RX common control request, запускает stock host TX и показывает, на каких значениях `start_offset` runtime BPSK receive attempt доходит до полного кадра. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_18_runtime_rx_common_reinit_fresh_session_sweep.py` | Fresh-session helper, который между точками возвращает плату в stock state, затем снова hot-load'ит runtime overlay и проверяет, меняется ли BER при варьировании `start_offset`, RX gain, TX attenuation и TX phase без влияния старого session state. |
| `docs/assets/lab115_runtime_bridge_rx_host_tx_probe_live_20260623_bridge_rx_only_b.json` | Более ранний live-отчет по `bridge_rx_only`, снятый до добавления дополнительной сырой RX-tap инструменталки: overlay загружается корректно и stock host TX работает, но и idle probe, и host-TX probe все равно заканчиваются с `tx_valid_count = 2376`, `rx_valid_count = 0` и `received_bits = 0`. |
| `docs/assets/lab115_runtime_bridge_rx_host_tx_probe_live_20260623_bridge_rx_only_debug_a.json` | Канонический уточненный live-отчет по `bridge_rx_only`: overlay загружается корректно, stock host TX работает, но оба probe все равно заканчиваются с `tx_valid_count = 2376`, `rx_valid_count = 0`, `received_bits = 0` и `capture_debug_word = 0`, что доказывает отсутствие любой сырой активности на RX tap после runtime reload. |
| `docs/assets/lab115_runtime_bridge_rx_host_tx_probe_live_20260623_bridge_rx_only_input_debug_a.json` | Уточненный input-side live-отчет по `bridge_rx_only`: после runtime reload сырой RX debug со стороны `axi_ad9361` все еще показывает `adc_input_reset_asserted_current = 1`, нулевой heartbeat, отсутствие активности `adc_valid_i0` и нулевую FIFO-output RX-tap активность даже при host-driven stock TX, что локализует blocker в сыром RX reset/enable path до FIFO-output domain. |
| `docs/assets/lab116_runtime_rx_common_reinit_probe_live_20260623.json` | Живой re-init probe, показывающий, что запись stock `rx_common_ctrl_req = 0x3` после runtime reload восстанавливает ненулевой `rx_common_clk_count` и снимает сырой RX reset, хотя оба host RX capture path все еще падают с теми же timeout-симптомами. |
| `docs/assets/lab116_runtime_rx_common_reinit_host_tx_probe_live_20260623.json` | Живой post-reinit host-TX witness, показывающий, что runtime overlay снова получает сырой RX-valid, поднимает `rx_valid_count > 0` и завершает одну полную попытку приема кадра длиной `281 бит`, хотя BER пока остается высоким. |
| `docs/assets/lab117_runtime_rx_common_reinit_start_offset_sweep_live_20260623.json` | Первый post-reinit sweep по `start_offset`, показывающий, что runtime overlay способен завершить полный прием кадра хотя бы в одном раннем окне `start_offset`, что переводит оставшийся blocker из категории “мертвый RX plumbing” в категорию timing/phase stability. |
| `docs/assets/lab118_runtime_rx_common_reinit_fresh_session_start_offset_wide_live_20260623.json` | Частичный, но уже показательный широкий fresh-session sweep по `start_offset`: один и тот же результат `281 / 144 / 136` сохранился от `start_offset = 0` до `576`, так что оставшийся сбой уже нельзя объяснить только узким локальным timing-window. |
| `docs/assets/lab119_runtime_rx_decision_debug_single_point_live_20260623.json` | Живое full-frame доказательство по знаку решений: после runtime reload и RX-common re-init bridge видит recovered valid pulses и ненулевые decision samples, но ни одного отрицательного decision sample и ни одного recovered bit `1`, что и объясняет поведение BER counters как у all-zero recovered bit stream. |
| `docs/assets/lab120_runtime_capture_sign_single_point_live_20260623.json` | Живой witness по знаку на сыром bridge tap, доказывающий, что оживленный RX path все еще подавал в BER core unsigned offset-binary выборки AD9361: сырая активность `RX1` и полный масштаб есть, но ни `I`, ни `Q` ни разу не уходят в минус на tap. |
| `docs/assets/lab121_runtime_offset_binary_fix_single_point_live_20260623.json` | Первое живое доказательство после локального bridge-side offset-binary conversion: recovered path теперь видит отрицательные решения и recovered `1` bits, то есть старый режим all-zero stream действительно закрыт. |
| `docs/assets/lab122_runtime_offset_binary_fix_phase_sweep_live_20260623.json` | Fresh-session sweep по фазе `start_offset` после offset-binary fix, показывающий, что лучший live point смещается к `start_offset = 34` и улучшает BER до `281 / 129 / 120`. |
| `docs/assets/lab123_runtime_offset_binary_fix_tx_phase_sweep_live_20260623.json` | Sweep по TX phase в лучшей известной runtime точке, показывающий лишь умеренный дополнительный выигрыш и подтверждающий, что доминирующая оставшаяся проблема уже не в старом unsigned-sample defect. |
| `docs/assets/lab124_runtime_offset_binary_fix_gain_sweep_live_20260623.json` | Лучшая текущая live runtime точка после offset-binary fix: `received_bits = 281`, `total_errors = 127`, `payload_errors = 114` при `start_offset = 34`, `tx_phase = 315 deg`, `rx_gain = 5 dB`. |
| `docs/assets/lab125_runtime_bridge_txrx_self_timed_single_point_live_20260623.json` | Первое self-timed runtime-доказательство для `bridge_txrx_mux`: PL-owned TX/RX path теперь завершает полный кадр длиной `281 бит` без timeout после hot-load и RX-common re-init, то есть прежняя неопределенность host-driven cyclic-TX пути уже не мешает самому факту приема кадра. |
| `docs/assets/lab125_runtime_bridge_txrx_self_timed_summary_live_20260624.json` | Краткая follow-up сводка по timing-clean rebuild от `2026-06-24`: strict full-preamble live lock все еще уходит в timeout, но новый coarse 4-bit acquisition prefix уже возвращает стабильные self-timed full-frame runtime точки на `neg-q` при `start_offset = 58..60`, с лучшей сохраненной точкой `281 / 141 / 132`. |
| `docs/assets/lab126_runtime_bridge_txrx_self_timed_mode_sweep_live_20260623.json` | Exploratory self-timed sweep по осям решения `I`, `-I`, `Q` и `-Q`, показывающий, что даже простой выбор polarity/axis уже меняет BER и что в-session лучшим из четырех режимов оказывается `neg-i`. |
| `docs/assets/lab126_runtime_bridge_txrx_self_timed_neg_i_single_point_live_20260623.json` | Чистый single-point rerun self-timed режима `neg-i` с автоматическим возвратом платы в stock state после завершения, показывающий, что deterministic path остается full-frame, но BER все еще чувствителен к session state. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_14_stock_shell_bpsk_ota.py` | Host-driven stock-shell AD9361 fallback, который передает детерминированный OTA BPSK burst через уже доказанный Linux TX/RX DMA path, считает BER/EVM и теперь еще принудительно возвращает safe TX state через SSH/sysfs после завершения. |
| `datasets/lab11_14_stock_shell_bpsk_ota/manifest_live_20260623d.yaml` | Первый успешный live manifest для stock-shell OTA BPSK: `915 MHz`, `3.84 MS/s`, `240 ksym/s`, `TX -50 dB`, `RX +35 dB`, frame detected, `BER = 0`. |
| `docs/assets/lab114_stock_shell_bpsk_ota_live_20260623d_metrics.json` | Живые метрики первого успешного stock-shell OTA BPSK fallback run: состояние платы до и после конфигурации, нулевой BER, EVM и амплитудные метрики захвата. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_20_read_rtl_wav_ota_bpsk_ber.py` | Офлайн reader для RTL-SDR/SDR++ WAV IQ: переиспользует детерминированный BPSK-эталон Lab 11.14, ищет остаточное частотное смещение, при необходимости делает пересэмплирование `4.0 -> 3.84 MS/s` и считает BER/EVM по мониторинговым записям. |
| `datasets/lab11_20_rtl_sdr_ota_bpsk/manifest_template.yaml` | Стартовый manifest для локальных RTL-SDR monitor-capture, чтобы внешний WAV-путь запускал BER-анализатор напрямую, а не оставался только описанием метаданных. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_21_capture_rtl_sdr_monitor_wav.py` | Host-side helper, который включает stock-shell BPSK-передатчик на ZynqSDR, пишет свежий monitor WAV IQ через RTL-SDR по `rtlsdr.dll` и формирует manifest для офлайн BER-reader. |
| `datasets/lab11_20_rtl_sdr_ota_bpsk/manifest_live_20260624a.yaml` | Первый свежий локальный manifest для RTL-SDR monitor-capture против stock-shell BPSK TX path на ZynqSDR: `915 MHz`, `2.4 MS/s`, готов к прямому BER-replay через новый офлайн reader. |
| `docs/assets/lab1121_rtl_sdr_monitor_live_20260624a.json` | Capture-report первого автоматизированного прогона helper'а `ZynqSDR -> RTL-SDR monitor`, включая модель RTL-донгла, sample rate, TX attenuation и статистику по сырым unsigned IQ-отсчётам. |
| `docs/assets/lab1120_lab11_20_rtl_sdr_ota_bpsk_live_20260624a_metrics.json` | Первый живой офлайн BER-результат RTL-SDR для stock-shell BPSK-передатчика ZynqSDR: frame detected, `BER total = 0`, `BER payload = 0`, без клиппинга в monitor-захвате и с измеренным остаточным смещением около `+2.4 kHz`. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_22_capture_runtime_pl_rtl_monitor_wav.py` | Helper для runtime-path monitor-захвата: hot-load'ит `bridge_txrx_mux`, настраивает AD9361, пишет свежий RTL-SDR WAV вокруг повторных PL-owned BPSK start pulse и формирует manifest, который можно напрямую replay'ить офлайн BER-reader'ом. |
| `datasets/lab11_22_runtime_pl_rtl_monitor/manifest_live_20260624_runtime_pl_a.yaml` | Первый свежий локальный manifest RTL-SDR monitor-capture для runtime/PL BPSK path на `915 MHz` и `2.4 MS/s`, уже привязанный к общему пакету `end_to_end_bpsk_reference`, а не к stock-shell fallback-волне. |
| `docs/assets/lab1122_runtime_bridge_txrx_self_timed_live_20260624_runtime_pl_a.json` | Живой runtime bring-up report для прогона с внешним мониторингом: self-timed PL path дошел до полного кадра `281 бит` на `neg-q`, `start_offset = 59`, с лучшим сохраненным внутренним результатом `281 / 131 / 115`. |
| `docs/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_live_20260624_runtime_pl_a_live_20260624_runtime_pl_a_metrics.json` | Первый живой офлайн BER-результат RTL-SDR уже для runtime/PL BPSK path: внешний монитор действительно демодулирует переданный кадр и измеряет `BER total = 105 / 281`, `BER payload = 99 / 256`, так что оставшийся blocker теперь точно в устойчивости BER, а не в отсутствии OTA-излучения. |
| `blocks/block_11_integrated_sdr_project/python/lab_11_23_runtime_pl_rtl_monitor_sweep.py` | Focused helper для runtime/PL external-monitor sweep: прогоняет компактную область параметров вокруг уже живой точки, ранжирует каждую конфигурацию по офлайн RTL-SDR BER и умеет отдельно rerun'ить лучшую точку как каноническое evidence. |
| `docs/assets/lab1123_runtime_pl_rtl_monitor_sweep_live_20260624_runtime_pl_sweep_a.json` | Сводка focused live sweep по `start_offset = 58..60`, `RX gain = 5,10,15 dB`, `TX attenuation = -50,-45 dB` и отдельной донастройке tuner gain: лучшая измеренная точка оказалась `start_offset = 60`, `RX = 10 dB`, `TX = -45 dB`, `RTL gain = 20.0 dB`, с временным внешним BER `95 / 281` и payload BER `90 / 256`. |
| `datasets/lab11_22_runtime_pl_rtl_monitor/manifest_live_20260624_runtime_pl_sweep_a_best.yaml` | Канонический manifest повторного прогона лучшей runtime/PL monitor-точки, перенесенный из временного sweep-workspace в постоянное дерево датасетов. |
| `docs/assets/lab1122_runtime_bridge_txrx_self_timed_live_20260624_runtime_pl_sweep_a_best.json` | Runtime bring-up report для повторного прогона лучшей sweep-точки: self-timed PL path снова доходит до полного кадра `281 бит` при `start_offset = 60`, `RX = 10 dB`, `TX = -45 dB`. |
| `docs/assets/lab1122_runtime_pl_rtl_monitor_live_20260624_runtime_pl_sweep_a_best.json` | External-monitor capture report повторного прогона лучшей точки, включая выбранные runtime-параметры и статистику по сырым unsigned-IQ отсчетам в продвинутом evidence-захвате. |
| `docs/assets/lab1120_lab11_22_runtime_pl_rtl_monitor_live_20260624_runtime_pl_sweep_a_best_live_20260624_runtime_pl_sweep_a_best_metrics.json` | Улучшенное каноническое живое RTL-SDR BER-evidence уже для runtime/PL BPSK path: повторный прогон лучшей точки измеряет `BER total = 99 / 281`, `BER payload = 93 / 256`, то есть улучшает прежний baseline `105 / 281`, но одновременно показывает заметную межзапусковую вариативность даже на лучшем параметре. |
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
- Block 1 уже включает и реальные пассивные RTL-SDR записи из SDR++, и управляемую лабораторную с DDS-тоном Zynq, наблюдаемым через RTL-SDR; обе ветки снабжены manifest и метаданными воспроизводимости.

## Главные пробелы, которые нужно закрыть

1. Заменить manifest-only QPSK-датасет на маленький подтвержденный файл или внешнюю ссылку.
2. Расширить первые измерения на реальной плате для тракта Zynq/AD9363 до полного gain/loopback package и превратить новый post-reinit runtime BPSK receive path в повторяемый low-BER сценарий.
3. Повысить Block 5 OOC FPGA-отчеты до данных по top-level placed-and-routed дизайну.
4. Держать RU/EN страницы синхронными при добавлении новых лабораторных.
5. Довести один QPSK- или tone-сценарий до полного финального отчета с графиками и ограничениями.
6. Проверить публикационный/юридический статус реальных off-air записей, прежде чем считать их публично распространяемыми данными курса.

## Приоритетные улучшения

1. Поднять один полный сценарий `Model -> FPGA -> RF -> Measurement` до статуса portfolio-ready, используя новый post-reinit runtime BPSK receive path как кратчайший аппаратный маршрут.
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
