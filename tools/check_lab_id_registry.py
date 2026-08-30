#!/usr/bin/env python3
"""Validate canonical ownership of late Block 11 lab identifiers."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "tools" / "lab_id_registry.yml"
SEPARATED_ID = re.compile(r"(?:^|/)lab[-_]11[-_](\d+)")
COMPACT_ID = re.compile(r"(?:^|/)lab11(\d+)")
PYTHON_CACHE_DIR = "__pycache__"
PYTHON_CACHE_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class RegistryReport:
    unknown: tuple[str, ...]
    stale: tuple[str, ...]
    mismatched: tuple[str, ...]
    duplicate: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not (self.unknown or self.stale or self.mismatched or self.duplicate)


def _load_registry(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _artifact_id(path: str) -> str | None:
    match = SEPARATED_ID.search(path) or COMPACT_ID.search(path)
    if match is None:
        return None
    return f"11.{int(match.group(1))}"


def _is_transient_python_cache(path: Path) -> bool:
    return PYTHON_CACHE_DIR in path.parts or path.suffix in PYTHON_CACHE_SUFFIXES


def check_registry(
    root: Path = ROOT,
    registry_path: Path | None = None,
) -> RegistryReport:
    registry_path = registry_path or root / "tools" / "lab_id_registry.yml"
    data = _load_registry(registry_path)

    block = int(data.get("block", 0))
    if block != 11:
        raise ValueError("the current registry checker supports Block 11")

    id_range = data.get("id_range")
    if not isinstance(id_range, list) or len(id_range) != 2:
        raise ValueError("id_range must contain [minimum, maximum]")
    minimum, maximum = (int(value) for value in id_range)

    scan_roots = data.get("scan_roots")
    if not isinstance(scan_roots, list) or not all(isinstance(item, str) for item in scan_roots):
        raise ValueError("scan_roots must be a list of repository-relative paths")

    labs = data.get("labs")
    if not isinstance(labs, dict):
        raise ValueError("labs must be a mapping")

    discovered: set[str] = set()
    for relative_root in scan_roots:
        base = root / relative_root
        if not base.exists():
            continue
        for candidate in base.rglob("*"):
            if not candidate.is_file() or _is_transient_python_cache(candidate):
                continue
            relative = candidate.relative_to(root).as_posix()
            lab_id = _artifact_id(relative)
            if lab_id is None:
                continue
            number = int(lab_id.split(".", maxsplit=1)[1])
            if minimum <= number <= maximum:
                discovered.add(relative)

    owners: dict[str, list[str]] = {}
    stale: list[str] = []
    mismatched: list[str] = []

    for raw_lab_id, entry in labs.items():
        lab_id = str(raw_lab_id)
        if not isinstance(entry, dict):
            raise ValueError(f"registry entry {lab_id} must be a mapping")
        artifacts = entry.get("artifacts")
        if not isinstance(artifacts, list) or not all(isinstance(item, str) for item in artifacts):
            raise ValueError(f"registry entry {lab_id} must contain an artifacts list")

        for pattern in artifacts:
            matches = sorted(
                candidate.relative_to(root).as_posix()
                for candidate in root.glob(pattern)
                if candidate.is_file()
            )
            if not matches:
                stale.append(f"{lab_id}: {pattern}")
                continue
            for relative in matches:
                owners.setdefault(relative, []).append(lab_id)
                encoded_id = _artifact_id(relative)
                if encoded_id != lab_id:
                    mismatched.append(f"{lab_id} owns {relative}, which encodes {encoded_id}")

    unknown = sorted(discovered - owners.keys())
    duplicate = sorted(
        f"{path}: {', '.join(lab_ids)}"
        for path, lab_ids in owners.items()
        if len(lab_ids) > 1
    )
    return RegistryReport(
        unknown=tuple(unknown),
        stale=tuple(sorted(stale)),
        mismatched=tuple(sorted(mismatched)),
        duplicate=tuple(duplicate),
    )


def main() -> int:
    report = check_registry()
    if report.ok:
        print("Lab ID registry check passed.")
        return 0

    sections = (
        ("Unregistered Block 11 artifacts", report.unknown),
        ("Stale registry patterns", report.stale),
        ("Registry ID mismatches", report.mismatched),
        ("Artifacts with multiple owners", report.duplicate),
    )
    for title, rows in sections:
        if not rows:
            continue
        print(f"{title}:")
        for row in rows:
            print(f"  - {row}")
    print(
        "Update tools/lab_id_registry.yml under the canonical topic, "
        "or choose an unused lab ID."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
