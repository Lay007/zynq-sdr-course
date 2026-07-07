from __future__ import annotations

import json
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from aggregate_lab11_28_sessions import aggregate_sessions  # noqa: E402


def write_metrics(path: Path, *, errors: list[int], safe_reboot: bool = True) -> None:
    frames = [
        {
            "detected": True,
            "bit_errors": error,
            "evm_percent": 20.0 + index,
            "snr_from_evm_db": 14.0 - index,
            "total_frequency_shift_hz": 1_950.0 + index,
            "normalized_correlation": 0.97,
        }
        for index, error in enumerate(errors)
    ]
    total_errors = sum(errors)
    zero = sum(error == 0 for error in errors)
    payload = {
        "analysis_mode": "multi_burst",
        "dataset_id": path.stem,
        "capture_sha256": path.stem * 4,
        "symbol_rate_hz": 480_000,
        "symbol_count": 140,
        "raw_clipping_fraction": 0.0,
        "session": {
            "run_tag": path.stem,
            "bitstream_md5": "abc123",
            "center_frequency_hz": 868_300_000,
            "transmitter_sample_rate_hz": 3_840_000,
            "rtl_sample_rate_hz": 2_400_000,
            "tx_attenuation_db": -50.0,
            "rtl_tuner_gain_db10": 300,
            "reboot_to_stock_ok": safe_reboot,
        },
        "burst_analysis": {
            "summary": {
                "commanded_burst_count": len(errors),
                "detected_burst_count": len(errors),
                "zero_error_burst_count": zero,
                "compared_bits_total": len(errors) * 280,
                "bit_errors_total": total_errors,
                "aggregate_ber": total_errors / (len(errors) * 280),
                "evm_percent": {"median": 20.5},
                "snr_from_evm_db": {"median": 13.5},
                "frequency_shift_hz": {"median": 1_950.5},
            },
            "frames": frames,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_aggregate_sessions_counts_cross_session_results(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a.json"
    run_b = tmp_path / "run_b.json"
    write_metrics(run_a, errors=[0, 0])
    write_metrics(run_b, errors=[0, 1])

    summary = aggregate_sessions([run_a, run_b])

    assert summary["session_count"] == 2
    assert summary["successful_sessions"] == 1
    assert summary["safe_reboot_sessions"] == 2
    assert summary["commanded_bursts"] == 4
    assert summary["detected_bursts"] == 4
    assert summary["zero_error_bursts"] == 3
    assert summary["bit_errors"] == 1
    assert summary["compared_bits"] == 1_120
    assert summary["aggregate_ber"] == 1 / 1_120
