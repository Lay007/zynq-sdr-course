from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "blocks" / "block_03_dsp_basics" / "python"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PY / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LAB31 = _load("lab_3_1_fft_windows")
LAB32 = _load("lab_3_2_fir_low_pass")
LAB33 = _load("lab_3_3_digital_mixing")
LAB34 = _load("lab_3_4_decimation")


def test_lab31_enbw_and_scalloping_match_textbook_values() -> None:
    results = {
        name: LAB31.analyse(name, w) for name, w in LAB31.windows(LAB31.N).items()
    }
    assert abs(results["rectangular"].enbw_bins - 1.0) < 1e-9
    assert abs(results["hann"].enbw_bins - 1.5) < 0.01
    # Rectangular window loses the most on an off-bin tone.
    assert (
        results["rectangular"].scalloping_loss_db > results["hann"].scalloping_loss_db
    )
    assert results["blackman"].scalloping_loss_db < results["hann"].scalloping_loss_db


def test_lab31_weak_tone_is_hidden_by_rectangular_and_visible_with_blackman() -> None:
    results = {
        name: LAB31.analyse(name, w) for name, w in LAB31.windows(LAB31.N).items()
    }
    assert results["rectangular"].weak_tone_visibility_db < 0.0
    assert results["hann"].weak_tone_visibility_db > 6.0
    assert (
        results["blackman"].weak_tone_visibility_db
        > results["hann"].weak_tone_visibility_db
    )


def test_lab32_filter_passes_wanted_and_rejects_interferer() -> None:
    h = LAB32.design_lowpass()
    gains = LAB32.response_db(h, np.array([LAB32.WANTED_HZ, LAB32.INTERFERER_HZ]))
    assert abs(gains[0]) < 0.01
    assert gains[1] < -100.0


def test_lab32_q15_taps_raise_the_stopband_floor() -> None:
    h = LAB32.design_lowpass()
    grid = np.linspace(LAB32.STOPBAND_START_HZ, LAB32.FS_HZ / 2, 4001)
    float_peak = LAB32.response_db(h, grid).max()
    q15_peak = LAB32.response_db(LAB32.quantize_q15(h), grid).max()
    assert q15_peak > float_peak + 10.0


def test_lab33_sign_convention_and_nco_resolution() -> None:
    t = np.arange(LAB33.N) / LAB33.FS_HZ
    x = np.exp(1j * 2 * np.pi * LAB33.TONE_HZ * t)
    assert abs(LAB33.peak_hz(x * LAB33.ideal_nco(LAB33.SHIFT_HZ))) < 1.0
    assert abs(LAB33.peak_hz(x * LAB33.ideal_nco(-LAB33.SHIFT_HZ)) - 840e3) < 100.0
    assert LAB33.phase_increment(LAB33.SHIFT_HZ) == 3543348019


def test_lab33_each_extra_lut_address_bit_buys_about_6_db() -> None:
    spur8 = LAB33.worst_spur_dbc(LAB33.hardware_nco(LAB33.SHIFT_HZ, lut_addr_bits=8))
    spur10 = LAB33.worst_spur_dbc(LAB33.hardware_nco(LAB33.SHIFT_HZ, lut_addr_bits=10))
    assert 10.0 < spur8 - spur10 < 14.0


def test_lab34_alias_prediction_and_suppression() -> None:
    assert LAB34.alias_hz(520e3, 600e3) == -80e3
    assert LAB34.alias_hz(250e3, 600e3) == 250e3
    x = LAB34.make_signal()
    bad = x[:: LAB34.M]
    good = np.convolve(x, LAB34.design_lowpass(), mode="same")[:: LAB34.M]
    bad_dbc = LAB34.level_at(bad, LAB34.FS_OUT_HZ, -80e3) - LAB34.level_at(
        bad, LAB34.FS_OUT_HZ, 80e3
    )
    good_dbc = LAB34.level_at(good, LAB34.FS_OUT_HZ, -80e3) - LAB34.level_at(
        good, LAB34.FS_OUT_HZ, 80e3
    )
    assert abs(bad_dbc - (-6.0)) < 0.5
    assert good_dbc < -90.0


LAB36 = _load("lab_3_6_convolution_correlation")


def test_lab36_correlation_finds_the_exact_delay() -> None:
    # Regression: mode="same" on the causal channel shifted the preamble by one sample.
    preamble = LAB36.qpsk_preamble(64)
    rx = LAB36.make_received_signal(preamble, 512)
    filtered = np.convolve(rx, LAB36.lowpass_fir(), mode="same")
    assert int(np.argmax(LAB36.matched_correlation(filtered, preamble))) == 512
