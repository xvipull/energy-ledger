-- Reconciliation control: raw source extract -> curated fact -> reporting KPI.
-- Value tolerance is INR 0.01 for floating-point presentation; row tolerance is 0.
DROP VIEW IF EXISTS v_reconciliation_source_to_reporting;
CREATE VIEW v_reconciliation_source_to_reporting AS
WITH source AS (
  SELECT source_file_name, currency_code,
         source_row_count, source_invoice_amount_local
  FROM audit_source_invoice_control
), curated AS (
  SELECT source_file_name, currency_code,
         COUNT(*) AS curated_row_count,
         SUM(invoice_amount_local) AS curated_invoice_amount_local
  FROM v_energy_ledger_enriched
  GROUP BY source_file_name, currency_code
), reporting AS (
  SELECT currency_code,
         SUM(invoice_line_count) AS reporting_row_count,
         SUM(invoice_amount_local) AS reporting_invoice_amount_local
  FROM v_monthly_site_energy_kpis
  GROUP BY currency_code
)
SELECT
  s.source_file_name,
  s.currency_code,
  s.source_row_count,
  c.curated_row_count,
  r.reporting_row_count,
  s.source_invoice_amount_local,
  c.curated_invoice_amount_local,
  r.reporting_invoice_amount_local,
  ROUND(c.curated_invoice_amount_local - s.source_invoice_amount_local, 2) AS source_to_curated_value_difference,
  ROUND(r.reporting_invoice_amount_local - c.curated_invoice_amount_local, 2) AS curated_to_reporting_value_difference,
  CASE WHEN s.source_row_count = c.curated_row_count
            AND c.curated_row_count = r.reporting_row_count
            AND ABS(c.curated_invoice_amount_local - s.source_invoice_amount_local) <= 0.01
            AND ABS(r.reporting_invoice_amount_local - c.curated_invoice_amount_local) <= 0.01
       THEN 'PASS' ELSE 'FAIL' END AS reconciliation_status
FROM source s
LEFT JOIN curated c ON c.source_file_name = s.source_file_name AND c.currency_code = s.currency_code
LEFT JOIN reporting r ON r.currency_code = s.currency_code;
