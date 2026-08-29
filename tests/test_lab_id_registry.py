from __future__ import annotations

from pathlib import Path

from tools.check_lab_id_registry import check_registry


ROOT = Path(__file__).resolve().parents[1]


def test_repository_lab_id_registry_is_complete() -> None:
    assert check_registry(ROOT).ok


def test_checker_rejects_unregistered_reuse_of_an_existing_id(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yml"
    registry.write_text(
        """\
block: 11
id_range: [44, 44]
scan_roots:
  - blocks
  - docs
labs:
  "11.44":
    topic: differential-qpsk-live-validation
    artifacts:
      - blocks/lab_11_44_diff_qpsk_live_validation.py
""",
        encoding="utf-8",
    )
    script = tmp_path / "blocks" / "lab_11_44_diff_qpsk_live_validation.py"
    script.parent.mkdir(parents=True)
    script.write_text("# canonical owner\n", encoding="utf-8")
    page = tmp_path / "docs" / "lab-11-44-unrelated-topic.md"
    page.parent.mkdir(parents=True)
    page.write_text("# conflicting owner\n", encoding="utf-8")

    report = check_registry(tmp_path, registry)

    assert report.unknown == ("docs/lab-11-44-unrelated-topic.md",)
    assert not report.ok
