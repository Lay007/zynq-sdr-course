#!/usr/bin/env python3
"""Publish the curated Markdown pages to the separate GitHub Wiki repository."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPOSITORY = "Lay007/zynq-sdr-course"
WIKI_URL = f"https://github.com/{REPOSITORY}.wiki.git"
PAGE_NAMES = (
    "Home.md",
    "Getting-Started.md",
    "Hardware.md",
    "DSP-to-FPGA.md",
    "Troubleshooting.md",
    "_Sidebar.md",
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "wiki"
    missing = [name for name in PAGE_NAMES if not (source / name).is_file()]
    if missing:
        print(f"Missing Wiki source pages: {', '.join(missing)}", file=sys.stderr)
        return 1

    if not shutil.which("git"):
        print("Git is required to publish the Wiki.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="zynq-sdr-wiki-") as temp:
        destination = Path(temp) / "wiki"
        try:
            run("git", "clone", WIKI_URL, str(destination))
        except subprocess.CalledProcessError:
            print(
                "Cannot clone the Wiki. Create its initial Home page in the "
                f"GitHub interface first: https://github.com/{REPOSITORY}/wiki "
                "and check Git authentication.",
                file=sys.stderr,
            )
            return 1

        for name in PAGE_NAMES:
            shutil.copyfile(source / name, destination / name)

        run("git", "-C", str(destination), "add", "--", *PAGE_NAMES)
        changed = subprocess.run(
            ["git", "-C", str(destination), "diff", "--cached", "--quiet"],
            check=False,
        )
        if changed.returncode == 0:
            print("GitHub Wiki is already up to date.")
            return 0
        if changed.returncode != 1:
            print("Could not inspect staged Wiki changes.", file=sys.stderr)
            return 1

        try:
            run(
                "git", "-C", str(destination), "commit",
                "-m", "Publish engineering Wiki reference pages",
            )
            run("git", "-C", str(destination), "push", "origin", "HEAD")
        except subprocess.CalledProcessError:
            print(
                "Wiki publication failed. Check your Git credentials and "
                "write access, then rerun; no force push was attempted.",
                file=sys.stderr,
            )
            return 1

    print(f"Published {len(PAGE_NAMES)} pages to https://github.com/{REPOSITORY}/wiki")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
