-- Energy Ledger dimensional model. Fact grain: one utility invoice line.
PRAGMA foreign_keys = ON;

CREATE TABLE dim_site (
  site_key INTEGER PRIMARY KEY,
  site_id TEXT NOT NULL UNIQUE,
  site_name TEXT NOT NULL,
  country_code TEXT NOT NULL,
  floor_area_sqm REAL NOT NULL,
  active_flag TEXT NOT NULL
);

CREATE TABLE dim_date (
  date_key INTEGER PRIMARY KEY,
  calendar_date TEXT NOT NULL UNIQUE,
  calendar_year INTEGER NOT NULL,
  calendar_month INTEGER NOT NULL,
  month_name TEXT NOT NULL
);

CREATE TABLE dim_energy_type (
  energy_type_key INTEGER PRIMARY KEY,
  energy_type TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_currency (
  currency_key INTEGER PRIMARY KEY,
  currency_code TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_emission_factor (
  emission_factor_key INTEGER PRIMARY KEY,
  factor_id TEXT NOT NULL UNIQUE,
  country_code TEXT NOT NULL,
  energy_type TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to TEXT NOT NULL,
  kgco2e_per_kwh REAL NOT NULL,
  methodology TEXT NOT NULL
);

CREATE TABLE fact_energy_ledger (
  energy_ledger_key INTEGER PRIMARY KEY,
  invoice_line_id TEXT NOT NULL UNIQUE,
  utility_account_id TEXT NOT NULL,
  site_key INTEGER NOT NULL REFERENCES dim_site(site_key),
  billing_start_date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  billing_end_date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  invoice_date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  energy_type_key INTEGER NOT NULL REFERENCES dim_energy_type(energy_type_key),
  currency_key INTEGER NOT NULL REFERENCES dim_currency(currency_key),
  emission_factor_key INTEGER NOT NULL REFERENCES dim_emission_factor(emission_factor_key),
  quantity_native REAL NOT NULL,
  native_unit TEXT NOT NULL,
  quantity_kwh_equivalent REAL NOT NULL,
  invoice_amount_local REAL NOT NULL,
  emissions_kgco2e REAL NOT NULL,
  source_file_name TEXT NOT NULL,
  load_timestamp_utc TEXT NOT NULL
);

-- Meter grain: one meter's consumption for one closed billing interval.
CREATE TABLE dim_meter (
  meter_key INTEGER PRIMARY KEY,
  meter_id TEXT NOT NULL UNIQUE,
  site_key INTEGER NOT NULL REFERENCES dim_site(site_key),
  utility_account_id TEXT NOT NULL,
  energy_type_key INTEGER NOT NULL REFERENCES dim_energy_type(energy_type_key),
  UNIQUE (site_key, utility_account_id, energy_type_key)
);

CREATE TABLE fact_meter_consumption (
  meter_consumption_key INTEGER PRIMARY KEY,
  meter_reading_id TEXT NOT NULL UNIQUE,
  meter_key INTEGER NOT NULL REFERENCES dim_meter(meter_key),
  billing_start_date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  billing_end_date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
  quantity_native REAL NOT NULL,
  native_unit TEXT NOT NULL,
  quantity_kwh_equivalent REAL NOT NULL CHECK (quantity_kwh_equivalent > 0),
  source_file_name TEXT NOT NULL,
  load_timestamp_utc TEXT NOT NULL,
  UNIQUE (meter_key, billing_end_date_key)
);

-- Governed, reproducible decision-support output. The fact key makes each
-- anomaly result traceable to the exact meter interval it assessed.
CREATE TABLE analytics_meter_anomaly (
  meter_consumption_key INTEGER PRIMARY KEY REFERENCES fact_meter_consumption(meter_consumption_key),
  history_period_count INTEGER NOT NULL,
  baseline_median_kwh REAL,
  baseline_mad_kwh REAL,
  robust_z_score REAL,
  anomaly_status TEXT NOT NULL,
  methodology TEXT NOT NULL,
  calculated_at_utc TEXT NOT NULL
);

-- One immutable control record per landed invoice extract.  This retains the
-- source-level count and value needed to reconcile raw, curated, and reporting
-- layers without copying raw invoice lines into the analytics model.
CREATE TABLE audit_source_invoice_control (
  source_file_name TEXT PRIMARY KEY,
  source_row_count INTEGER NOT NULL CHECK (source_row_count >= 0),
  source_invoice_amount_local REAL NOT NULL,
  currency_code TEXT NOT NULL,
  loaded_at_utc TEXT NOT NULL
);
