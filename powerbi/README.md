# Energy Ledger Power BI Report

Build the report from `data/energy_ledger.db` using the supplied governed SQL extracts and DAX measures. The model uses a dedicated `Dim Date` table with active `Billing End Date` and inactive `Billing Start Date` and `Invoice Date` relationships to invoice activity. Use `USERELATIONSHIP` in measures that need the inactive date roles.

## Report pages

1. **Executive overview**: cards for invoice cost, energy, emissions, energy intensity, bill-meter variance, anomaly count, and data-quality pass count. Include billing-month, site, energy-type, and currency slicers.
2. **Diagnostics**: ranked site/fuel cost and consumption, cost-per-kWh outliers, invoice-rate exceptions, and a drill-through button to invoice detail.
3. **Trend**: monthly energy, cost, emissions, and month-over-month changes. Use the proper date table and continuous month axis.
4. **Invoice and meter detail**: drill-through by site/account/energy type, with invoice lines, meter intervals, bill-meter variance, and anomaly baseline evidence.
5. **Data quality**: raw-to-curated-to-reporting row/value reconciliation and control status.
6. **Definitions and help**: metric formulas, 5% bill-meter tolerance, 3.5 robust-z threshold, source scope, and limitations.

## Interaction design

Use report-page tooltips for cost/kWh, intensity, factor version, meter baseline median/MAD, robust z-score, and source file. Apply conditional formatting to high variance and anomaly status. Cross-filter charts from the site/fuel slicers. Avoid aggregating currencies before an approved FX layer is added.

## Refresh

Run `python3 src/run_pipeline.py`, then refresh the SQLite extracts. Details are in `sqlite_import_queries.sql`. An SQLite ODBC driver or Power Query SQLite connector is required in the desktop environment.
