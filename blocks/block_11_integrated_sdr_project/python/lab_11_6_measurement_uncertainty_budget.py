#!/usr/bin/env python3
"""Lab 11.6 - Measurement uncertainty budget example."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ASSET_DIR = ROOT / "docs" / "assets"


@dataclass(frozen=True)
class BudgetEntry:
    name: str
    distribution: str
    divisor: float
    value: float


@dataclass(frozen=True)
class BudgetSummary:
    combined_standard_uncertainty: float
    expanded_uncertainty_k2: float
    coverage_factor_k: float
    nominal_measurement: float
    interval_low: float
    interval_high: float


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    nominal_evm_percent = 3.8
    type_a_samples = np.array([3.72, 3.91, 3.85, 3.77, 3.88, 3.81, 3.79, 3.86], dtype=np.float64)
    u_a = float(np.std(type_a_samples, ddof=1) / np.sqrt(len(type_a_samples)))

    entries = [
        BudgetEntry("repeatability (Type A)", "normal", 1.0, u_a),
        BudgetEntry("instrument amplitude accuracy", "rectangular", np.sqrt(3.0), 0.20),
        BudgetEntry("reference clock tolerance", "rectangular", np.sqrt(3.0), 0.08),
        BudgetEntry("cable + connector drift", "rectangular", np.sqrt(3.0), 0.12),
        BudgetEntry("temperature effect", "normal", 1.0, 0.10),
    ]

    u_components = np.array([e.value / e.divisor for e in entries], dtype=np.float64)
    u_c = float(np.sqrt(np.sum(u_components**2)))
    k = 2.0
    u_expanded = float(k * u_c)

    summary = BudgetSummary(
        combined_standard_uncertainty=u_c,
        expanded_uncertainty_k2=u_expanded,
        coverage_factor_k=k,
        nominal_measurement=nominal_evm_percent,
        interval_low=nominal_evm_percent - u_expanded,
        interval_high=nominal_evm_percent + u_expanded,
    )

    fig_path = ASSET_DIR / "lab116_uncertainty_budget_contributions.png"
    table_path = ASSET_DIR / "lab116_uncertainty_budget_table.md"
    metrics_path = ASSET_DIR / "lab116_uncertainty_budget_metrics.json"

    labels = [e.name for e in entries]
    plt.figure(figsize=(8.1, 4.6))
    plt.bar(labels, u_components)
    plt.grid(True, axis="y", alpha=0.35)
    plt.ylabel("Standard uncertainty contribution, % EVM")
    plt.title("Lab 11.6 - Uncertainty budget contributions")
    plt.xticks(rotation=18, ha="right")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()

    table_lines = [
        "# Lab 11.6 uncertainty budget",
        "",
        "| Source | Distribution | Input value | Divisor | Standard contribution |",
        "|---|---|---:|---:|---:|",
    ]
    for e, u in zip(entries, u_components):
        table_lines.append(f"| {e.name} | {e.distribution} | {e.value:.4f} | {e.divisor:.4f} | {u:.4f} |")
    table_lines.extend(
        [
            "",
            f"Combined standard uncertainty: **{u_c:.4f}% EVM**",
            f"Expanded uncertainty (k=2): **{u_expanded:.4f}% EVM**",
            "",
            (
                "Reported result: "
                f"**EVM = {nominal_evm_percent:.3f}% +/- {u_expanded:.3f}% (k=2)**, "
                f"interval [{summary.interval_low:.3f}, {summary.interval_high:.3f}]%"
            ),
        ]
    )
    table_path.write_text("\n".join(table_lines), encoding="utf-8")

    metrics_path.write_text(
        json.dumps(
            {
                "nominal_evm_percent": nominal_evm_percent,
                "type_a_samples_percent": type_a_samples.tolist(),
                "entries": [asdict(e) for e in entries],
                "standard_contributions": u_components.tolist(),
                "summary": asdict(summary),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Lab 11.6 - Measurement uncertainty budget")
    print(f"Nominal EVM: {nominal_evm_percent:.3f}%")
    print(f"Combined standard uncertainty: {u_c:.4f}%")
    print(f"Expanded uncertainty (k=2): {u_expanded:.4f}%")
    print(f"Report interval: [{summary.interval_low:.3f}, {summary.interval_high:.3f}]%")
    print(f"Metrics JSON: {metrics_path}")


if __name__ == "__main__":
    main()
