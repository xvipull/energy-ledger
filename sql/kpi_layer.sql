-- Analytics semantic layer for Energy Ledger (SQLite).
-- All monetary values are local currency; cross-currency portfolio totals must
-- not be used until an approved FX conversion layer is introduced.

DROP VIEW IF EXISTS v_energy_ledger_enriched;
CREATE VIEW v_energy_ledger_enriched AS
SELECT
  f.energy_ledger_key,
  f.invoice_line_id,
  f.utility_account_id,
  s.site_id,
  s.site_name,
  s.country_code,
  s.floor_area_sqm,
  et.energy_type,
  c.currency_code,
  bs.calendar_date AS billing_start_date,
  be.calendar_date AS billing_end_date,
  substr(be.calendar_date, 1, 7) AS billing_month,
  i.calendar_date AS invoice_date,
  f.quantity_native,
  f.native_unit,
  f.quantity_kwh_equivalent,
  f.invoice_amount_local,
  f.emissions_kgco2e,
  ef.factor_id,
  ef.kgco2e_per_kwh,
  f.source_file_name
FROM fact_energy_ledger f
JOIN dim_site s ON s.site_key = f.site_key
JOIN dim_energy_type et ON et.energy_type_key = f.energy_type_key
JOIN dim_currency c ON c.currency_key = f.currency_key
JOIN dim_date bs ON bs.date_key = f.billing_start_date_key
JOIN dim_date be ON be.date_key = f.billing_end_date_key
JOIN dim_date i ON i.date_key = f.invoice_date_key
JOIN dim_emission_factor ef ON ef.emission_factor_key = f.emission_factor_key;

-- Grain: site x energy type x billing month x currency.  Cost/kWh and energy
-- intensity return NULL rather than divide by zero.
DROP VIEW IF EXISTS v_monthly_site_energy_kpis;
CREATE VIEW v_monthly_site_energy_kpis AS
SELECT
  billing_month,
  site_id,
  site_name,
  energy_type,
  currency_code,
  COUNT(*) AS invoice_line_count,
  SUM(quantity_kwh_equivalent) AS energy_kwh,
  SUM(invoice_amount_local) AS invoice_amount_local,
  SUM(emissions_kgco2e) AS emissions_kgco2e,
  ROUND(SUM(invoice_amount_local) / NULLIF(SUM(quantity_kwh_equivalent), 0), 4) AS cost_per_kwh,
  ROUND(SUM(quantity_kwh_equivalent) / NULLIF(MAX(floor_area_sqm), 0), 4) AS energy_kwh_per_sqm,
  ROUND(SUM(emissions_kgco2e) / 1000.0, 4) AS emissions_tco2e
FROM v_energy_ledger_enriched
GROUP BY billing_month, site_id, site_name, energy_type, currency_code;

-- Portfolio trend is partitioned by currency to prevent invalid currency sums.
-- LAG supplies the comparable prior month and a rolling three-period trend.
DROP VIEW IF EXISTS v_monthly_portfolio_trends;
CREATE VIEW v_monthly_portfolio_trends AS
WITH monthly AS (
  SELECT
    billing_month,
    currency_code,
    SUM(energy_kwh) AS energy_kwh,
    SUM(invoice_amount_local) AS invoice_amount_local,
    SUM(emissions_kgco2e) AS emissions_kgco2e
  FROM v_monthly_site_energy_kpis
  GROUP BY billing_month, currency_code
), trended AS (
  SELECT
    *,
    LAG(energy_kwh) OVER (PARTITION BY currency_code ORDER BY billing_month) AS prior_month_energy_kwh,
    LAG(invoice_amount_local) OVER (PARTITION BY currency_code ORDER BY billing_month) AS prior_month_invoice_amount_local,
    AVG(energy_kwh) OVER (PARTITION BY currency_code ORDER BY billing_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS rolling_3_month_energy_kwh
  FROM monthly
)
SELECT
  *,
  ROUND(100.0 * (energy_kwh - prior_month_energy_kwh) / NULLIF(prior_month_energy_kwh, 0), 2) AS energy_mom_pct,
  ROUND(100.0 * (invoice_amount_local - prior_month_invoice_amount_local) / NULLIF(prior_month_invoice_amount_local, 0), 2) AS cost_mom_pct
FROM trended;

-- Operational segment for peer comparison. Floor-area bands are documented
-- assumptions, not a replacement for a governed site classification.
DROP VIEW IF EXISTS v_site_size_segments;
CREATE VIEW v_site_size_segments AS
SELECT
  site_id,
  site_name,
  floor_area_sqm,
  CASE
    WHEN floor_area_sqm >= 15000 THEN 'large_15k_plus_sqm'
    WHEN floor_area_sqm >= 5000 THEN 'medium_5k_to_15k_sqm'
    ELSE 'small_under_5k_sqm'
  END AS site_size_segment
FROM dim_site;

DROP VIEW IF EXISTS v_monthly_segment_kpis;
CREATE VIEW v_monthly_segment_kpis AS
SELECT
  k.billing_month,
  seg.site_size_segment,
  k.energy_type,
  k.currency_code,
  COUNT(DISTINCT k.site_id) AS site_count,
  SUM(k.energy_kwh) AS energy_kwh,
  SUM(k.invoice_amount_local) AS invoice_amount_local,
  ROUND(SUM(k.energy_kwh) / NULLIF(SUM(s.floor_area_sqm), 0), 4) AS energy_kwh_per_sqm
FROM v_monthly_site_energy_kpis k
JOIN v_site_size_segments seg ON seg.site_id = k.site_id
JOIN dim_site s ON s.site_id = k.site_id
GROUP BY k.billing_month, seg.site_size_segment, k.energy_type, k.currency_code;

-- Flag invoice lines whose unit cost differs by more than 25% from the peer
-- site/energy-type/month average. Fewer than two peers are labelled insufficient
-- evidence, rather than marked an exception.
DROP VIEW IF EXISTS v_invoice_rate_exceptions;
CREATE VIEW v_invoice_rate_exceptions AS
WITH priced AS (
  SELECT
    *,
    invoice_amount_local / NULLIF(quantity_kwh_equivalent, 0) AS line_cost_per_kwh
  FROM v_energy_ledger_enriched
), benchmarked AS (
  SELECT
    *,
    COUNT(*) OVER (PARTITION BY billing_month, energy_type, currency_code) AS peer_line_count,
    AVG(line_cost_per_kwh) OVER (PARTITION BY billing_month, energy_type, currency_code) AS peer_avg_cost_per_kwh
  FROM priced
)
SELECT
  invoice_line_id,
  billing_month,
  site_id,
  energy_type,
  currency_code,
  ROUND(line_cost_per_kwh, 4) AS line_cost_per_kwh,
  ROUND(peer_avg_cost_per_kwh, 4) AS peer_avg_cost_per_kwh,
  ROUND(100.0 * (line_cost_per_kwh - peer_avg_cost_per_kwh) / NULLIF(peer_avg_cost_per_kwh, 0), 2) AS variance_to_peer_pct,
  CASE
    WHEN peer_line_count < 2 THEN 'insufficient_peer_evidence'
    WHEN ABS(line_cost_per_kwh - peer_avg_cost_per_kwh) / NULLIF(peer_avg_cost_per_kwh, 0) > 0.25 THEN 'rate_variance_high'
    ELSE 'within_tolerance'
  END AS exception_status
FROM benchmarked;
