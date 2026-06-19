#!/usr/bin/env python3
"""Inspect memory-mapped register windows exported by Vivado XSA/HWH files."""

from __future__ import annotations

import argparse
import io
import json
import tarfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class MemRange:
    instance: str
    base_addr: int
    high_addr: int
    address_block: str
    memtype: str
    master_bus_interface: str
    slave_bus_interface: str
    basename: str
    highname: str


def _parse_int(value: str) -> int:
    return int(value, 0)


def _decode_xml_bytes(payload: bytes) -> str:
    return payload.decode("utf-8", errors="ignore")


def _read_hwh_from_zip(archive: zipfile.ZipFile) -> bytes | None:
    for name in archive.namelist():
        if name.lower().endswith(".hwh"):
            return archive.read(name)

    for name in archive.namelist():
        if not name.lower().endswith((".xsa", ".zip")):
            continue
        nested_payload = archive.read(name)
        nested_stream = io.BytesIO(nested_payload)
        if not zipfile.is_zipfile(nested_stream):
            continue
        nested_stream.seek(0)
        with zipfile.ZipFile(nested_stream) as nested_archive:
            nested_hwh = _read_hwh_from_zip(nested_archive)
            if nested_hwh is not None:
                return nested_hwh
    return None


def _load_hwh_payload(export_path: Path) -> bytes:
    if export_path.suffix.lower() == ".hwh":
        return export_path.read_bytes()

    if zipfile.is_zipfile(export_path):
        with zipfile.ZipFile(export_path) as archive:
            nested_hwh = _read_hwh_from_zip(archive)
            if nested_hwh is not None:
                return nested_hwh

    if tarfile.is_tarfile(export_path):
        with tarfile.open(export_path) as archive:
            for member in archive.getmembers():
                if member.name.lower().endswith(".hwh"):
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        return extracted.read()
                if not member.name.lower().endswith((".xsa", ".zip")):
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                nested_payload = extracted.read()
                nested_stream = io.BytesIO(nested_payload)
                if not zipfile.is_zipfile(nested_stream):
                    continue
                nested_stream.seek(0)
                with zipfile.ZipFile(nested_stream) as nested_archive:
                    nested_hwh = _read_hwh_from_zip(nested_archive)
                    if nested_hwh is not None:
                        return nested_hwh

    raise FileNotFoundError(f"Could not find an .hwh payload inside {export_path}")


def parse_memranges_text(text: str) -> list[MemRange]:
    root = ElementTree.fromstring(text)
    ranges: list[MemRange] = []
    for node in root.iter():
        if not str(node.tag).endswith("MEMRANGE"):
            continue
        attrs = node.attrib
        if "BASEVALUE" not in attrs or "HIGHVALUE" not in attrs or "INSTANCE" not in attrs:
            continue
        ranges.append(
            MemRange(
                instance=attrs["INSTANCE"],
                base_addr=_parse_int(attrs["BASEVALUE"]),
                high_addr=_parse_int(attrs["HIGHVALUE"]),
                address_block=attrs.get("ADDRESSBLOCK", ""),
                memtype=attrs.get("MEMTYPE", ""),
                master_bus_interface=attrs.get("MASTERBUSINTERFACE", ""),
                slave_bus_interface=attrs.get("SLAVEBUSINTERFACE", ""),
                basename=attrs.get("BASENAME", ""),
                highname=attrs.get("HIGHNAME", ""),
            )
        )
    return sorted(ranges, key=lambda item: (item.base_addr, item.instance))


def read_memranges(export_path: Path) -> list[MemRange]:
    return parse_memranges_text(_decode_xml_bytes(_load_hwh_payload(export_path)))


def filter_memranges(memranges: list[MemRange], filters: list[str]) -> list[MemRange]:
    if not filters:
        return memranges
    lowered = [item.lower() for item in filters]
    return [entry for entry in memranges if all(token in entry.instance.lower() for token in lowered)]


def format_table(memranges: list[MemRange]) -> str:
    headers = ("Base", "High", "Instance", "MemType", "Master", "Slave")
    rows = [
        (
            f"0x{entry.base_addr:08X}",
            f"0x{entry.high_addr:08X}",
            entry.instance,
            entry.memtype or "-",
            entry.master_bus_interface or "-",
            entry.slave_bus_interface or "-",
        )
        for entry in memranges
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    lines = [
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "  ".join("-" * widths[index] for index in range(len(headers))),
    ]
    lines.extend("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)) for row in rows)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect Vivado XSA/HWH memory map exports.")
    parser.add_argument("export_path", type=Path, help="Path to a .xsa or .hwh export file.")
    parser.add_argument(
        "--find",
        action="append",
        default=[],
        help="Case-insensitive substring filter applied to INSTANCE names. Can be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON array instead of a text table.")
    parser.add_argument(
        "--require-match",
        action="store_true",
        help="Return exit code 1 when --find filters produce no rows.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    memranges = read_memranges(args.export_path)
    filtered = filter_memranges(memranges, args.find)

    if args.json:
        print(json.dumps([asdict(entry) for entry in filtered], indent=2))
    else:
        if filtered:
            print(format_table(filtered))
        else:
            print("No matching MEMRANGE entries found.")

    if args.require_match and not filtered:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
