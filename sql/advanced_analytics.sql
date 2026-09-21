-- Governed meter anomaly and bill-versus-meter decision-support views.
-- Robust-z classification uses a trailing median/MAD baseline persisted in
-- analytics_meter_anomaly. The calculation itself is Python because SQLite
-- lacks a native median aggregate; all inputs and outputs stay queryable here.

DROP VIEW IF EXISTS v_meter_anomaly;
CREATE VIEW v_meter_anomaly AS
SELECT
  f.meter_reading_id,
  m.meter_id,
  s.site_id,
  s.site_name,
  m.utility_account_id,
  et.energy_type,
  d.calendar_date AS billing_end_date,
  f.quantity_kwh_equivalent AS observed_kwh,
  a.history_period_count,
  a.baseline_median_kwh,
  a.baseline_mad_kwh,
  a.robust_z_score,
  a.anomaly_status,
  a.methodology,
  a.calculated_at_utc
FROM analytics_meter_anomaly a
JOIN fact_meter_consumption f ON f.meter_consumption_key = a.meter_consumption_key
JOIN dim_meter m ON m.meter_key = f.meter_key
JOIN dim_site s ON s.site_key = m.site_key
JOIN dim_energy_type et ON et.energy_type_key = m.energy_type_key
JOIN dim_date d ON d.date_key = f.billing_end_date_key;

-- Invoice lines are first aggregated, preventing false exceptions where an
-- account has more than one invoice line for the same period.
DROP VIEW IF EXISTS v_bill_meter_variance;
CREATE VIEW v_bill_meter_variance AS
WITH billed AS (
  SELECT
    site_id, utility_account_id, energy_type, billing_start_date, billing_end_date,
    SUM(quantity_kwh_equivalent) AS billed_kwh,
    SUM(invoice_amount_local) AS billed_amount_local,
    MIN(currency_code) AS currency_code,
    COUNT(*) AS invoice_line_count
  FROM v_energy_ledger_enriched
  GROUP BY site_id, utility_account_id, energy_type, billing_start_date, billing_end_date
), metered AS (
  SELECT
    s.site_id, m.utility_account_id, et.energy_type,
    ds.calendar_date AS billing_start_date, de.calendar_date AS billing_end_date,
    SUM(f.quantity_kwh_equivalent) AS metered_kwh,
    COUNT(*) AS meter_reading_count
  FROM fact_meter_consumption f
  JOIN dim_meter m ON m.meter_key = f.meter_key
  JOIN dim_site s ON s.site_key = m.site_key
  JOIN dim_energy_type et ON et.energy_type_key = m.energy_type_key
  JOIN dim_date ds ON ds.date_key = f.billing_start_date_key
  JOIN dim_date de ON de.date_key = f.billing_end_date_key
  GROUP BY s.site_id, m.utility_account_id, et.energy_type, ds.calendar_date, de.calendar_date
)
SELECT
  b.site_id,
  b.utility_account_id,
  b.energy_type,
  b.billing_start_date,
  b.billing_end_date,
  b.invoice_line_count,
  b.billed_kwh,
  m.metered_kwh,
  b.billed_amount_local,
  b.currency_code,
  ROUND(b.billed_kwh - m.metered_kwh, 3) AS billed_minus_metered_kwh,
  ROUND(100.0 * (b.billed_kwh - m.metered_kwh) / NULLIF(m.metered_kwh, 0), 2) AS bill_vs_meter_variance_pct,
  CASE
    WHEN m.metered_kwh IS NULL THEN 'meter_missing'
    WHEN ABS(b.billed_kwh - m.metered_kwh) / NULLIF(m.metered_kwh, 0) > 0.05 THEN 'variance_high'
    ELSE 'within_5pct_tolerance'
  END AS reconciliation_status
FROM billed b
LEFT JOIN metered m ON m.site_id = b.site_id
  AND m.utility_account_id = b.utility_account_id
  AND m.energy_type = b.energy_type
  AND m.billing_start_date = b.billing_start_date
  AND m.billing_end_date = b.billing_end_date;
