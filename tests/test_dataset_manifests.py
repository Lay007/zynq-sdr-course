from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_dataset_manifests import (  # noqa: E402
    ManifestError,
    iter_manifest_paths,
    manifest_kind,
    validate_manifest,
)


def write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_all_committed_dataset_manifests_validate() -> None:
    manifests = iter_manifest_paths()

    assert manifests
    for manifest in manifests:
        validate_manifest(manifest)


def test_capture_session_requires_a_local_or_repository_file_reference(tmp_path: Path) -> None:
    path = tmp_path / "manifest.yaml"
    payload = {
        "manifest_kind": "capture-session",
        "dataset_id": "local-capture",
        "title": "Local capture",
        "description": "Temporary local capture",
        "storage": "local-workstation",
        "format": "wav",
        "sample_rate_hz": 2_400_000,
        "center_frequency_hz": 915_000_000,
        "analysis_command": "python analyze.py",
        "signal": {"modulation": "BPSK"},
        "notes": ["local only"],
    }
    write_yaml(path, payload)

    with pytest.raises(ManifestError, match="local_path_hint_windows or file_name"):
        validate_manifest(path)


def test_template_kind_is_inferred_from_filename() -> None:
    path = Path("capture.template.yaml")

    assert manifest_kind(path, {"status": "template"}) == "template"
