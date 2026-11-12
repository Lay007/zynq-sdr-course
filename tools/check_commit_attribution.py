#!/usr/bin/env python3
"""Reject new commit messages that attribute authorship to an AI tool.

The repository intentionally keeps AI tools out of Git author attribution: no
Co-authored-by trailer naming a model or its vendor (Claude, ChatGPT, Codex,
OpenAI, Copilot, Gemini, Anthropic), and no "Generated with ..." signature of a
generator. This checker scans only the commit range supplied by CI, so historical
commits do not make every future build fail.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

AI_NAMES = "claude|chatgpt|codex|openai|copilot|gemini|anthropic"
FORBIDDEN_IDENTITY_RE = re.compile(rf"\b(?:{AI_NAMES})\b", flags=re.IGNORECASE)
FORBIDDEN_TRAILER_RE = re.compile(
    rf"^(?:co-authored-by:[^\n]*\b(?:{AI_NAMES})\b[^\n]*"
    rf"|[^\w\n]*generated (?:with|by) [^\n]*\b(?:{AI_NAMES}|ai)\b[^\n]*)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class AttributionViolation:
    commit: str
    trailer: str


def find_forbidden_trailers(message: str) -> tuple[str, ...]:
    """Return AI co-author trailers and generator signatures found in one commit message."""

    return tuple(match.group(0).strip() for match in FORBIDDEN_TRAILER_RE.finditer(message))


def find_forbidden_identities(author_name: str, author_email: str,
                              committer_name: str, committer_email: str) -> tuple[str, ...]:
    """Flag AI attribution in author/committer identities, not normal prose."""

    fields = (
        ("author name", author_name),
        ("author email", author_email),
        ("committer name", committer_name),
        ("committer email", committer_email),
    )
    return tuple(f"{label}: {value}" for label, value in fields
                 if FORBIDDEN_IDENTITY_RE.search(value))


def commit_messages(revision_range: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Read commit SHAs, full messages and identity violations in a revision range."""

    # Explicit UTF-8: with the locale codec (cp1251 on a Russian Windows) a commit message
    # with a byte it cannot decode made the reader thread fail, and stdout came back None.
    result = subprocess.run(
        ["git", "rev-list", "--reverse", revision_range],
        check=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    messages: list[tuple[str, str, tuple[str, ...]]] = []
    for commit in commits:
        payload = subprocess.run(
            ["git", "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%B", commit],
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        ).stdout
        fields = payload.split("\x00", 4)
        if len(fields) != 5:
            raise ValueError(f"Unable to parse attribution for {commit}")
        author_name, author_email, committer_name, committer_email, message = fields
        messages.append((commit, message, find_forbidden_identities(
            author_name, author_email, committer_name, committer_email)))
    return messages


def check_revision_range(revision_range: str) -> tuple[AttributionViolation, ...]:
    violations: list[AttributionViolation] = []
    for commit, message, identities in commit_messages(revision_range):
        for trailer in (*find_forbidden_trailers(message), *identities):
            violations.append(AttributionViolation(commit=commit, trailer=trailer))
    return tuple(violations)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--range",
        dest="revision_range",
        default="HEAD^!",
        help="Git revision range to inspect (default: HEAD^!)",
    )
    args = parser.parse_args()

    try:
        violations = check_revision_range(args.revision_range)
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"Unable to inspect commit range {args.revision_range!r}: {exc}", file=sys.stderr)
        return 2

    if not violations:
        print(f"Commit attribution check passed for {args.revision_range}.")
        return 0

    print("Commit attribution check failed: an AI tool must not be listed as a co-author or signature.")
    for violation in violations:
        print(f"  - {violation.commit[:12]}: {violation.trailer}")
    print("Remove the trailer or signature and recreate the affected commit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
