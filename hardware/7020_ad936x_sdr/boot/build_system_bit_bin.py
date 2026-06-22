#!/usr/bin/env python3
"""Convert a raw Vivado `.bit` into a boot-time `system.bit.bin` payload."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path


WINDOWS_BOOTGEN_GLOBS = [
    Path(f"{drive}:/Xilinx/Vivado").glob("*/bin/bootgen.bat")
    for drive in ("C", "D", "E", "F", "G")
]


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_bootgen(explicit: Path | None) -> Path:
    if explicit:
        if not explicit.exists():
            raise FileNotFoundError(f"Bootgen not found: {explicit}")
        return explicit

    for candidate in ("bootgen", "bootgen.bat"):
        resolved = shutil.which(candidate)
        if resolved:
            return Path(resolved)

    discovered: list[Path] = []
    for pattern in WINDOWS_BOOTGEN_GLOBS:
        discovered.extend(sorted(pattern))
    if discovered:
        return discovered[-1]

    raise FileNotFoundError(
        "Could not locate Bootgen. Pass --bootgen or add bootgen to PATH."
    )


def default_output_path(bit_path: Path) -> Path:
    return Path(f"{bit_path}.bin")


def write_bif(bit_path: Path, bif_path: Path) -> None:
    bif_path.write_text(
        "all:\n{\n  \"" + bit_path.resolve().as_posix() + "\"\n}\n",
        encoding="ascii",
    )


def build_system_bit_bin(
    bit_path: Path,
    *,
    output_path: Path | None = None,
    bootgen_path: Path | None = None,
) -> Path:
    bit_path = bit_path.resolve()
    if not bit_path.exists():
        raise FileNotFoundError(f"Missing input bit file: {bit_path}")
    if bit_path.suffix.lower() != ".bit":
        raise ValueError(f"Expected a .bit input, got: {bit_path.name}")

    output_path = (output_path or default_output_path(bit_path)).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bootgen = find_bootgen(bootgen_path)
    bif_path = output_path.with_suffix(output_path.suffix + ".bif")
    write_bif(bit_path, bif_path)

    try:
        subprocess.run(
            [
                str(bootgen),
                "-arch",
                "zynq",
                "-image",
                str(bif_path),
                "-o",
                str(output_path),
                "-w",
                "on",
            ],
            check=True,
        )
    finally:
        bif_path.unlink(missing_ok=True)

    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bit_path", type=Path, help="Input raw .bit file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output .bit.bin path; defaults to <bit_path>.bin",
    )
    parser.add_argument(
        "--bootgen",
        type=Path,
        help="Optional explicit Bootgen executable path",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    bit_path = args.bit_path.resolve()
    output_path = build_system_bit_bin(
        bit_path,
        output_path=args.output,
        bootgen_path=args.bootgen,
    )

    print(f"Input : {bit_path}")
    print(f"Output: {output_path}")
    print(f"Size  : {output_path.stat().st_size} bytes")
    print(f"MD5   : {md5_file(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
