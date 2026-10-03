"""The resource/timing tables in the Vivado evidence reports must match the metrics JSON.

Each report row that names a top in backticks and is followed by LUT, FF, DSP and
BRAM cells is compared with the post-route numbers Vivado produced, in both the
English and the Russian report (which writes decimals with a comma). Every top in
the JSON must also appear in the table. A number edited by hand, or a JSON
regenerated without updating the report, fails here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FPGA = Path(__file__).resolve().parents[1] / "reports" / "fpga"

REPORTS = (
    ("block8-ofdm-vivado-evidence.md", "block8_ofdm_vivado_ooc_raw/block8_ofdm_vivado_ooc_metrics.json"),
    ("block8-ofdm-vivado-evidence_ru.md", "block8_ofdm_vivado_ooc_raw/block8_ofdm_vivado_ooc_metrics.json"),
    ("block5-bpsk-vivado-evidence.md", "block5_bpsk_vivado_ooc_raw/block5_bpsk_vivado_ooc_metrics.json"),
    ("block5-bpsk-vivado-evidence_ru.md", "block5_bpsk_vivado_ooc_raw/block5_bpsk_vivado_ooc_metrics.json"),
)

TOP_RE = re.compile(r"`([a-z0-9_]+)`")
WNS_RE = re.compile(r"([+-]?\d+[.,]\d+)")


def _int_cell(cell: str) -> int | None:
    cell = cell.strip()
    return int(cell) if cell.isdigit() else None


def table_rows(text: str, tops: set[str]) -> dict[str, dict[str, object]]:
    """Rows of the form | ... | `top` ... | LUT | FF | DSP | BRAM | WNS | ... |."""
    rows: dict[str, dict[str, object]] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = line.strip().strip("|").split("|")
        for index, cell in enumerate(cells):
            match = TOP_RE.search(cell)
            if not match or match.group(1) not in tops:
                continue
            numbers = [_int_cell(c) for c in cells[index + 1:index + 5]]
            if len(numbers) != 4 or any(n is None for n in numbers):
                continue
            wns_cell = cells[index + 5] if index + 5 < len(cells) else ""
            wns = WNS_RE.search(wns_cell)
            rows[match.group(1)] = {
                "lut": numbers[0],
                "ff": numbers[1],
                "dsp": numbers[2],
                "bram": numbers[3],
                "wns": float(wns.group(1).replace(",", ".")) if wns else None,
            }
            break
    return rows


@pytest.mark.parametrize(("report", "metrics"), REPORTS)
def test_report_table_matches_metrics(report: str, metrics: str) -> None:
    data = json.loads((FPGA / metrics).read_text(encoding="utf-8"))
    entries = {entry["top"]: entry for entry in data["tops"]}
    rows = table_rows((FPGA / report).read_text(encoding="utf-8"), set(entries))

    missing = sorted(set(entries) - set(rows))
    assert not missing, f"{report}: tops without a table row: {missing}"

    problems = []
    for top, row in rows.items():
        route = entries[top]["post_route"]
        util = route["utilization"]
        expected = {
            "lut": util["lut"],
            "ff": util["ff"],
            "dsp": util["dsp"],
            "bram": int(util["bram_tiles"]),
        }
        for key, value in expected.items():
            if row[key] != value:
                problems.append(f"{top} {key}: report {row[key]}, Vivado {value}")
        wns = route["timing"].get("wns_ns")
        if wns is None:
            if row["wns"] is not None:
                problems.append(f"{top}: report gives WNS {row['wns']}, Vivado has no clocked path")
        elif row["wns"] is None or abs(row["wns"] - wns) > 0.0005:
            problems.append(f"{top} WNS: report {row['wns']}, Vivado {wns}")
    assert not problems, f"{report}: " + "; ".join(problems)


def test_table_parser_reads_both_decimal_styles() -> None:
    text = (
        "| `a_top` (note) | 10 | 20 | 1 | 0 | +1.335 ns | |\n"
        "| 5.8 | `b_top` | 3 | 4 | 0 | 0 | **-13,447 нс**, 122 | |\n"
        "| `a_top` | WNS -10.2 ns | other table |\n"
    )
    rows = table_rows(text, {"a_top", "b_top"})
    assert rows["a_top"] == {"lut": 10, "ff": 20, "dsp": 1, "bram": 0, "wns": 1.335}
    assert rows["b_top"]["wns"] == -13.447
