"""Check the word-length model against the shared RTL vectors and signed limits."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: str):
    spec = spec_from_file_location(name, ROOT / path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lab = load_module("fir_word_lengths", "blocks/block_04_simulink_and_fixed_point/python/lab_4_5_fir_word_lengths.py")
rtl = load_module("fir_architecture_vectors", "tools/run_fir_architectures.py")


def test_baseline_matches_all_rtl_golden_vectors(tmp_path):
    path = tmp_path / "fir_vectors.txt"
    rtl.make_vectors(path)
    lines = iter(path.read_text(encoding="ascii").splitlines())
    for _ in range(int(next(lines))):
        *taps, count = map(int, next(lines).split())
        vector = np.array([list(map(int, next(lines).split())) for _ in range(count)])
        result, events, _ = lab.fir_integer(vector[:, 1:3], np.array(taps), lab.Widths(), "wrap")
        np.testing.assert_array_equal(result, vector[:, 3:5])
        assert events == 0


def test_accumulator_wrap_and_saturate_preserve_different_signs_at_endpoint():
    samples = np.tile([-32768, 32767], (4, 1))
    taps = np.full(4, -32768)
    wrapped, events, _ = lab.fir_integer(samples, taps, lab.Widths(accumulator_bits=33), "wrap")
    saturated, saturations, _ = lab.fir_integer(samples, taps, lab.Widths(accumulator_bits=33), "saturate")
    full, full_events, clipped = lab.fir_integer(samples, taps, lab.Widths(), "wrap")
    assert events == saturations == 1
    assert full_events == 0 and clipped == 7
    assert wrapped[-1].tolist() == [-32768, -32768]
    assert saturated[-1].tolist() == full[-1].tolist() == [32767, -32768]


def test_rounds_signed_half_lsb_once_after_accumulation():
    samples = np.array([[4, -4], [12, -12]])
    result, events, clips = lab.fir_integer(samples, np.array([4096]), lab.Widths(), "wrap")
    assert result.tolist() == [[1, 0], [2, -1]]
    assert events == clips == 0
