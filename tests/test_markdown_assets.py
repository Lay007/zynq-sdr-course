from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_markdown_assets", ROOT / "tools/check_markdown_assets.py")
assert SPEC is not None and SPEC.loader is not None
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def test_report_wiki_and_community_sources_are_scanned(tmp_path, monkeypatch):
    monkeypatch.setattr(CHECK, "ROOT", tmp_path)
    for name in ("DOCS", "BLOCKS", "TEMPLATES", "EXPERIMENTS", "REPORTS", "WIKI", "COMMUNITY"):
        directory = tmp_path / name.lower()
        directory.mkdir()
        monkeypatch.setattr(CHECK, name, directory, raising=False)
    expected = []
    for directory in ("reports", "wiki", "community"):
        path = tmp_path / directory / "page.md"
        path.write_text("[Missing](missing.md)\n", encoding="utf-8")
        expected.append(path)
    assert set(expected).issubset(CHECK.iter_markdown_files())
    assert all(CHECK.check_file(path) for path in expected)


def test_wiki_extensionless_page_links_are_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(CHECK, "ROOT", tmp_path)
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    monkeypatch.setattr(CHECK, "WIKI", wiki, raising=False)
    (wiki / "FAQ.md").write_text("# FAQ\n", encoding="utf-8")
    home = wiki / "Home.md"
    home.write_text("[FAQ](FAQ#help) [Missing](Missing-Page)\n", encoding="utf-8")
    assert CHECK.check_file(home) == [f"{home.relative_to(tmp_path)}: missing local asset: Missing-Page"]


def test_wiki_links_cannot_escape_the_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(CHECK, "ROOT", tmp_path)
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    monkeypatch.setattr(CHECK, "WIKI", wiki, raising=False)
    home = wiki / "Home.md"
    home.write_text("[Escape](../../outside)\n", encoding="utf-8")
    assert CHECK.check_file(home) == [f"{home.relative_to(tmp_path)}: link escapes repository: ../../outside"]


def test_external_and_mkdocs_directory_links_still_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(CHECK, "ROOT", tmp_path)
    monkeypatch.setattr(CHECK, "WIKI", tmp_path / "wiki", raising=False)
    page = tmp_path / "page.md"
    page.write_text("[Site](https://example.com/FAQ) [Page](model-to-measurement/) [Section](#intro)\n", encoding="utf-8")
    assert CHECK.check_file(page) == []
