# SQL Analytics, Exceptions, and Reconciliation

`sql/kpi_layer.sql` is installed into `data/energy_ledger.db` every time the pipeline runs. It supplies an intentionally thin semantic layer over the curated fact and dimensions.

| View | Grain / purpose |
| --- | --- |
| `v_energy_ledger_enriched` | Invoice line enriched with business dimensions and dates. |
| `v_monthly_site_energy_kpis` | Site × energy type × billing month × currency. Provides energy, cost, emissions, cost/kWh, and energy intensity. |
| `v_monthly_portfolio_trends` | Month × currency. Uses `LAG` for period-over-period percentage trends and a three-period rolling energy average. |
| `v_site_size_segments`, `v_monthly_segment_kpis` | Size-based peer segments for operational comparison; thresholds are documented assumptions. |
| `v_invoice_rate_exceptions` | Invoice-line rate screen. A line is `rate_variance_high` only when it is more than 25% from its month/fuel/currency peer average and has at least two peers. |
| `v_reconciliation_source_to_reporting` | Source extract → curated fact → reporting view proof. |

## Reconciliation policy

The pipeline stores a source control record with the raw invoice row count and parsed monetary total. `v_reconciliation_source_to_reporting` compares it with the fact and then the monthly KPI layer. The accepted row-count difference is **0** and the accepted INR value difference is **≤ ₹0.01**, solely to accommodate presentation of SQLite floating-point values. Reconciliation is currency-partitioned; portfolio totals must not combine currencies before an approved FX layer exists.

Run the query after `python3 src/run_pipeline.py`:

```sql
SELECT * FROM v_reconciliation_source_to_reporting;
```

Meter anomaly and bill-versus-meter decision-support outputs are documented in [advanced analytics](advanced_analytics.md).

## EDA

Run `python3 src/run_eda.py` after the pipeline. The script investigates curated-field missingness, descriptive distributions, IQR outlier signals, correlations, and site-level cost/consumption drivers. It writes a concise result narrative to `reports/eda_summary.md` and only two decision-useful PNGs to `reports/figures/`.
