"""Reproducible ingestion, validation, cleaning, and SQLite star-model load."""

import csv
import re
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path


REQUIRED_COLUMNS = {
    "utility_invoices.csv": {
        "invoice_line_id", "site_code", "utility_account", "billing_start",
        "billing_end", "energy_category", "quantity", "unit", "invoice_amount",
        "currency", "invoice_date",
    },
    "sites.csv": {"site_code", "site_name", "country_code", "floor_area_sqm", "active_flag"},
    "emission_factors.csv": {
        "factor_id", "country_code", "energy_type", "effective_from", "effective_to",
        "kgco2e_per_kwh", "methodology",
    },
}
CATEGORY_MAP = {"electricity": "electricity", "power": "electricity", "electric": "electricity",
                "natural gas": "natural_gas", "natural_gas": "natural_gas", "gas": "natural_gas"}
UNIT_TO_KWH = {"kwh": Decimal("1"), "mwh": Decimal("1000"), "gj": Decimal("277.777778"), "therm": Decimal("29.3071")}
SUPPORTED_CURRENCIES = {"INR"}


class DataQualityError(ValueError):
    """Raised when a blocking data quality control fails."""


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataQualityError(f"{path.name}: missing header row")
        missing = REQUIRED_COLUMNS[path.name] - set(reader.fieldnames)
        if missing:
            raise DataQualityError(f"{path.name}: missing required columns: {', '.join(sorted(missing))}")
        rows = list(reader)
    if not rows:
        raise DataQualityError(f"{path.name}: contains no records")
    return rows


def _parse_date(value):
    value = value.strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise DataQualityError(f"invalid date: {value!r}")


def _decimal(value, label):
    cleaned = re.sub(r"[^0-9.\-]", "", value.strip())
    try:
        return Decimal(cleaned)
    except Exception as exc:
        raise DataQualityError(f"invalid {label}: {value!r}") from exc


def _site_id(value):
    cleaned = value.strip().upper()
    return cleaned if cleaned.startswith("IN-") else f"IN-{cleaned}"


def _write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _check_required_values(rows, name):
    required = REQUIRED_COLUMNS[name]
    empty = [f"row {index + 2}: {column}" for index, row in enumerate(rows)
             for column in required if not (row.get(column) or "").strip()]
    if empty:
        raise DataQualityError(f"{name}: required-value null threshold exceeded (0 allowed): {', '.join(empty[:5])}")


def clean(base_dir, as_of_date=None):
    """Read raw source files, enforce controls, and return cleaned dimensions and fact rows."""
    base_dir = Path(base_dir)
    raw_dir = base_dir / "data" / "raw"
    invoices = _read_csv(raw_dir / "utility_invoices.csv")
    sites = _read_csv(raw_dir / "sites.csv")
    factors = _read_csv(raw_dir / "emission_factors.csv")
    for name, rows in (("utility_invoices.csv", invoices), ("sites.csv", sites), ("emission_factors.csv", factors)):
        _check_required_values(rows, name)

    site_rows = []
    for row in sites:
        area = _decimal(row["floor_area_sqm"], "floor area")
        if area <= 0:
            raise DataQualityError(f"sites.csv: invalid floor area for {row['site_code']}")
        site_rows.append({"site_id": _site_id(row["site_code"]), "site_name": row["site_name"].strip(),
                          "country_code": row["country_code"].strip().upper(), "floor_area_sqm": float(area),
                          "active_flag": row["active_flag"].strip().upper()})
    if len({row["site_id"] for row in site_rows}) != len(site_rows):
        raise DataQualityError("sites.csv: duplicate site business key")
    site_map = {row["site_id"]: row for row in site_rows}

    factor_rows = []
    for row in factors:
        energy_type = CATEGORY_MAP.get(row["energy_type"].strip().lower())
        if not energy_type:
            raise DataQualityError(f"emission_factors.csv: unsupported energy type {row['energy_type']!r}")
        factor = _decimal(row["kgco2e_per_kwh"], "emission factor")
        start, end = _parse_date(row["effective_from"]), _parse_date(row["effective_to"])
        if factor < 0 or end < start:
            raise DataQualityError(f"emission_factors.csv: invalid range for {row['factor_id']}")
        factor_rows.append({"factor_id": row["factor_id"].strip(), "country_code": row["country_code"].strip().upper(),
                            "energy_type": energy_type, "effective_from": start.isoformat(), "effective_to": end.isoformat(),
                            "kgco2e_per_kwh": float(factor), "methodology": row["methodology"].strip()})
    if len({row["factor_id"] for row in factor_rows}) != len(factor_rows):
        raise DataQualityError("emission_factors.csv: duplicate factor business key")

    cleaned = []
    seen_invoice_lines = set()
    for raw in invoices:
        line_id = raw["invoice_line_id"].strip()
        if line_id in seen_invoice_lines:
            raise DataQualityError(f"utility_invoices.csv: duplicate invoice_line_id {line_id}")
        seen_invoice_lines.add(line_id)
        site_id = _site_id(raw["site_code"])
        if site_id not in site_map:
            raise DataQualityError(f"utility_invoices.csv: referential integrity failure, unknown site {site_id}")
        energy_type = CATEGORY_MAP.get(raw["energy_category"].strip().lower())
        unit = raw["unit"].strip().lower()
        currency = raw["currency"].strip().upper()
        if not energy_type or unit not in UNIT_TO_KWH or currency not in SUPPORTED_CURRENCIES:
            raise DataQualityError(f"utility_invoices.csv: invalid category, unit, or currency on {line_id}")
        start, end, invoice_date = _parse_date(raw["billing_start"]), _parse_date(raw["billing_end"]), _parse_date(raw["invoice_date"])
        quantity, amount = _decimal(raw["quantity"], "quantity"), _decimal(raw["invoice_amount"], "invoice amount")
        if quantity <= 0 or amount < 0 or end < start or invoice_date < end:
            raise DataQualityError(f"utility_invoices.csv: invalid range on {line_id}")
        matching_factors = [factor for factor in factor_rows if factor["country_code"] == site_map[site_id]["country_code"]
                            and factor["energy_type"] == energy_type and factor["effective_from"] <= end.isoformat() <= factor["effective_to"]]
        if len(matching_factors) != 1:
            raise DataQualityError(f"utility_invoices.csv: factor referential integrity failure on {line_id}")
        factor = matching_factors[0]
        kwh = quantity * UNIT_TO_KWH[unit]
        cleaned.append({
            "invoice_line_id": line_id, "site_id": site_id, "utility_account_id": raw["utility_account"].strip().upper(),
            "billing_start": start.isoformat(), "billing_end": end.isoformat(), "invoice_date": invoice_date.isoformat(),
            "energy_type": energy_type, "quantity_native": float(quantity), "native_unit": unit.upper(),
            "quantity_kwh_equivalent": float(kwh.quantize(Decimal("0.000001"))), "invoice_amount_local": float(amount),
            "currency_code": currency, "factor_id": factor["factor_id"], "emissions_kgco2e": float((kwh * Decimal(str(factor["kgco2e_per_kwh"]))).quantize(Decimal("0.000001"))),
            "source_file_name": "utility_invoices.csv",
        })

    cutoff = (as_of_date or date.today()).toordinal() - 45
    newest = max(_parse_date(row["invoice_date"]) for row in invoices)
    if newest.toordinal() < cutoff:
        raise DataQualityError(f"utility_invoices.csv: freshness failure; newest invoice date {newest} is older than 45 days")
    return site_rows, factor_rows, cleaned, sum(_decimal(row["invoice_amount"], "invoice amount") for row in invoices)


def load_star_model(base_dir, site_rows, factor_rows, facts, raw_value):
    base_dir = Path(base_dir)
    db_path = base_dir / "data" / "energy_ledger.db"
    schema = (base_dir / "sql" / "star_model.sql").read_text(encoding="utf-8")
    kpi_layer = (base_dir / "sql" / "kpi_layer.sql").read_text(encoding="utf-8")
    reconciliation_layer = (base_dir / "sql" / "reconciliation.sql").read_text(encoding="utf-8")
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema)
    connection.executescript(kpi_layer)
    connection.executescript(reconciliation_layer)
    try:
        with connection:
            for row in site_rows:
                connection.execute("INSERT INTO dim_site (site_id, site_name, country_code, floor_area_sqm, active_flag) VALUES (:site_id,:site_name,:country_code,:floor_area_sqm,:active_flag)", row)
            for energy_type in sorted({row["energy_type"] for row in facts}):
                connection.execute("INSERT INTO dim_energy_type (energy_type) VALUES (?)", (energy_type,))
            for currency in sorted({row["currency_code"] for row in facts}):
                connection.execute("INSERT INTO dim_currency (currency_code) VALUES (?)", (currency,))
            for row in factor_rows:
                connection.execute("INSERT INTO dim_emission_factor (factor_id,country_code,energy_type,effective_from,effective_to,kgco2e_per_kwh,methodology) VALUES (:factor_id,:country_code,:energy_type,:effective_from,:effective_to,:kgco2e_per_kwh,:methodology)", row)
            all_dates = sorted({value for row in facts for value in (row["billing_start"], row["billing_end"], row["invoice_date"])})
            for value in all_dates:
                parsed = date.fromisoformat(value)
                connection.execute("INSERT INTO dim_date (date_key,calendar_date,calendar_year,calendar_month,month_name) VALUES (?,?,?,?,?)", (int(parsed.strftime("%Y%m%d")), value, parsed.year, parsed.month, parsed.strftime("%B")))
            ids = {table: dict(connection.execute(f"SELECT {column}, {key} FROM {table}")) for table, column, key in (
                ("dim_site", "site_id", "site_key"), ("dim_energy_type", "energy_type", "energy_type_key"),
                ("dim_currency", "currency_code", "currency_key"), ("dim_emission_factor", "factor_id", "emission_factor_key"))}
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            connection.execute(
                """INSERT INTO audit_source_invoice_control
                   (source_file_name,source_row_count,source_invoice_amount_local,currency_code,loaded_at_utc)
                   VALUES (?,?,?,?,?)""",
                ("utility_invoices.csv", len(facts), float(raw_value), "INR", timestamp),
            )
            for row in facts:
                row["site_key"] = ids["dim_site"][row["site_id"]]
                row["energy_type_key"] = ids["dim_energy_type"][row["energy_type"]]
                row["currency_key"] = ids["dim_currency"][row["currency_code"]]
                row["emission_factor_key"] = ids["dim_emission_factor"][row["factor_id"]]
                row["billing_start_date_key"] = int(row["billing_start"].replace("-", ""))
                row["billing_end_date_key"] = int(row["billing_end"].replace("-", ""))
                row["invoice_date_key"] = int(row["invoice_date"].replace("-", ""))
                row["load_timestamp_utc"] = timestamp
                connection.execute("""INSERT INTO fact_energy_ledger
                    (invoice_line_id,utility_account_id,site_key,billing_start_date_key,billing_end_date_key,invoice_date_key,energy_type_key,currency_key,emission_factor_key,quantity_native,native_unit,quantity_kwh_equivalent,invoice_amount_local,emissions_kgco2e,source_file_name,load_timestamp_utc)
                    VALUES (:invoice_line_id,:utility_account_id,:site_key,:billing_start_date_key,:billing_end_date_key,:invoice_date_key,:energy_type_key,:currency_key,:emission_factor_key,:quantity_native,:native_unit,:quantity_kwh_equivalent,:invoice_amount_local,:emissions_kgco2e,:source_file_name,:load_timestamp_utc)""", row)
        count, value = connection.execute("SELECT COUNT(*), COALESCE(SUM(invoice_amount_local), 0) FROM fact_energy_ledger").fetchone()
        if count != len(facts) or Decimal(str(value)) != raw_value:
            raise DataQualityError(f"reconciliation failure: raw rows/value {len(facts)}/{raw_value}; fact rows/value {count}/{value}")
        return db_path, count, value
    finally:
        connection.close()


def write_report(base_dir, facts, raw_value, loaded_count, loaded_value, as_of_date):
    report = Path(base_dir) / "reports" / "data_quality_report.md"
    report.write_text(f"""# Data Quality Report\n\nGenerated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}\n\n| Control | Result | Evidence |\n| --- | --- | --- |\n| Required columns | PASS | All three raw sources contain their documented required columns. |\n| Null threshold | PASS | 0 nulls in required fields; threshold is 0. |\n| Duplicate business keys | PASS | {len(facts)} unique `invoice_line_id` values and unique dimension business keys. |\n| Invalid ranges | PASS | Positive quantities, non-negative values, valid date intervals, and valid factor ranges. |\n| Referential integrity | PASS | Every invoice resolves to a site and exactly one effective emission factor. |\n| Freshness | PASS | Latest invoice date is within 45 days of {as_of_date.isoformat()}. |\n| Row reconciliation | PASS | Raw invoice rows: {len(facts)}; loaded fact rows: {loaded_count}. |\n| Value reconciliation | PASS | Raw parsed invoice value: {raw_value}; loaded fact value: {loaded_value}. |\n\n## Loaded model\n\n- Fact grain: one utility invoice line (`invoice_line_id`).\n- Fact rows: {loaded_count}.\n- Total invoice value (INR): {loaded_value:.2f}.\n- Total standardized energy (kWh): {sum(row['quantity_kwh_equivalent'] for row in facts):.2f}.\n""", encoding="utf-8")


def run(base_dir, as_of_date=None):
    as_of_date = as_of_date or date.today()
    site_rows, factor_rows, facts, raw_value = clean(base_dir, as_of_date)
    _write_csv(Path(base_dir) / "data" / "staging" / "clean_energy_ledger.csv", facts)
    _write_csv(Path(base_dir) / "data" / "staging" / "dim_site.csv", site_rows)
    db_path, count, value = load_star_model(base_dir, site_rows, factor_rows, facts, raw_value)
    write_report(base_dir, facts, raw_value, count, value, as_of_date)
    return {"database": str(db_path), "fact_rows": count, "invoice_value": float(value)}
