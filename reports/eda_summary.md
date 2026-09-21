# Exploratory Data Analysis

This reproducible analysis reads the curated SQLite views, not the raw files. It is intended to identify investigation leads; the six-line synthetic August 2026 sample is too small for causal conclusions or stable trend inference.

## Findings

- **Bengaluru HQ** is the largest energy consumer in the sample at **131,944 kWh equivalent**.
- Energy and invoice amount have a Pearson correlation of **-0.487**. Interpret this cautiously: unit rates and energy types vary, and the sample contains only six invoice lines.
- Curated required analytic fields have **0%** missingness. Raw-source null controls remain authoritative.
- IQR flags are exploratory only; unusual records should be reviewed with tariff, meter, and period context before being labelled exceptions.

## Distribution summary

| metric | count | mean | std | min | 50% | max |
| --- | --- | --- | --- | --- | --- | --- |
| quantity_kwh_equivalent | 6.000 | 38498.148 | 46388.774 | 5400.000 | 15550.000 | 119444.445 |
| invoice_amount_local | 6.000 | 99125.000 | 79336.270 | 25500.000 | 68750.000 | 232500.000 |
| emissions_kgco2e | 6.000 | 11327.059 | 7631.394 | 3823.200 | 11009.400 | 24127.778 |
| floor_area_sqm | 6.000 | 10600.000 | 6530.544 | 4100.000 | 9200.000 | 18500.000 |

## Missingness

| field | missing_pct |
| --- | --- |
| energy_ledger_key | 0.000 |
| invoice_line_id | 0.000 |
| utility_account_id | 0.000 |
| site_id | 0.000 |
| site_name | 0.000 |
| country_code | 0.000 |
| floor_area_sqm | 0.000 |
| energy_type | 0.000 |
| currency_code | 0.000 |
| billing_start_date | 0.000 |
| billing_end_date | 0.000 |
| billing_month | 0.000 |
| invoice_date | 0.000 |
| quantity_native | 0.000 |
| native_unit | 0.000 |
| quantity_kwh_equivalent | 0.000 |
| invoice_amount_local | 0.000 |
| emissions_kgco2e | 0.000 |
| factor_id | 0.000 |
| kgco2e_per_kwh | 0.000 |
| source_file_name | 0.000 |

## IQR outlier screen

| metric | iqr_outlier_count |
| --- | --- |
| quantity_kwh_equivalent | 0 |
| invoice_amount_local | 0 |
| emissions_kgco2e | 0 |

## Correlations

| metric | quantity_kwh_equivalent | invoice_amount_local | emissions_kgco2e | floor_area_sqm |
| --- | --- | --- | --- | --- |
| quantity_kwh_equivalent | 1.000 | -0.487 | 0.925 | 0.560 |
| invoice_amount_local | -0.487 | 1.000 | -0.119 | 0.123 |
| emissions_kgco2e | 0.925 | -0.119 | 1.000 | 0.690 |
| floor_area_sqm | 0.560 | 0.123 | 0.690 | 1.000 |

## Reconciliation status

| source_file_name | currency_code | source_row_count | curated_row_count | reporting_row_count | source_invoice_amount_local | curated_invoice_amount_local | reporting_invoice_amount_local | source_to_curated_value_difference | curated_to_reporting_value_difference | reconciliation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| utility_invoices.csv | INR | 6 | 6 | 6 | 594750.000 | 594750.000 | 594750.000 | 0.000 | 0.000 | PASS |

## Figures

- `reports/figures/site_energy_cost_drivers.png` — concentration of site energy use and invoice cost relationship.
- `reports/figures/invoice_distribution_and_missingness.png` — distribution shape and curated-field completeness.
