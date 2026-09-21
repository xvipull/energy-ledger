-- Load these as Power Query / SQLite source extracts after pipeline refresh.
SELECT * FROM v_energy_ledger_enriched;
SELECT * FROM v_monthly_site_energy_kpis;
SELECT * FROM v_monthly_portfolio_trends;
SELECT * FROM v_invoice_rate_exceptions;
SELECT * FROM v_bill_meter_variance;
SELECT * FROM v_meter_anomaly;
SELECT * FROM v_reconciliation_source_to_reporting;
SELECT calendar_date AS Date, calendar_year, calendar_month, month_name FROM dim_date;
