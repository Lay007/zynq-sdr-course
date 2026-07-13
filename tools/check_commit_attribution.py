#!/usr/bin/env python3
"""Reject new commit messages that attribute authorship to Claude.

The repository intentionally keeps AI tools out of Git author attribution. This
checker scans only the commit range supplied by CI, so historical commits do not
make every future build fail.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

FORBIDDEN_TRAILER_RE = re.compile(
    r"^co-authored-by:\s*claude\b.*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class AttributionViolation:
    commit: str
    trailer: str


def find_forbidden_trailers(message: str) -> tuple[str, ...]:
    """Return Claude co-author trailers found in one commit message."""

    return tuple(match.group(0).strip() for match in FORBIDDEN_TRAILER_RE.finditer(message))


def commit_messages(revision_range: str) -> list[tuple[str, str]]:
    """Read commit SHAs and full messages for a git revision range."""

    result = subprocess.run(
        ["git", "rev-list", "--reverse", revision_range],
        check=True,
        capture_output=True,
        text=True,
    )
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    messages: list[tuple[str, str]] = []
    for commit in commits:
        message = subprocess.run(
            ["git", "show", "-s", "--format=%B", commit],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        messages.append((commit, message))
    return messages


def check_revision_range(revision_range: str) -> tuple[AttributionViolation, ...]:
    violations: list[AttributionViolation] = []
    for commit, message in commit_messages(revision_range):
        for trailer in find_forbidden_trailers(message):
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
    except subprocess.CalledProcessError as exc:
        print(f"Unable to inspect commit range {args.revision_range!r}: {exc}", file=sys.stderr)
        return 2

    if not violations:
        print(f"Commit attribution check passed for {args.revision_range}.")
        return 0

    print("Commit attribution check failed: Claude must not be listed as a co-author.")
    for violation in violations:
        print(f"  - {violation.commit[:12]}: {violation.trailer}")
    print("Remove the Co-Authored-By trailer and recreate the affected commit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
