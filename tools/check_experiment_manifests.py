#!/usr/bin/env python3
"""Validate experiment manifest files.

The checker is intentionally lightweight and dependency-free. It verifies that
YAML manifests contain the core fields expected by the course documentation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = ROOT / "experiments"
REQUIRED_TOP_LEVEL = {"experiment", "metrics", "reports", "acceptance"}
REQUIRED_EXPERIMENT_FIELDS = {"id", "title", "objective"}


def strip_comments(line: str) -> str:
    if "#" not in line:
        return line
    return line.split("#", 1)[0]


def top_level_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for line in text.splitlines():
        line = strip_comments(line).rstrip()
        if not line or line.startswith(" ") or line.startswith("-"):
            continue
        match = re.match(r"^([A-Za-z0-9_\-]+):", line)
        if match:
            keys.add(match.group(1))
    return keys


def experiment_fields(text: str) -> set[str]:
    fields: set[str] = set()
    in_experiment = False
    for raw in text.splitlines():
        line = strip_comments(raw).rstrip()
        if not line:
            continue
        if re.match(r"^experiment:\s*$", line):
            in_experiment = True
            continue
        if in_experiment and re.match(r"^[A-Za-z0-9_\-]+:", line):
            break
        if in_experiment:
            match = re.match(r"^\s{2}([A-Za-z0-9_\-]+):", line)
            if match:
                fields.add(match.group(1))
    return fields


def validate_manifest(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    keys = top_level_keys(text)
    missing_keys = sorted(REQUIRED_TOP_LEVEL - keys)
    if missing_keys:
        errors.append(f"{path.relative_to(ROOT)}: missing top-level keys: {', '.join(missing_keys)}")

    fields = experiment_fields(text)
    missing_fields = sorted(REQUIRED_EXPERIMENT_FIELDS - fields)
    if missing_fields:
        errors.append(f"{path.relative_to(ROOT)}: missing experiment fields: {', '.join(missing_fields)}")

    if "template:" in text:
        for match in re.finditer(r"template:\s*([^\n]+)", text):
            raw = match.group(1).strip().strip("'\"")
            if raw and not raw.startswith(("http://", "https://")):
                target = (ROOT / raw).resolve()
                try:
                    target.relative_to(ROOT)
                except ValueError:
                    errors.append(f"{path.relative_to(ROOT)}: template escapes repository: {raw}")
                    continue
                if not target.exists():
                    errors.append(f"{path.relative_to(ROOT)}: missing template: {raw}")

    return errors


def main() -> int:
    manifests = sorted(EXPERIMENTS_DIR.glob("*.yaml"))
    if not manifests:
        print("No experiment manifests found.")
        return 1

    errors: list[str] = []
    for manifest in manifests:
        errors.extend(validate_manifest(manifest))

    if errors:
        print("Experiment manifest check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Experiment manifest check passed: {len(manifests)} manifests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
