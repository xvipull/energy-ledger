"""Reproducible exploratory analysis for the curated Energy Ledger model."""

from __future__ import annotations

import sqlite3
import sys
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-energy-ledger")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def _markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    """Render a small frame without requiring optional tabulate dependency."""
    headers = list(frame.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in frame.itertuples(index=False, name=None):
        formatted = [f"{value:.{digits}f}" if isinstance(value, (float, np.floating)) else str(value) for value in row]
        lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join(lines)


def run(base_dir: Path) -> dict[str, object]:
    base_dir = Path(base_dir)
    database = base_dir / "data" / "energy_ledger.db"
    figures = base_dir / "reports" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    if not database.exists():
        raise FileNotFoundError("Run src/run_pipeline.py before EDA so the curated database exists.")

    with sqlite3.connect(database) as connection:
        invoices = pd.read_sql_query("SELECT * FROM v_energy_ledger_enriched", connection)
        site_kpis = pd.read_sql_query("SELECT * FROM v_monthly_site_energy_kpis", connection)
        reconciliation = pd.read_sql_query("SELECT * FROM v_reconciliation_source_to_reporting", connection)

    numeric = ["quantity_kwh_equivalent", "invoice_amount_local", "emissions_kgco2e", "floor_area_sqm"]
    missingness = invoices.isna().mean().mul(100).rename("missing_pct").reset_index().rename(columns={"index": "field"})
    summary = invoices[numeric].describe().T.reset_index().rename(columns={"index": "metric"})
    correlation = invoices[numeric].corr().round(3)

    # IQR flags are exploratory signals, not automated pipeline failures.
    outlier_rows = []
    for column in ("quantity_kwh_equivalent", "invoice_amount_local", "emissions_kgco2e"):
        lower, upper = invoices[column].quantile([0.25, 0.75])
        iqr = upper - lower
        flagged = ((invoices[column] < lower - 1.5 * iqr) | (invoices[column] > upper + 1.5 * iqr)).sum()
        outlier_rows.append({"metric": column, "iqr_outlier_count": int(flagged)})
    outliers = pd.DataFrame(outlier_rows)

    sns.set_theme(style="whitegrid", context="notebook")
    by_site = invoices.groupby("site_name", as_index=False).agg(
        energy_kwh=("quantity_kwh_equivalent", "sum"),
        invoice_amount_local=("invoice_amount_local", "sum"),
        emissions_kgco2e=("emissions_kgco2e", "sum"),
    )
    order = by_site.sort_values("energy_kwh", ascending=False)["site_name"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.barplot(data=by_site, y="site_name", x="energy_kwh", order=order, color="#2676a1", ax=axes[0])
    axes[0].set(title="Energy consumption by site", xlabel="kWh equivalent", ylabel="")
    sns.scatterplot(data=invoices, x="quantity_kwh_equivalent", y="invoice_amount_local", hue="energy_type", s=95, ax=axes[1])
    axes[1].set(title="Invoice cost driver", xlabel="kWh equivalent", ylabel="Invoice amount (INR)")
    fig.tight_layout()
    driver_chart = figures / "site_energy_cost_drivers.png"
    fig.savefig(driver_chart, dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    sns.histplot(invoices["quantity_kwh_equivalent"], bins=min(8, len(invoices)), kde=True, color="#2676a1", ax=axes[0])
    axes[0].set(title="Invoice energy distribution", xlabel="kWh equivalent", ylabel="Invoice lines")
    missing_plot = missingness.sort_values("missing_pct", ascending=False)
    sns.barplot(data=missing_plot, y="field", x="missing_pct", color="#d67b32", ax=axes[1])
    axes[1].set(title="Curated-field missingness", xlabel="Missing values (%)", ylabel="")
    axes[1].set_xlim(0, max(1, missing_plot["missing_pct"].max() + 1))
    fig.tight_layout()
    quality_chart = figures / "invoice_distribution_and_missingness.png"
    fig.savefig(quality_chart, dpi=160, bbox_inches="tight")
    plt.close(fig)

    cost_energy_corr = correlation.loc["quantity_kwh_equivalent", "invoice_amount_local"]
    top_site = by_site.loc[by_site["energy_kwh"].idxmax()]
    report = f"""# Exploratory Data Analysis

This reproducible analysis reads the curated SQLite views, not the raw files. It is intended to identify investigation leads; the six-line synthetic August 2026 sample is too small for causal conclusions or stable trend inference.

## Findings

- **{top_site['site_name']}** is the largest energy consumer in the sample at **{top_site['energy_kwh']:,.0f} kWh equivalent**.
- Energy and invoice amount have a Pearson correlation of **{cost_energy_corr:.3f}**. Interpret this cautiously: unit rates and energy types vary, and the sample contains only six invoice lines.
- Curated required analytic fields have **{missingness['missing_pct'].max():.0f}%** missingness. Raw-source null controls remain authoritative.
- IQR flags are exploratory only; unusual records should be reviewed with tariff, meter, and period context before being labelled exceptions.

## Distribution summary

{_markdown_table(summary[["metric", "count", "mean", "std", "min", "50%", "max"]])}

## Missingness

{_markdown_table(missingness)}

## IQR outlier screen

{_markdown_table(outliers, digits=0)}

## Correlations

{_markdown_table(correlation.reset_index().rename(columns={"index": "metric"}))}

## Reconciliation status

{_markdown_table(reconciliation)}

## Figures

- `reports/figures/site_energy_cost_drivers.png` — concentration of site energy use and invoice cost relationship.
- `reports/figures/invoice_distribution_and_missingness.png` — distribution shape and curated-field completeness.
"""
    report_path = base_dir / "reports" / "eda_summary.md"
    report_path.write_text(report, encoding="utf-8")
    return {"invoice_lines": len(invoices), "figures": [str(driver_chart), str(quality_chart)], "report": str(report_path)}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run(root)
    print(f"Analysed {result['invoice_lines']} invoice lines; wrote {len(result['figures'])} figures.")
