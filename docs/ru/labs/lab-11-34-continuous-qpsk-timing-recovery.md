# Лабораторная 11.34 — непрерывное восстановление тактовой фазы QPSK

## Цель

Заменить одноразовый выбор целочисленной фазы непрерывным timing-контуром, способным
компенсировать рассогласование sample clocks, и сохранить baseline в том же bitstream для
честного runtime A/B. Живой эксперимент завершён: Gardner заметно повышает вероятность
получить полный кадр, но не проходит заранее заданный критерий по доле чистых попыток во всём
CFO sweep, поэтому baseline остаётся режимом по умолчанию.

## Что реализовано

Новый `qpsk_symbol_timing_recovery.v` содержит комплексный sign-Gardner:

1. Q16 NCO создаёт два интерполяционных строба на символ.
2. Линейный интерполятор вычисляет sample на дробной фазе между соседними выходами matched
   filter.
3. Чётные стробы выдают символ, нечётные сохраняют середину символа.
4. TED объединяет обе квадратуры:

   `e = sign(sign(I_mid) * sign(I_now - I_prev) + sign(Q_mid) * sign(Q_now - Q_prev))`

5. PI-фильтр обновляет `omega` с ограничением вокруг номинального шага `2/SPS`.

Первый аппаратный кандидат использовал `K1=1/256`, `K2=1/4096`; live-телеметрия показала
размах `omega_q16` 15 600…16 848 при номинале 16 384. В ретюненном кандидате оба коэффициента
уменьшены вдвое, до `K1=1/512`, `K2=1/8192`. Нулевые ошибки модельных drift-тестов сохранены,
а live-размах во всём sweep сузился до 16 088…16 672.

Python-модель точно повторяет fixed-point арифметику и семантику nonblocking assignments.
Общего делителя в RTL нет: при `SPS=8` вычисление `mu/omega` сводится к ограниченной
фиксированной операции.

## Runtime-интерфейс

В bridge обе реализации собраны одновременно:

| `gp_ctrl[14]` | Режим |
|---:|---|
| 0 | прежний fixed-phase sampler |
| 1 | непрерывный Gardner, phase picker принудительно bypass |

При включённом bit 14 в `gp_adc_input_debug` доступны `{omega[15:0], mu[15:0]}`, а capture
debug показывает знаковую трёхуровневую ошибку TED. После runtime mux добавлен один регистр
`valid/I/Q`: он даёт одинаковую задержку данным и разрывает путь от синхронизированного
control bit через mux и два DSP coarse-CFO за один 8-нс такт.

Принятый boot image Lab 11.33 не заменяется до завершения живого A/B.

## Модель

```powershell
python blocks/block_05_fpga_hdl_flow/python/qpsk_timing_recovery_model.py
```

| Samples/symbol | Float Gardner | Fixed Gardner | Fixed phase |
|---:|---:|---:|---:|
| 8.000 | 0 | 0 | 0 |
| 8.030 | 0 | 0 | 0 |
| 8.060 | 0 | 0 | 14 |
| 7.970 | 0 | 0 | 0 |
| 7.940 | 0 | 0 | 12 |

На длинной последовательности из 12 000 символов при реалистичных ±100 ppm fixed-point
Gardner даёт 0 ошибок. Лучший постоянный offset даёт 1790 ошибок при +100 ppm и 1789 при
−100 ppm: начальная удачная фаза не компенсирует накопленный уход часов.

## RTL-регрессии

```powershell
python tools/run_block5_hdl_smoke.py `
  --test tb_qpsk_symbol_timing_recovery `
  --test tb_qpsk_timing_recovery_chain `
  --test tb_qpsk_timing_recovery_mux `
  --test tb_qpsk_timing_recovery_retained
```

Проверено:

- standalone RTL bit-exact совпадает с integer-моделью на 140 символах при `SPS=8.06`;
- полная drifted chain даёт 0/280 ошибок против 15/280 у fixed sampler;
- runtime mux сохраняет тот же результат;
- на сохранённом двухплатном захвате +30 кГц чистыми остаются offsets 3, 4 и 7;
- прежние QPSK top и bridge loopback сохраняют BER=0.

## Физическая реализация

Первый route обнаружил ошибку покрытия XDC: multicycle для timing recovery совпадал только с
BPSK hierarchy. QPSK recurrence длиной 24,836 нс анализировался как одноклоковый и дал
`WNS=-17.340 ns`. После применения корректного setup/hold 4/3 route достиг
`WNS=-0.188 ns`, `TNS=-6.084 ns`, hold `+0.033 ns`.

Худший путь уже шёл не внутри Gardner, а от `gp_ctrl[14]` через runtime mux в coarse-CFO DSP.
Post-route physopt улучшил лишь 0,002 нс, поэтому вместо ослабления constraints добавлена
регистровая граница.

Первый зарегистрированный кандидат закрыл physical gate при `WNS=+0,049 нс` и позволил
обнаружить лишнюю подвижность контура. После ретюнинга PI и post-route physical optimization
итоговый кандидат также закрыл timing:

- `WNS=+0,003 нс`, `TNS=0,000 нс`;
- `WHS=+0,041 нс`, `THS=0,000 нс`;
- разведены все 77 389 routable nets, routing errors отсутствуют;
- bitgen завершился без errors и critical warnings.

Проверенный boot-образ находится в
`tmp/snapshot_impl_sweep/lab1134_retuned_postroute/system_top.bit`. SHA-256:
`2493b26225b76768ccff985359570761a424a0b6522a70ef4d7e111bbc5ef380`.
Board B чисто загрузилась с него, AD9361 инициализировался, course core ID равен
`0x4250534B`.

## Результат живого A/B

Board A работала как vendor cyclic-DMA TX, board B — как course RX. Кабельный тракт:
915 МГц, 30 dB attenuator, TX −30 dB, RX +50 dB. Оба режима проверялись на одном bitstream
с одинаковыми CFO, offsets и числом повторов; no-lock оставался в знаменателе.

| Кампания | Режим | Полные кадры | BER=0 attempts | Aggregate BER по полным кадрам |
|---|---|---:|---:|---:|
| +30 кГц, 80 attempts | fixed | 54/80 (67,5%) | 21/80 (26,25%) | 0,192196 |
| +30 кГц, 80 attempts | retuned Gardner | 72/80 (90,0%) | 22/80 (27,5%) | 0,106597 |
| 0…55 кГц, 288 attempts | fixed | 193/288 (67,01%) | 72/288 (25,00%) | 0,137435 |
| 0…55 кГц, 288 attempts | retuned Gardner | 246/288 (85,42%) | 71/288 (24,65%) | 0,119178 |

Сфокусированный gate +30 кГц проходит: Gardner добавляет 18 полных кадров и одну чистую
попытку. В решающем полном sweep он достигает BER=0 во всех 12 точках и добавляет 53 полных
кадра, но чистых попыток на одну меньше. По заранее заданному правилу
`clean_rate_improved && lock_rate_preserved` это reject. Разница слишком мала, чтобы считать
Gardner хуже, но её недостаточно и для замены baseline. Более длинное сравнение со
статистическим запасом будет отдельным экспериментом.

Runner Lab 11.32 теперь поддерживает `--timing-recovery`, поэтому обе кампании используют
один код измерения и отличаются только `gp_ctrl[14]`. Результаты собирает post-processor
Lab 11.34:

```powershell
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py `
  --json-out tmp/lab1134_fixed.json
python blocks/block_11_integrated_sdr_project/python/lab_11_32_two_board_fabric_coarse_cfo.py `
  --timing-recovery --json-out tmp/lab1134_gardner.json
python blocks/block_11_integrated_sdr_project/python/lab_11_34_continuous_qpsk_timing_recovery.py `
  --baseline tmp/lab1134_fixed.json --gardner tmp/lab1134_gardner.json
```

Post-processor отвергает несовпадающие CFO grids, offsets или budgets и оставляет все попытки
в знаменателях lock/clean rate. Сырые attempts, timing-телеметрия и графики сохранены в
`docs/assets/lab1134_*_live_20260721.*`.

Текущий честный вывод: **непрерывный QPSK timing recovery реализован, прошёл модель/RTL,
закрыл timing и измерен на живом кабельном линке. Он сильно повышает full-frame lock, но не
проходит clean-attempt gate полного sweep, поэтому fixed sampler остаётся baseline.**
