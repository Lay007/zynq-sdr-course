"""Formatting rules for the course pages that MkDocs renders.

- Every opening code fence names a language (``text`` for diagrams and output).
- A wrapper page under docs/ that includes a snippet starting with an H1 has no
  H1 of its own; otherwise MkDocs renders the title twice.
- Lab and project H1s read 'Lab N.M — Title' (Russian pages: 'Лабораторная N.M — ...').
- The Russian navigation in mkdocs.yml labels pages in Russian.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CYRILLIC = re.compile("[А-Яа-яЁё]")
INCLUDE = re.compile(r'^--8<-- "([^"]+)"\s*$', re.MULTILINE)
LAB_H1 = re.compile(r"^# (Lab|Лабораторная|Project|Проект) (\d+\.\d+)(.*)$")


def course_pages() -> list[Path]:
    return sorted((ROOT / "blocks").rglob("*.md")) + sorted((ROOT / "docs").rglob("*.md"))


def is_russian(path: Path) -> bool:
    return "/docs/ru/" in path.as_posix() or path.stem.endswith("_ru")


def test_code_fences_name_a_language():
    bare = []
    for path in course_pages():
        inside = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("```"):
                continue
            if not inside and stripped == "```":
                bare.append(f"{path.relative_to(ROOT)}:{number}")
            inside = not inside
    assert not bare, f"code fences without a language: {bare}"


def test_wrapper_pages_do_not_repeat_the_included_h1():
    repeated = []
    for path in sorted((ROOT / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = INCLUDE.search(text)
        if not match or not text.startswith("# "):
            continue
        included = ROOT / match.group(1)
        if included.exists() and included.read_text(encoding="utf-8").lstrip().startswith("# "):
            repeated.append(str(path.relative_to(ROOT)))
    assert not repeated, f"wrapper H1 duplicates the included page's H1: {repeated}"


def lab_pages() -> list[Path]:
    pages = [p for p in (ROOT / "blocks").rglob("*.md") if p.name.startswith(("lab_", "project_"))]
    return sorted(pages) + sorted((ROOT / "docs").glob("*/labs/*.md"))


def test_lab_titles_use_one_form():
    wrong = []
    for path in lab_pages():
        first = path.read_text(encoding="utf-8").split("\n", 1)[0].rstrip("\r")
        match = LAB_H1.match(first)
        if not match:
            continue
        kind, _, rest = match.groups()
        if not rest.startswith(" — ") or (is_russian(path) and kind == "Lab"):
            wrong.append(f"{path.relative_to(ROOT)}: {first}")
    assert not wrong, f"lab/project H1 not in the 'Lab N.M — Title' form: {wrong}"


def test_russian_navigation_labels_are_russian():
    english = []
    for line in (ROOT / "mkdocs.yml").read_text(encoding="utf-8").splitlines():
        match = re.match(r'\s+- "(.*)": (ru/\S+\.md)\s*$', line)
        if match and (not CYRILLIC.search(match.group(1)) or match.group(1).startswith("Lab ")):
            english.append(match.group(1))
    assert not english, f"Russian nav entries with English labels: {english}"
