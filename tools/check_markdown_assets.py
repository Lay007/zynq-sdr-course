#!/usr/bin/env python3
"""Check local Markdown asset links used by the MkDocs site.

The checker is intentionally conservative:
- it scans only `docs/**/*.md` and the root `README.md`;
- it validates image links and explicit file links;
- it ignores external URLs, anchors, mail links and site-absolute MkDocs URLs;
- it ignores directory-style MkDocs links such as `demo/` because MkDocs resolves them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
README = ROOT / "README.md"
SITE_PREFIX = "/zynq-sdr-course/"

MARKDOWN_LINK_RE = re.compile(r"(!?)\[[^\]]*\]\(([^)]+)\)")
HTML_LINK_RE = re.compile(r"(?P<attr>src|href)=\"(?P<link>[^\"]+)\"")

IGNORE_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "#",
    "data:",
)

FILE_SUFFIXES = {
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
}


def iter_markdown_files() -> list[Path]:
    files: set[Path] = set(DOCS.rglob("*.md"))
    if README.exists():
        files.add(README)
    return sorted(files)


def normalize_link(raw: str) -> str | None:
    link = raw.strip().split()[0].strip("'\"")
    if not link or link.startswith(IGNORE_PREFIXES):
        return None

    if link.startswith(SITE_PREFIX):
        return None

    parsed = urlparse(link)
    if parsed.scheme or parsed.netloc:
        return None

    path = unquote(parsed.path)
    if not path or path.startswith("#"):
        return None

    # MkDocs directory-style links, for example `demo/` or `model-to-measurement/`,
    # are valid site links and are resolved by MkDocs rather than the filesystem.
    if path.endswith("/"):
        return None

    # Do not treat extensionless links as assets. MkDocs can resolve many of them
    # through the nav and permalink configuration.
    suffix = Path(path).suffix.lower()
    if not suffix:
        return None
    if suffix not in FILE_SUFFIXES:
        return None

    return path


def check_file(md_file: Path) -> list[str]:
    text = md_file.read_text(encoding="utf-8")
    raw_links: list[str] = []

    for match in MARKDOWN_LINK_RE.finditer(text):
        is_image, link = match.groups()
        raw_links.append(link)

    raw_links.extend(match.group("link") for match in HTML_LINK_RE.finditer(text))

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
