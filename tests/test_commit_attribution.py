from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_commit_attribution import find_forbidden_trailers  # noqa: E402


def test_accepts_regular_commit_message() -> None:
    message = "Fix QPSK timing recovery\n\nValidated with the HDL smoke test.\n"

    assert find_forbidden_trailers(message) == ()


def test_rejects_claude_coauthor_trailer_case_insensitively() -> None:
    message = (
        "Add hardware report\n\n"
        "co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>\n"
    )

    assert find_forbidden_trailers(message) == (
        "co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>",
    )


def test_does_not_reject_normal_body_reference_to_claude() -> None:
    message = (
        "Document AI-assisted workflow\n\n"
        "The comparison mentions Claude Code, Codex and local review tools.\n"
    )

    assert find_forbidden_trailers(message) == ()


def test_reports_multiple_forbidden_trailers() -> None:
    message = (
        "Update course\n\n"
        "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>\n"
        "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>\n"
    )

    assert len(find_forbidden_trailers(message)) == 2
