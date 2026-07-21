from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "tools" / "tasks.py"


def load_tasks():
    spec = importlib.util.spec_from_file_location("course_tasks", TASKS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_readme_is_detected_as_tracked() -> None:
    tasks = load_tasks()

    assert tasks.is_git_tracked(ROOT / "README.md") is True


def test_remove_generated_file_preserves_tracked_file(tmp_path: Path, monkeypatch) -> None:
    tasks = load_tasks()
    artifact = tmp_path / "evidence.json"
    artifact.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(tasks, "is_git_tracked", lambda path: True)

    removed = tasks.remove_generated_file(artifact)

    assert removed is False
    assert artifact.is_file()


def test_remove_generated_file_deletes_untracked_file(tmp_path: Path, monkeypatch) -> None:
    tasks = load_tasks()
    artifact = tmp_path / "generated.json"
    artifact.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(tasks, "is_git_tracked", lambda path: False)

    removed = tasks.remove_generated_file(artifact)

    assert removed is True
    assert not artifact.exists()
