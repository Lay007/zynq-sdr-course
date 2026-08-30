from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "blocks"
    / "block_11_integrated_sdr_project"
    / "python"
    / "offline_qpsk_diagnostics.py"
)
SPEC = importlib.util.spec_from_file_location("offline_qpsk_diagnostics", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
DIAG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAG)


def test_render_diagnostics_exports_observable_rx_stages(tmp_path: Path) -> None:
    samples = DIAG.rx.synthetic_reference_capture(
        cfo_hz=14_000.0,
        phase_rad=0.33,
        prefix_samples=333,
        suffix_samples=400,
        snr_db=36.0,
        seed=11381,
    )

    report = DIAG.render_diagnostics(samples, DIAG.rx.MODEL_SAMPLE_RATE_HZ, tmp_path)

    assert report["hardware_rx_claimed"] is False
    assert report["evidence_scope"] == "offline-diagnostics-only"
    assert report["sync_metric_peak"] >= 0.80
    assert abs(report["cfo_hz"] - 14_000.0) <= 500.0
    assert set(report["plots"]) == {
        "spectrum",
        "sync_metric",
        "constellation_before",
        "constellation_after",
        "matched_filter_timing",
    }

    for path_text in report["plots"].values():
        path = Path(path_text)
        assert path.is_file()
        assert path.stat().st_size > 1_000
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
