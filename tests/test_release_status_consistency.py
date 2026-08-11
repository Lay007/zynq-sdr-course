from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_surfaces_point_to_the_final_differential_modem() -> None:
    release_notes = (ROOT / "docs" / "release-notes-v0.1.0.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "status.md").read_text(encoding="utf-8")
    lab_index = (ROOT / "docs" / "lab-index.md").read_text(encoding="utf-8")

    assert "11.41–11.45" in release_notes
    assert "Portfolio-ready (two-board link complete)" in status
    assert "11.1-11.45" in lab_index
    assert "gross rotation 0" in lab_index


def test_release_surfaces_do_not_restore_the_pre_report_roadmap_claim() -> None:
    checklist = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    assert "clear roadmap toward one portfolio-ready" not in checklist
    assert "hardware-validated portfolio-ready model-to-measurement report" in checklist
