#!/usr/bin/env python3
"""Validate dataset manifests and Git LFS pointers used by the course."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT / "datasets"
LFS_VERSION = "https://git-lfs.github.com/spec/v1"
LFS_POINTER_RE = re.compile(
    rb"^version (?P<version>\S+)\n"
    rb"oid sha256:(?P<sha256>[0-9a-fA-F]{64})\n"
    rb"size (?P<size>\d+)\n?$"
)
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")

DATASET_REQUIRED_FIELDS = (
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

CAPTURE_SESSION_REQUIRED_FIELDS = (
    "dataset_id",
    "title",
    "description",
    "storage",
    "format",
    "sample_rate_hz",
    "center_frequency_hz",
    "analysis_command",
    "signal",
    "notes",
)

TEMPLATE_REQUIRED_FIELDS = (
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

CAPTURE_SESSION_STORAGE = {"local-workstation", "repo-generated"}
MANIFEST_KINDS = {"dataset", "capture-session", "template"}


class ManifestError(RuntimeError):
    """Raised when a manifest is internally inconsistent."""


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: manifest must be a YAML mapping")
    return data


def read_lfs_pointer_or_digest(path: Path) -> tuple[str, int, str]:
    """Return (sha256, size, source) for a Git LFS pointer or real binary file."""

    payload = path.read_bytes()
    match = LFS_POINTER_RE.match(payload)
    if match is not None:
        pointer = match.groupdict()
        version = pointer["version"].decode("ascii")
        if version != LFS_VERSION:
            raise ManifestError(f"{path}: unexpected Git LFS pointer version {version}")
        return (
            pointer["sha256"].decode("ascii"),
            int(pointer["size"].decode("ascii")),
            "git-lfs-pointer",
        )

    return hashlib.sha256(payload).hexdigest(), len(payload), "file-content"


def require_fields(path: Path, data: dict[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        joined = ", ".join(missing)
        raise ManifestError(f"{path}: missing required fields: {joined}")


def manifest_kind(path: Path, data: dict[str, Any]) -> str:
    explicit = data.get("manifest_kind")
    if explicit is not None:
        kind = str(explicit)
        if kind not in MANIFEST_KINDS:
            expected = ", ".join(sorted(MANIFEST_KINDS))
            raise ManifestError(f"{path}: manifest_kind must be one of: {expected}")
        return kind
    if ".template." in path.name or str(data.get("status", "")) == "template":
        return "template"
    if str(data.get("storage", "")) in CAPTURE_SESSION_STORAGE:
        return "capture-session"
    if str(data.get("status", "")) in {"local-only", "review-before-lfs"}:
        return "capture-session"
    return "dataset"


def require_positive_number(path: Path, value: Any, context: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ManifestError(f"{path}: {context} must be a positive number")


def validate_template_manifest(path: Path, data: dict[str, Any]) -> None:
    require_fields(path, data, TEMPLATE_REQUIRED_FIELDS)
    if str(data.get("status")) != "template":
        raise ManifestError(f"{path}: template manifest must use status: template")


def validate_capture_session_manifest(path: Path, data: dict[str, Any]) -> None:
    require_fields(path, data, CAPTURE_SESSION_REQUIRED_FIELDS)
    if str(data.get("storage")) not in CAPTURE_SESSION_STORAGE:
        expected = ", ".join(sorted(CAPTURE_SESSION_STORAGE))
        raise ManifestError(f"{path}: capture-session storage must be one of: {expected}")
    if not data.get("local_path_hint_windows") and not data.get("file_name"):
        raise ManifestError(f"{path}: capture-session requires local_path_hint_windows or file_name")
    if not isinstance(data.get("analysis_command"), str) or not data["analysis_command"].strip():
        raise ManifestError(f"{path}: capture-session requires a non-empty analysis_command")
    if not isinstance(data.get("signal"), dict) or not data["signal"]:
        raise ManifestError(f"{path}: capture-session signal must be a non-empty mapping")
    require_positive_number(path, data.get("sample_rate_hz"), "sample_rate_hz")


def require_sha256(path: Path, sha256: Any, context: str) -> str:
    if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
        raise ManifestError(f"{path}: {context} requires a 64-hex sha256")
    return sha256


def validate_git_lfs_manifest(path: Path, data: dict[str, Any]) -> None:
    file_name = data.get("file_name")
    sha256 = require_sha256(path, data.get("sha256"), "git-lfs manifest")
    if not isinstance(file_name, str) or not file_name:
        raise ManifestError(f"{path}: git-lfs manifest requires file_name")

    data_file = path.parent / file_name
    if not data_file.exists():
        raise ManifestError(f"{path}: referenced data file does not exist: {data_file}")

    actual_sha256, size, source = read_lfs_pointer_or_digest(data_file)
    if actual_sha256.lower() != sha256.lower():
        raise ManifestError(
            f"{path}: manifest sha256 does not match {source} "
            f"({sha256} != {actual_sha256})"
        )
    if size <= 0:
        raise ManifestError(f"{path}: referenced data size must be positive")


def validate_generated_local_manifest(path: Path, data: dict[str, Any]) -> None:
    sha256 = require_sha256(path, data.get("sha256"), "generated-local manifest")
    generator = data.get("generator")
    if not isinstance(generator, str) or not generator:
        raise ManifestError(f"{path}: generated-local manifest requires generator")

    generator_path = ROOT / generator
    if not generator_path.exists():
        raise ManifestError(f"{path}: generator does not exist: {generator}")

    metrics_path = path.parent / "metrics.json"
    if metrics_path.exists():
        with metrics_path.open("r", encoding="utf-8") as handle:
            metrics = json.load(handle)
        if metrics.get("sha256", "").lower() != sha256.lower():
            raise ManifestError(f"{path}: metrics.json sha256 does not match manifest sha256")

    data_file = path.parent / str(data.get("file_name", ""))
    if data_file.exists():
        digest = hashlib.sha256(data_file.read_bytes()).hexdigest()
        if digest.lower() != sha256.lower():
            raise ManifestError(f"{path}: generated local file sha256 does not match manifest")


def validate_manifest(path: Path) -> None:
    data = load_manifest(path)
    kind = manifest_kind(path, data)
    if kind == "template":
        validate_template_manifest(path, data)
        return
    if kind == "capture-session":
        validate_capture_session_manifest(path, data)
        return

    require_fields(path, data, DATASET_REQUIRED_FIELDS)
    require_positive_number(path, data.get("sample_rate_hz"), "sample_rate_hz")

    storage = str(data.get("storage", ""))
    status = str(data.get("status", ""))
    sha256 = data.get("sha256")

    if storage == "git-lfs" or status == "git-lfs":
        validate_git_lfs_manifest(path, data)
    elif storage == "generated-local" or status == "generated-local":
        validate_generated_local_manifest(path, data)

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
        except (ManifestError, OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
            errors.append(str(exc))
            print(f"ERR {manifest.relative_to(ROOT)}: {exc}")

    if errors:
        print(f"\nDataset manifest validation failed: {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(f"\nValidated {len(manifests)} dataset manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
