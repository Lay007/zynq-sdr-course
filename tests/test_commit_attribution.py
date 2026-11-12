from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_commit_attribution import (  # noqa: E402
    find_forbidden_identities,
    find_forbidden_trailers,
)


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


def test_rejects_other_ai_coauthors_and_generator_signatures() -> None:
    for line in (
        "Co-authored-by: ChatGPT <noreply@openai.com>",
        "Co-authored-by: Codex <codex@openai.com>",
        "Co-authored-by: Copilot <copilot@github.com>",
        "\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)",
        "Generated with AI",
    ):
        assert find_forbidden_trailers(f"Update course\n\n{line}\n") == (line,), line


def test_accepts_human_and_bot_coauthors_and_ordinary_generated_files() -> None:
    message = (
        "Bump numpy\n\n"
        "Generated with tools/generate_ofdm_sin_rom.py.\n"
        "Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>\n"
        "Co-authored-by: Alexander <laymob@gmail.com>\n"
    )

    assert find_forbidden_trailers(message) == ()


def test_reports_multiple_forbidden_trailers() -> None:
    message = (
        "Update course\n\n"
        "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>\n"
        "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>\n"
    )

    assert len(find_forbidden_trailers(message)) == 2

def test_rejects_ai_author_and_committer_identifiers() -> None:
    findings = find_forbidden_identities(
        "Human", "human@example.org",
        "OpenAI Codex", "noreply@openai.com",
    )
    assert "committer name: OpenAI Codex" in findings
    assert "committer email: noreply@openai.com" in findings


def test_accepts_legitimate_github_and_dependabot_identities() -> None:
    assert find_forbidden_identities(
        "Alexander", "35570696+Lay007@users.noreply.github.com",
        "GitHub", "noreply@github.com",
    ) == ()
    assert find_forbidden_identities(
        "dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com",
        "GitHub", "noreply@github.com",
    ) == ()
