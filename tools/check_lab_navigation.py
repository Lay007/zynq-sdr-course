#!/usr/bin/env python3
"""Ensure publishable lab pages are represented in the MkDocs configuration.

The check scans bilingual lab directories and requires every publishable lab or
final-project page to be present in ``nav``, explicitly listed in
``not_in_nav``, or temporarily recorded in the navigation allowlist.

The allowlist exists only for known pre-existing debt. New pages must be added
to ``mkdocs.yml`` in the same change that creates them.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "mkdocs.yml"
ALLOWLIST = ROOT / "tools" / "lab_navigation_allowlist.txt"
LAB_PREFIXES = ("lab-", "project-")
LANGUAGES = ("ru", "en")


class MkDocsLoader(yaml.SafeLoader):
    """Safe YAML loader that tolerates MkDocs Python-name extension tags."""


def _python_name_as_text(
    loader: MkDocsLoader,
    suffix: str,
    node: yaml.Node,
) -> str:
    del loader, node
    return suffix


MkDocsLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:",
    _python_name_as_text,
)


@dataclass(frozen=True)
class NavigationReport:
    missing: tuple[str, ...]
    known_debt: tuple[str, ...]
    stale_allowlist: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing and not self.stale_allowlist


def _collect_markdown_paths(node: Any) -> set[str]:
    paths: set[str] = set()

    if isinstance(node, str):
        if node.endswith(".md"):
            paths.add(node.replace("\\", "/"))
        return paths

    if isinstance(node, list):
        for item in node:
            paths.update(_collect_markdown_paths(item))
        return paths

    if isinstance(node, dict):
        for value in node.values():
            paths.update(_collect_markdown_paths(value))

    return paths


def _parse_not_in_nav(value: Any) -> set[str]:
    if value is None:
        return set()

    if isinstance(value, str):
        return {
            line.strip().replace("\\", "/")
            for line in value.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

    return _collect_markdown_paths(value)


def _read_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()

    return {
        line.strip().replace("\\", "/")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _iter_publishable_lab_pages(docs_dir: Path) -> set[str]:
    pages: set[str] = set()

    for language in LANGUAGES:
        lab_dir = docs_dir / language / "labs"
        if not lab_dir.exists():
            continue

        for path in lab_dir.glob("*.md"):
            if path.name.startswith(LAB_PREFIXES):
                pages.add(path.relative_to(docs_dir).as_posix())

    return pages


def check_navigation(
    root: Path = ROOT,
    config_path: Path | None = None,
    allowlist_path: Path | None = None,
) -> NavigationReport:
    config_path = config_path or root / "mkdocs.yml"
    allowlist_path = allowlist_path or root / "tools" / "lab_navigation_allowlist.txt"

    config = yaml.load(
        config_path.read_text(encoding="utf-8"),
        Loader=MkDocsLoader,
    )
    if not isinstance(config, dict):
        raise ValueError(f"{config_path} must contain a YAML mapping")

    docs_dir = root / str(config.get("docs_dir", "docs"))
    pages = _iter_publishable_lab_pages(docs_dir)
    nav_paths = _collect_markdown_paths(config.get("nav", []))
    excluded_paths = _parse_not_in_nav(config.get("not_in_nav"))
    allowlisted_paths = _read_allowlist(allowlist_path)

    represented = nav_paths | excluded_paths | allowlisted_paths
    missing = tuple(sorted(pages - represented))
    known_debt = tuple(sorted(pages & allowlisted_paths))
    stale_allowlist = tuple(sorted(allowlisted_paths - pages))

    return NavigationReport(
        missing=missing,
        known_debt=known_debt,
        stale_allowlist=stale_allowlist,
    )


def main() -> int:
    report = check_navigation()

    if report.missing:
        print("Lab navigation check failed: pages missing from mkdocs.yml:")
        for path in report.missing:
            print(f"  - {path}")
        print(
            "Add each page to nav/not_in_nav. Use the allowlist only for "
            "documented pre-existing debt."
        )

    if report.stale_allowlist:
        print("Lab navigation check failed: stale allowlist entries:")
        for path in report.stale_allowlist:
            print(f"  - {path}")
        print("Remove entries after deleting a page or adding it to navigation.")

    if not report.ok:
        return 1

    if report.known_debt:
        print("Lab navigation check passed with known navigation debt:")
        for path in report.known_debt:
            print(f"  - {path}")
    else:
        print("Lab navigation check passed with no navigation debt.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
