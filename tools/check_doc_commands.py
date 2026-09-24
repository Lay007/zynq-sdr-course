#!/usr/bin/env python3
"""Check that `python <script>.py --flag ...` commands in the docs still work.

For every fenced code block in `docs/**/*.md`, `blocks/**/*.md`, `templates/**/*.md`
and root-level `*.md` files, the checker joins shell line continuations (`\\` for
bash, a trailing backtick for PowerShell), finds `python <path>.py ...` invocations
and reports:

- a script path that does not exist in the repository;
- a `--flag` that the script's argparse parser does not define.

Flags are read statically from `add_argument(...)` calls with the AST, so scripts
that import hardware libraries (libiio, pyadi) are never executed. argparse accepts
unambiguous prefixes of long options, and so does this checker. Scripts that do not
use argparse are skipped.

Missing data paths are reported as warnings only with `--paths`: many commands
name large captures that are intentionally kept out of git.
"""

from __future__ import annotations

import argparse
import ast
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("docs", "blocks", "templates")
FENCE_RE = re.compile(r"^(```|~~~)[^\n]*\n(.*?)^\1", re.DOTALL | re.MULTILINE)
PY_LAUNCHERS = {"python", "python3", "py"}
PATH_PREFIXES = ("blocks/", "datasets/", "docs/", "tools/", "hardware/", "verification/", "templates/")
OUTPUT_FLAG_HINTS = ("out", "output", "save", "write", "report", "log")


@dataclass(frozen=True)
class Problem:
    doc: Path
    line: int
    message: str


def markdown_files() -> list[Path]:
    files = [p for p in ROOT.glob("*.md")]
    for name in SCAN_DIRS:
        files.extend((ROOT / name).rglob("*.md"))
    return sorted(p for p in files if "site" not in p.relative_to(ROOT).parts[:1])


def logical_lines(block: str) -> list[tuple[int, str]]:
    """Join `\\` and PowerShell backtick continuations; keep the first line number."""
    out: list[tuple[int, str]] = []
    buf = ""
    start = 0
    for offset, raw in enumerate(block.splitlines()):
        line = raw.rstrip()
        if not buf:
            start = offset
        if line.endswith("\\") or line.endswith("`"):
            buf += line[:-1] + " "
            continue
        buf += line
        out.append((start, buf.strip()))
        buf = ""
    if buf:
        out.append((start, buf.strip()))
    return out


def split_command(line: str) -> list[str]:
    line = line.split(" #", 1)[0]
    try:
        return shlex.split(line, posix=True)
    except ValueError:
        return line.split()


SHELL_OPERATORS = {"&&", "||", ";", "|"}


def split_pipeline(line: str) -> list[list[str]]:
    """Tokenize with shell quoting first, then split on unquoted operators."""
    commands: list[list[str]] = [[]]
    for token in split_command(line):
        if token in SHELL_OPERATORS:
            commands.append([])
        else:
            commands[-1].append(token)
    return [c for c in commands if c]


_FLAG_CACHE: dict[Path, set[str] | None] = {}


def script_flags(script: Path) -> set[str] | None:
    """Long options defined via add_argument, or None when argparse is not used."""
    if script in _FLAG_CACHE:
        return _FLAG_CACHE[script]
    try:
        tree = ast.parse(script.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        _FLAG_CACHE[script] = None
        return None
    flags: set[str] = set()
    uses_argparse = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_argument":
                uses_argparse = True
                optional_bool = any(
                    kw.arg == "action" and isinstance(kw.value, ast.Attribute) and kw.value.attr == "BooleanOptionalAction"
                    for kw in node.keywords
                )
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("--"):
                        flags.add(arg.value)
                        if optional_bool:
                            flags.add("--no-" + arg.value[2:])
            elif node.func.attr in {"parse_args", "parse_known_args"}:
                uses_argparse = True
    result = flags if uses_argparse else None
    _FLAG_CACHE[script] = result
    return result


def flag_known(flag: str, known: set[str]) -> bool:
    if flag in known or flag in {"--help", "-h"}:
        return True
    matches = [k for k in known if k.startswith(flag)]
    return len(matches) == 1


def check_invocation(doc: Path, line_no: int, tokens: list[str], check_paths: bool, cwd: Path = ROOT) -> list[Problem]:
    problems: list[Problem] = []
    try:
        idx = next(i for i, tok in enumerate(tokens) if Path(tok).name in PY_LAUNCHERS or tok in PY_LAUNCHERS)
    except StopIteration:
        return problems
    rest = tokens[idx + 1 :]
    if not rest or rest[0].startswith("-") or not rest[0].endswith(".py"):
        return problems  # python -m ..., python -c ..., interactive
    script_arg = rest[0].replace("\\", "/")
    if any(mark in script_arg for mark in ("<", "$", "{", "...", "path/to/")):
        return problems  # placeholder
    script = (cwd / script_arg).resolve()
    if not script.is_file():
        problems.append(Problem(doc, line_no, f"script not found: {script_arg}"))
        return problems
    known = script_flags(script)
    args = rest[1:]
    for i, tok in enumerate(args):
        if not tok.startswith("--") or tok == "--":
            continue
        flag = tok.split("=", 1)[0]
        if known is not None and not flag_known(flag, known):
            problems.append(Problem(doc, line_no, f"{script_arg}: unknown option {flag}"))
        if check_paths and i + 1 < len(args):
            value = args[i + 1].replace("\\", "/")
            is_output = any(h in flag.lower() for h in OUTPUT_FLAG_HINTS)
            if (
                not is_output
                and value.startswith(PATH_PREFIXES)
                and not any(c in value for c in "*<>${}")
                and not (ROOT / value).exists()
            ):
                problems.append(Problem(doc, line_no, f"warning: {script_arg} {flag}: path not in repo: {value}"))
    return problems


def check_file(doc: Path, check_paths: bool) -> list[Problem]:
    text = doc.read_text(encoding="utf-8", errors="replace")
    problems: list[Problem] = []
    for match in FENCE_RE.finditer(text):
        block_start_line = text.count("\n", 0, match.start(2)) + 1
        cwd = ROOT  # every code block is assumed to start in the repository root
        for offset, line in logical_lines(match.group(2)):
            for tokens in split_pipeline(line):
                part = " ".join(tokens)
                if len(tokens) == 2 and tokens[0] in {"cd", "Set-Location", "pushd"}:
                    target = (cwd / tokens[1].replace("\\", "/")).resolve()
                    if target.is_dir():
                        cwd = target
                    continue
                if "python" in part:
                    problems.extend(check_invocation(doc, block_start_line + offset, tokens, check_paths, cwd))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paths", action="store_true", help="also warn about data paths missing from the repo")
    args = parser.parse_args()

    problems: list[Problem] = []
    for doc in markdown_files():
        problems.extend(check_file(doc, args.paths))
    errors = [p for p in problems if not p.message.startswith("warning:")]
    for p in problems:
        print(f"{p.doc.relative_to(ROOT).as_posix()}:{p.line}: {p.message}")
    if errors:
        print(f"Documented command check failed: {len(errors)} problem(s).")
        return 1
    print("Documented command check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
