#!/usr/bin/env python3
"""Validate dataset manifests and Git LFS pointers used by the course."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT / "datasets"
LFS_VERSION = "https://git-lfs.github.com/spec/v1"
LFS_POINTER_RE = re.compile(
    r"^version (?P<version>\S+)\n"
    r"oid sha256:(?P<sha256>[0-9a-fA-F]{64})\n"
    r"size (?P<size>\d+)\n?$"
)

REQUIRED_FIELDS = (
    "dataset_id",
    "version",
    "status",
    "title",
    "description",
    "storage",
    "file_name",
    "format",
    "sample_rate_hz",
    "source",
    "analysis_targets",
    "quality_checks",
    "license",
)


class ManifestError(RuntimeError):
    """Raised when a manifest is internally inconsistent."""


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping")
    return data


def parse_lfs_pointer(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = LFS_POINTER_RE.match(text)
    if match is None:
        raise ManifestError(f"{path}: expected a Git LFS pointer file")
    pointer = match.groupdict()
    if pointer["version"] != LFS_VERSION:
        raise ManifestError(f"{path}: unexpected Git LFS pointer version {pointer['version']}")
    return pointer


def require_fields(path: Path, data: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        joined = ", ".join(missing)
        raise ManifestError(f"{path}: missing required fields: {joined}")


def validate_manifest(path: Path) -> None:
    data = load_manifest(path)
    require_fields(path, data)

    storage = str(data.get("storage", ""))
    status = str(data.get("status", ""))
    file_name = data.get("file_name")
    sha256 = data.get("sha256")

    if storage == "git-lfs" or status == "git-lfs":
        if not isinstance(file_name, str) or not file_name:
            raise ManifestError(f"{path}: git-lfs manifest requires file_name")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
            raise ManifestError(f"{path}: git-lfs manifest requires a 64-hex sha256")

        data_file = path.parent / file_name
        if not data_file.exists():
            raise ManifestError(f"{path}: referenced data file does not exist: {data_file}")

        pointer = parse_lfs_pointer(data_file)
        if pointer["sha256"].lower() != sha256.lower():
            raise ManifestError(
                f"{path}: manifest sha256 does not match LFS pointer "
                f"({sha256} != {pointer['sha256']})"
            )
        if int(pointer["size"]) <= 0:
            raise ManifestError(f"{path}: LFS pointer size must be positive")

    if status == "manifest-only" and sha256 not in (None, "replace_after_capture"):
        raise ManifestError(f"{path}: manifest-only dataset should not claim a final sha256")


def iter_manifest_paths() -> list[Path]:
    return sorted(DATASETS_DIR.rglob("manifest*.yaml")) + sorted(DATASETS_DIR.rglob("manifest*.yml"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    manifests = iter_manifest_paths()
    if not manifests:
        print("No dataset manifests found.")
        return 0

    errors: list[str] = []
    for manifest in manifests:
        try:
            validate_manifest(manifest)
            print(f"OK  {manifest.relative_to(ROOT)}")
        except ManifestError as exc:
            errors.append(str(exc))
            print(f"ERR {exc}")

    if errors:
        print(f"\nDataset manifest validation failed: {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"\nValidated {len(manifests)} dataset manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
