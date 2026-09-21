# User Acceptance Testing

## Scope and evidence

UAT uses the committed synthetic India utility-invoice, site, factor, and meter dataset. Run the tests after `python3 src/run_pipeline.py`; evidence comes from the SQLite views, generated quality report, Power BI import extracts, and Excel management pack. The synthetic September high-consumption meter reading is intentional.

| ID | Stakeholder | Test case | Expected result | Acceptance evidence |
| --- | --- | --- | --- | --- |
| UAT-01 | Finance | Reconcile source invoice rows and value to reporting | 6 source rows = 6 curated rows = 6 reporting rows; value differences are ₹0.00 | `v_reconciliation_source_to_reporting` returns `PASS` |
| UAT-02 | Finance | Review bill-versus-meter variance for August accounts | Five matched site/account/fuel/period records; all are within 5% | `v_bill_meter_variance` shows 5 `within_5pct_tolerance` rows |
| UAT-03 | Facilities | Identify unusual meter consumption | September Bengaluru HQ electricity is a high anomaly after eight history periods | `v_meter_anomaly` shows robust z 96.32 and `anomaly_high` |
| UAT-04 | Sustainability | Trace emissions | Each invoice links to an effective factor and publishes kgCO2e/tCO2e | `v_energy_ledger_enriched` exposes factor ID and emissions |
| UAT-05 | All | Filter / drill to source detail | Site, fuel, month, account, and anomaly status preserve the invoice or meter business key | Power BI model package and Excel detail tab |
| UAT-06 | Data Operations | Reject invalid required input | Missing required column/value, duplicate key, invalid range, unknown site, or factor mismatch blocks load | Automated unit tests and pipeline exceptions |
| UAT-07 | Finance | Scenario review | Changing Excel consumption/rate controls updates energy and cost scenario output | `Scenario` and `Executive Summary` sheets |
| UAT-08 | Report consumer | Review definitions and limitations | KPI, threshold, source, and methodology are visible before interpretation | Power BI definitions page specification and Excel Definitions tab |

## Reconciliation evidence

| Layer | Rows | Invoice value (INR) | Difference |
| --- | ---: | ---: | ---: |
| Raw invoice extract | 6 | 594,750.00 | — |
| Curated fact | 6 | 594,750.00 | 0.00 |
| Reporting KPI layer | 6 | 594,750.00 | 0.00 |

The controlled tolerance is zero rows and ₹0.01 for monetary presentation. Portfolio currency aggregation is prohibited until an approved FX layer is added.

## Performance and edge checks

On the committed sample, the full pipeline and five automated tests complete in under one second on a standard developer laptop. This is a smoke-performance result, not a production throughput benchmark. The UAT regression suite covers stale data, key/category/unit normalization, 45 meter intervals, six prior-period gating, zero-safe calculations, one known anomaly, and 5% variance threshold classification.

Before production sign-off, complete volume testing at expected monthly record counts, role-based access testing in Power BI, source-delivery failure recovery, and approved tariff/FX scenarios.
