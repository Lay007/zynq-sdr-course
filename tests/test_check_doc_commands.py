from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_doc_commands", ROOT / "tools" / "check_doc_commands.py")
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


def _write_doc(tmp_path: Path, body: str) -> Path:
    doc = tmp_path / "page.md"
    doc.write_text(body, encoding="utf-8")
    return doc


def _script(tmp_path: Path) -> Path:
    script = tmp_path / "demo.py"
    script.write_text(
        "import argparse\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--manifest')\n"
        "p.add_argument('--reboot-after', action=argparse.BooleanOptionalAction, default=True)\n"
        "p.parse_args()\n",
        encoding="utf-8",
    )
    return script


def _messages(tmp_path: Path, body: str, monkeypatch) -> list[str]:
    monkeypatch.setattr(CHECK, "ROOT", tmp_path)
    CHECK._FLAG_CACHE.clear()
    return [p.message for p in CHECK.check_file(_write_doc(tmp_path, body), check_paths=False)]


def test_known_flags_prefixes_and_negated_booleans_pass(tmp_path: Path, monkeypatch) -> None:
    _script(tmp_path)
    body = "```bash\npython demo.py \\n  --manifest x.yaml --no-reboot-after --mani y\n```\n"
    assert _messages(tmp_path, body, monkeypatch) == []


def test_unknown_flag_and_missing_script_are_reported(tmp_path: Path, monkeypatch) -> None:
    _script(tmp_path)
    body = "```bash\npython demo.py --wav-path a.wav\npython missing.py --x\n```\n"
    messages = _messages(tmp_path, body, monkeypatch)
    assert "demo.py: unknown option --wav-path" in messages
    assert "script not found: missing.py" in messages


def test_quoted_operators_and_cd_are_handled(tmp_path: Path, monkeypatch) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    _script(sub)
    body = (
        "```bash\n"
        "cd sub\n"
        "python demo.py --manifest \"plug --off && sleep 3\"\n"
        "```\n"
    )
    assert _messages(tmp_path, body, monkeypatch) == []


def test_repository_docs_pass() -> None:
    CHECK._FLAG_CACHE.clear()
    problems = []
    for doc in CHECK.markdown_files():
        problems.extend(CHECK.check_file(doc, check_paths=False))
    assert [p for p in problems if not p.message.startswith("warning:")] == []
