#!/usr/bin/env python3
"""Validate experiment manifest files.

The checker verifies YAML structure and required fields used by the course
documentation and CI reproducibility flow.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = ROOT / "experiments"
REQUIRED_TOP_LEVEL = {"experiment", "metrics", "reports", "acceptance"}
REQUIRED_EXPERIMENT_FIELDS = {"id", "title", "objective"}

def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_list_of_strings(value: object) -> bool:
    return isinstance(value, list) and all(_is_non_empty_string(item) for item in value)


def validate_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    relative_path = path.relative_to(ROOT)
    manifest_name = path.stem

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{relative_path}: invalid YAML: {exc}"]

    if not isinstance(data, dict):
        return [f"{relative_path}: root YAML node must be a mapping"]

    keys = set(data.keys())
    missing_keys = sorted(REQUIRED_TOP_LEVEL - keys)
    if missing_keys:
        errors.append(f"{relative_path}: missing top-level keys: {', '.join(missing_keys)}")

    experiment = data.get("experiment")
    if not isinstance(experiment, dict):
        errors.append(f"{relative_path}: 'experiment' must be a mapping")
        experiment = {}

    fields = set(experiment.keys())
    missing_fields = sorted(REQUIRED_EXPERIMENT_FIELDS - fields)
    if missing_fields:
        errors.append(f"{relative_path}: missing experiment fields: {', '.join(missing_fields)}")

    experiment_id = experiment.get("id")
    if _is_non_empty_string(experiment_id):
        if str(experiment_id) != manifest_name:
            errors.append(
                f"{relative_path}: experiment.id '{experiment_id}' must match filename stem '{manifest_name}'"
            )
    else:
        errors.append(f"{relative_path}: experiment.id must be a non-empty string")

    for field in ("title", "objective"):
        if not _is_non_empty_string(experiment.get(field)):
            errors.append(f"{relative_path}: experiment.{field} must be a non-empty string")

    for list_field in ("metrics", "acceptance"):
        value = data.get(list_field)
        if not _is_list_of_strings(value):
            errors.append(f"{relative_path}: '{list_field}' must be a non-empty list of strings")
        elif len(value) == 0:
            errors.append(f"{relative_path}: '{list_field}' must not be empty")

    reports = data.get("reports")
    if not isinstance(reports, dict):
        errors.append(f"{relative_path}: 'reports' must be a mapping")
        reports = {}

    template = reports.get("template")
    if not _is_non_empty_string(template):
        errors.append(f"{relative_path}: reports.template must be a non-empty string")
    elif not str(template).startswith(("http://", "https://")):
        target = (ROOT / str(template)).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            errors.append(f"{relative_path}: template escapes repository: {template}")
        else:
            if not target.exists():
                errors.append(f"{relative_path}: missing template: {template}")

    metadata_required = data.get("metadata_required")
    if metadata_required is not None and not _is_list_of_strings(metadata_required):
        errors.append(f"{relative_path}: 'metadata_required' must be a list of strings when present")

    return errors


def main() -> int:
    manifests = sorted(EXPERIMENTS_DIR.glob("*.yaml"))
    if not manifests:
        print("No experiment manifests found.")
        return 1

    errors: list[str] = []
    manifest_ids: dict[str, Path] = {}
    for manifest in manifests:
        errors.extend(validate_manifest(manifest))
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and isinstance(data.get("experiment"), dict):
            manifest_id = data["experiment"].get("id")
            if _is_non_empty_string(manifest_id):
                previous = manifest_ids.get(str(manifest_id))
                if previous is not None and previous != manifest:
                    errors.append(
                        "Duplicate experiment.id "
                        f"'{manifest_id}' in {previous.relative_to(ROOT)} and {manifest.relative_to(ROOT)}"
                    )
                else:
                    manifest_ids[str(manifest_id)] = manifest

    if errors:
        print("Experiment manifest check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Experiment manifest check passed: {len(manifests)} manifests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
