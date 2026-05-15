#!/usr/bin/env python3
"""Check local Markdown asset links.

This lightweight checker scans Markdown files and validates local image/file links.
It intentionally ignores external URLs, anchors, mail links and Mermaid content.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_DIRS = [ROOT / "docs", ROOT]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_SRC_RE = re.compile(r"(?:src|href)=\"([^\"]+)\"")

IGNORE_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "#",
    "data:",
)


def iter_markdown_files() -> list[Path]:
    files: set[Path] = set()
    for base in MARKDOWN_DIRS:
        if base.is_file() and base.suffix.lower() == ".md":
            files.add(base)
        elif base.is_dir():
            files.update(base.rglob("*.md"))
    return sorted(files)


def normalize_link(raw: str) -> str | None:
    link = raw.strip().split()[0].strip("'\"")
    if not link or link.startswith(IGNORE_PREFIXES):
        return None
    parsed = urlparse(link)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if not path or path.startswith("#"):
        return None
    return path


def check_file(md_file: Path) -> list[str]:
    text = md_file.read_text(encoding="utf-8")
    raw_links = [m.group(1) for m in LINK_RE.finditer(text)]
    raw_links.extend(m.group(1) for m in HTML_SRC_RE.finditer(text))

    errors: list[str] = []
    for raw in raw_links:
        path = normalize_link(raw)
        if path is None:
            continue
        target = (md_file.parent / path).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            errors.append(f"{md_file.relative_to(ROOT)}: link escapes repository: {raw}")
            continue
        if not target.exists():
            errors.append(f"{md_file.relative_to(ROOT)}: missing local asset: {raw}")
    return errors


def main() -> int:
    errors: list[str] = []
    for md_file in iter_markdown_files():
        errors.extend(check_file(md_file))

    if errors:
        print("Markdown asset check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Markdown asset check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
