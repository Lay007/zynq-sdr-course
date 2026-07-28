from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"


def load_asset(name: str) -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def assert_sweep_arithmetic(row: dict) -> None:
    assert row["locked"] + row["lost"] == row["frames"]
    assert row["clean"] + row["single"] + row["gross"] == row["locked"]
    assert row["clean_pct"] == pytest.approx(100 * row["clean"] / row["locked"])
    assert row["gross_pct"] == pytest.approx(100 * row["gross"] / row["locked"])
    assert 0 <= row["payload_ber"] <= 1


def test_lab1144_preserves_the_differential_ab_result() -> None:
    evidence = load_asset("lab1144_diff_qpsk_live.json")
    assert evidence["lab"] == "11.44"

    absolute = evidence["diff_off"]
    differential = evidence["diff_on"]
    assert_sweep_arithmetic(absolute)
    assert_sweep_arithmetic(differential)

    assert absolute["gross"] > 0
    assert differential["gross"] == 0
    assert differential["payload_ber"] < absolute["payload_ber"]


def test_lab1145_preserves_the_final_long_preamble_result() -> None:
    evidence = load_asset("lab1145_diff_long_preamble_live.json")
    assert evidence["lab"] == "11.45"
    assert evidence["frame_symbols"] == 152
    assert evidence["preamble_symbols"] == 24
    assert evidence["payload_bits"] == 256
    assert evidence["mode"] == "differential+gardner"

    assert evidence["clean"] + evidence["single_bit"] + evidence["gross"] == evidence["locked"]
    assert evidence["locked"] <= evidence["frames"]
    assert evidence["clean_pct"] == pytest.approx(
        100 * evidence["clean"] / evidence["locked"],
        abs=0.005,
    )
    assert evidence["gross"] == 0
    assert evidence["payload_ber"] < 5e-4
    assert sum(evidence["single_bit_idx"].values()) == evidence["single_bit"]
