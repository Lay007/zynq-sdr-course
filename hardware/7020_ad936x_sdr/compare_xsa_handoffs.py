#!/usr/bin/env python3
"""Compare two XSA hardware handoffs and summarize structural differences.

The main use case is narrowing down why a rebuilt AD9361 shell diverges from a
known vendor/source handoff even when PS7 init files remain identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


IGNORED_PARAMETER_NAMES = {
    "Component_Name",
    "EDK_IPTYPE",
}


def md5_bytes(payload: bytes) -> str:
    return hashlib.md5(payload).hexdigest()


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def zip_entry_info(zf: zipfile.ZipFile) -> dict[str, dict[str, Any]]:
    info: dict[str, dict[str, Any]] = {}
    for name in sorted(zf.namelist()):
        payload = zf.read(name)
        info[name] = {
            "size_bytes": len(payload),
            "md5": md5_bytes(payload),
        }
    return info


def parse_module_parameters(module: ET.Element) -> dict[str, str]:
    parameters: dict[str, str] = {}
    for parameter in module.findall("./PARAMETERS/PARAMETER"):
        name = parameter.attrib.get("NAME")
        value = parameter.attrib.get("VALUE")
        if not name or value is None or name in IGNORED_PARAMETER_NAMES:
            continue
        parameters[name] = value
    return parameters


def parse_modules(root: ET.Element) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    for module in root.findall(".//MODULE"):
        instance = module.attrib.get("INSTANCE")
        if not instance:
            continue
        parameters = parse_module_parameters(module)
        modules[instance] = {
            "instance": instance,
            "modtype": module.attrib.get("MODTYPE"),
            "vlnv": module.attrib.get("VLNV"),
            "parameter_count": len(parameters),
            "parameters": parameters,
        }
    return modules


def parse_memranges(root: ET.Element) -> dict[str, dict[str, str]]:
    memranges: dict[str, dict[str, str]] = {}
    for memrange in root.findall(".//MEMRANGE"):
        instance = memrange.attrib.get("INSTANCE", "")
        slave = memrange.attrib.get("SLAVEBUSINTERFACE", "")
        base = memrange.attrib.get("BASEVALUE", "")
        high = memrange.attrib.get("HIGHVALUE", "")
        key = f"{instance}:{slave}:{base}:{high}"
        memranges[key] = dict(sorted(memrange.attrib.items()))
    return memranges


def parse_hwh_bytes(payload: bytes) -> dict[str, Any]:
    root = ET.fromstring(payload.decode("utf-8-sig", errors="replace"))
    return {
        "module_count": len(root.findall(".//MODULE")),
        "memrange_count": len(root.findall(".//MEMRANGE")),
        "modules": parse_modules(root),
        "memranges": parse_memranges(root),
    }


def parse_xsa(path: Path, *, label: str) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        entries = zip_entry_info(zf)
        hwh_info = parse_hwh_bytes(zf.read("system.hwh")) if "system.hwh" in entries else None
        return {
            "label": label,
            "path": str(path),
            "entry_count": len(entries),
            "entries": entries,
            "embedded_system_top_bit_md5": entries.get("system_top.bit", {}).get("md5"),
            "embedded_system_top_bit_size_bytes": entries.get("system_top.bit", {}).get("size_bytes"),
            "hwh": hwh_info,
        }


def diff_entry_info(lhs: dict[str, dict[str, Any]], rhs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lhs_names = set(lhs)
    rhs_names = set(rhs)
    common = sorted(lhs_names & rhs_names)
    return {
        "lhs_only": sorted(lhs_names - rhs_names),
        "rhs_only": sorted(rhs_names - lhs_names),
        "common_equal": [
            name for name in common if lhs[name]["md5"] == rhs[name]["md5"]
        ],
        "common_different": [
            {
                "name": name,
                "lhs": lhs[name],
                "rhs": rhs[name],
            }
            for name in common
            if lhs[name]["md5"] != rhs[name]["md5"]
        ],
    }


def diff_module_parameters(
    lhs_params: dict[str, str], rhs_params: dict[str, str]
) -> dict[str, Any]:
    lhs_names = set(lhs_params)
    rhs_names = set(rhs_params)
    common = sorted(lhs_names & rhs_names)
    changed = {
        name: {"lhs": lhs_params[name], "rhs": rhs_params[name]}
        for name in common
        if lhs_params[name] != rhs_params[name]
    }
    return {
        "lhs_only": {name: lhs_params[name] for name in sorted(lhs_names - rhs_names)},
        "rhs_only": {name: rhs_params[name] for name in sorted(rhs_names - lhs_names)},
        "changed": changed,
    }


def diff_modules(lhs: dict[str, dict[str, Any]], rhs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lhs_names = set(lhs)
    rhs_names = set(rhs)
    common = sorted(lhs_names & rhs_names)
    diffs: list[dict[str, Any]] = []
    for name in common:
        lhs_module = lhs[name]
        rhs_module = rhs[name]
        identity_changed = {
            "lhs_modtype": lhs_module["modtype"],
            "rhs_modtype": rhs_module["modtype"],
            "lhs_vlnv": lhs_module["vlnv"],
            "rhs_vlnv": rhs_module["vlnv"],
        }
        params = diff_module_parameters(lhs_module["parameters"], rhs_module["parameters"])
        if (
            lhs_module["modtype"] != rhs_module["modtype"]
            or lhs_module["vlnv"] != rhs_module["vlnv"]
            or params["lhs_only"]
            or params["rhs_only"]
            or params["changed"]
        ):
            diffs.append(
                {
                    "instance": name,
                    "identity": identity_changed,
                    "parameter_diff": params,
                }
            )
    return {
        "lhs_only_instances": sorted(lhs_names - rhs_names),
        "rhs_only_instances": sorted(rhs_names - lhs_names),
        "common_changed": diffs,
    }


def diff_memranges(lhs: dict[str, dict[str, str]], rhs: dict[str, dict[str, str]]) -> dict[str, Any]:
    lhs_names = set(lhs)
    rhs_names = set(rhs)
    return {
        "lhs_only": [lhs[name] for name in sorted(lhs_names - rhs_names)],
        "rhs_only": [rhs[name] for name in sorted(rhs_names - lhs_names)],
    }


def build_report(lhs: dict[str, Any], rhs: dict[str, Any]) -> dict[str, Any]:
    entry_diff = diff_entry_info(lhs["entries"], rhs["entries"])
    lhs_hwh = lhs["hwh"] or {"modules": {}, "memranges": {}, "module_count": 0, "memrange_count": 0}
    rhs_hwh = rhs["hwh"] or {"modules": {}, "memranges": {}, "module_count": 0, "memrange_count": 0}
    return {
        "lhs": {
            "label": lhs["label"],
            "path": lhs["path"],
            "entry_count": lhs["entry_count"],
            "embedded_system_top_bit_md5": lhs["embedded_system_top_bit_md5"],
            "embedded_system_top_bit_size_bytes": lhs["embedded_system_top_bit_size_bytes"],
            "module_count": lhs_hwh["module_count"],
            "memrange_count": lhs_hwh["memrange_count"],
        },
        "rhs": {
            "label": rhs["label"],
            "path": rhs["path"],
            "entry_count": rhs["entry_count"],
            "embedded_system_top_bit_md5": rhs["embedded_system_top_bit_md5"],
            "embedded_system_top_bit_size_bytes": rhs["embedded_system_top_bit_size_bytes"],
            "module_count": rhs_hwh["module_count"],
            "memrange_count": rhs_hwh["memrange_count"],
        },
        "file_entry_diff": entry_diff,
        "ps7_init_c_identical": lhs["entries"].get("ps7_init.c", {}).get("md5")
        == rhs["entries"].get("ps7_init.c", {}).get("md5"),
        "ps7_init_tcl_identical": lhs["entries"].get("ps7_init.tcl", {}).get("md5")
        == rhs["entries"].get("ps7_init.tcl", {}).get("md5"),
        "hwh_diff": {
            "module_diff": diff_modules(lhs_hwh["modules"], rhs_hwh["modules"]),
            "memrange_diff": diff_memranges(lhs_hwh["memranges"], rhs_hwh["memranges"]),
        },
    }


def print_summary(report: dict[str, Any]) -> None:
    print(f"LHS: {report['lhs']['label']} -> {report['lhs']['path']}")
    print(f"RHS: {report['rhs']['label']} -> {report['rhs']['path']}")
    print(
        "PS7 init identical:",
        report["ps7_init_c_identical"] and report["ps7_init_tcl_identical"],
    )
    print(
        "Embedded bit md5:",
        report["lhs"]["embedded_system_top_bit_md5"],
        "vs",
        report["rhs"]["embedded_system_top_bit_md5"],
    )
    print(
        "Module counts:",
        report["lhs"]["module_count"],
        "vs",
        report["rhs"]["module_count"],
    )
    module_diff = report["hwh_diff"]["module_diff"]
    print("Modules only in lhs:", ", ".join(module_diff["lhs_only_instances"]) or "none")
    print("Modules only in rhs:", ", ".join(module_diff["rhs_only_instances"]) or "none")
    print("Common modules with identity/parameter differences:", len(module_diff["common_changed"]))
    for module in module_diff["common_changed"]:
        changed = module["parameter_diff"]["changed"]
        lhs_only = module["parameter_diff"]["lhs_only"]
        rhs_only = module["parameter_diff"]["rhs_only"]
        chunks: list[str] = []
        for name, values in changed.items():
            chunks.append(f"{name}={values['lhs']} -> {values['rhs']}")
        for name, value in lhs_only.items():
            chunks.append(f"{name}=lhs_only({value})")
        for name, value in rhs_only.items():
            chunks.append(f"{name}=rhs_only({value})")
        print(f"  - {module['instance']}: {', '.join(chunks)}")

    memrange_diff = report["hwh_diff"]["memrange_diff"]
    print("Memranges only in lhs:", len(memrange_diff["lhs_only"]))
    print("Memranges only in rhs:", len(memrange_diff["rhs_only"]))
    for side, items in (("lhs", memrange_diff["lhs_only"]), ("rhs", memrange_diff["rhs_only"])):
        for item in items:
            print(
                f"  - {side} memrange: {item.get('INSTANCE', '')} "
                f"{item.get('SLAVEBUSINTERFACE', '')} "
                f"{item.get('BASEVALUE', '')}..{item.get('HIGHVALUE', '')}"
            )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lhs", type=Path, help="Reference XSA path")
    parser.add_argument("rhs", type=Path, help="Candidate XSA path")
    parser.add_argument("--lhs-label", default="lhs")
    parser.add_argument("--rhs-label", default="rhs")
    parser.add_argument("--json-out", type=Path)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    lhs = parse_xsa(args.lhs, label=args.lhs_label)
    rhs = parse_xsa(args.rhs, label=args.rhs_label)
    report = build_report(lhs, rhs)
    print_summary(report)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"JSON report: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
