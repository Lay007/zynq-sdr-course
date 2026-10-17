#!/usr/bin/env python3
"""Lab 11.51: lines delivered vs TX level, with and without acknowledgements, from the report data.

    python plot_arq_sweep.py [--json reports/hardware/two-board-arq-20261017.json] [--out docs/assets/...png]

Two panels, one per direction; in each, the share of lines delivered without --arq and with --arq,
against board A's TX gain (board B is always 21 dB lower on the course bench).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
PLAIN, ARQ = "#eb6834", "#2a78d6"   # categorical slots 2 and 1 of the course palette


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=ROOT / "reports/hardware/two-board-arq-20261017.json")
    ap.add_argument("--out", type=Path, default=ROOT / "docs/assets/lab11_51_arq_vs_level.png")
    args = ap.parse_args()
    pts = json.loads(args.json.read_text(encoding="utf-8"))["level_sweep"]["points"]

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6), sharey=True, facecolor=SURFACE)
    for ax, key, title in ((axes[0], "a_to_b", "A → B"), (axes[1], "b_to_a", "B → A")):
        ax.set_facecolor(SURFACE)
        for arq, color, marker, label in ((False, PLAIN, "s", "without --arq"), (True, ARQ, "o", "with --arq")):
            rows = sorted((p for p in pts if p["arq"] == arq), key=lambda p: -p["tx_a_db"])
            x = [p["tx_a_db"] for p in rows]
            y = [100.0 * p[key] / p["rounds"] for p in rows]
            ax.plot(x, y, color=color, lw=2, marker=marker, ms=7, mec=SURFACE, mew=2, label=label, zorder=3)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.set_xlim(-43, -57.5)
        ax.set_ylim(-3, 103)
        ax.set_xticks([-44, -47, -50, -53, -56])
        ax.set_xlabel("board A TX, dB (board B 21 dB lower)", fontsize=8, color=INK2)
        ax.grid(True, color=GRID, lw=0.8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    axes[0].set_ylabel("lines delivered, %", fontsize=8, color=INK2)
    axes[1].legend(loc="lower left", fontsize=8, frameon=False, labelcolor=INK2)
    fig.suptitle("Two-board chat on the course bench: 40 lines per point", x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, facecolor=SURFACE)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
