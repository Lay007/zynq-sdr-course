from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_lab_navigation import check_navigation  # noqa: E402


def _write_fixture(
    root: Path,
    *,
    nav_path: str | None,
    allowlist: str = "",
) -> None:
    lab_path = root / "docs" / "en" / "labs" / "lab-1-1-example.md"
    lab_path.parent.mkdir(parents=True)
    lab_path.write_text("# Example lab\n", encoding="utf-8")

    nav_lines = ""
    if nav_path is not None:
        nav_lines = f'  - "Example": {nav_path}\n'

    (root / "mkdocs.yml").write_text(
        "docs_dir: docs\n"
        "markdown_extensions:\n"
        "  - pymdownx.superfences:\n"
        "      custom_fences:\n"
        "        - name: mermaid\n"
        "          format: "
        "!!python/name:pymdownx.superfences.fence_code_format\n"
        "nav:\n"
        f"{nav_lines}",
        encoding="utf-8",
    )

    allowlist_path = root / "tools" / "lab_navigation_allowlist.txt"
    allowlist_path.parent.mkdir(parents=True)
    allowlist_path.write_text(allowlist, encoding="utf-8")


def test_repository_lab_navigation_has_no_untracked_gaps() -> None:
    report = check_navigation()

    assert not report.missing
    assert not report.stale_allowlist


def test_checker_reports_new_lab_missing_from_navigation(tmp_path: Path) -> None:
    _write_fixture(tmp_path, nav_path=None)

    report = check_navigation(root=tmp_path)

    assert report.missing == ("en/labs/lab-1-1-example.md",)
    assert not report.ok


def test_checker_accepts_known_navigation_debt(tmp_path: Path) -> None:
    path = "en/labs/lab-1-1-example.md"
    _write_fixture(tmp_path, nav_path=None, allowlist=f"{path}\n")

    report = check_navigation(root=tmp_path)

    assert report.known_debt == (path,)
    assert report.ok


def test_checker_rejects_stale_allowlist_entry(tmp_path: Path) -> None:
    path = "en/labs/lab-1-1-example.md"
    _write_fixture(
        tmp_path,
        nav_path=path,
        allowlist="en/labs/lab-9-9-removed.md\n",
    )

    report = check_navigation(root=tmp_path)

    assert report.stale_allowlist == ("en/labs/lab-9-9-removed.md",)
    assert not report.ok
