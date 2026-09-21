# Reproducible Data Pipeline

## Selected dataset

The pipeline uses a deliberately small, synthetic August 2026 India utility-invoice dataset representing three facilities, plus site master, emissions-factor reference data, and nine months of monthly meter-consumption intervals. It is safe to commit and exercises the practical source problems expected from utility providers: inconsistent date formats, whitespace/case differences in keys, category aliases, mixed currency formatting, and mixed energy units. Production source files belong in `data/raw/` under the same schemas; raw files are never edited by the pipeline.

## Run

```sh
python3 src/run_pipeline.py
python3 -m unittest discover -s tests -v
```

The run creates `data/energy_ledger.db`, clean staging CSVs, and `reports/data_quality_report.md`. Generated database, staging, and report artifacts are intentionally ignored by Git; they are reproducible from tracked raw data and code.

## Transformations

| Input field | Transformation | Output |
| --- | --- | --- |
| `site_code` | Trim, uppercase, add the `IN-` prefix when omitted; join to site master | `site_id` |
| Date strings | Parse `%d/%m/%Y`, `%Y-%m-%d`, or `%Y/%m/%d`; reject invalid dates | ISO dates |
| `energy_category` | Map `power`/`electric` to `electricity` and `gas` to `natural_gas` | `energy_type` |
| `quantity`, `unit` | Parse numeric input and convert kWh, MWh, GJ, therm to kWh equivalent | `quantity_kwh_equivalent` |
| `invoice_amount` | Remove currency symbols and separators; parse decimal | `invoice_amount_local` |
| `currency` | Trim and uppercase; supported input is INR | `currency_code` |
| Factors | Match country, energy type, and billing end to factor effective period | factor ID and kgCO2e/kWh |

## Quality controls

The pipeline fails before database load on missing required columns, required-value nulls, duplicate business keys, invalid date/quantity/amount ranges, unmapped sites/categories/units/currencies, factor referential-integrity failures, or stale invoice data. The same controls apply to the committed monthly meter-consumption feed (`meter_reading_id` and meter/end-date keys are unique). It also compares raw invoice row count and summed parsed invoice value to the loaded fact table; a mismatch fails the run. The Markdown report records every check and reconciliation result.

## Model and grain

`fact_energy_ledger` has one row per `invoice_line_id` (one utility invoice line for one site, utility account, energy type, and billing period). `invoice_line_id` is the fact business key; `energy_ledger_key` is its surrogate key. Dimensions use integer surrogate keys and retain their source business keys: `dim_site.site_id`, `dim_date.calendar_date`, `dim_energy_type.energy_type`, `dim_currency.currency_code`, and `dim_emission_factor.factor_id`.
