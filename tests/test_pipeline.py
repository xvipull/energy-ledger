import sqlite3
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import DataQualityError, clean, run


ROOT = Path(__file__).resolve().parents[1]


class EnergyLedgerPipelineTests(unittest.TestCase):
    def test_pipeline_loads_expected_star_model(self):
        result = run(ROOT, as_of_date=date(2026, 9, 16))
        self.assertEqual(result["fact_rows"], 6)
        self.assertEqual(result["invoice_value"], 594750.0)
        connection = sqlite3.connect(result["database"])
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM dim_site").fetchone()[0], 3)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM fact_energy_ledger").fetchone()[0], 6)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM fact_energy_ledger WHERE quantity_kwh_equivalent <= 0").fetchone()[0], 0)
        finally:
            connection.close()

    def test_cleaning_standardizes_keys_units_and_categories(self):
        _, _, facts, _ = clean(ROOT, as_of_date=date(2026, 9, 16))
        gas = next(row for row in facts if row["invoice_line_id"] == "INV-1004-01")
        electricity = next(row for row in facts if row["invoice_line_id"] == "INV-1001-01")
        self.assertEqual(gas["site_id"], "IN-BLR-001")
        self.assertEqual(gas["energy_type"], "natural_gas")
        self.assertAlmostEqual(gas["quantity_kwh_equivalent"], 119444.44454, places=5)
        self.assertEqual(electricity["currency_code"], "INR")

    def test_freshness_control_fails_for_stale_data(self):
        with self.assertRaisesRegex(DataQualityError, "freshness failure"):
            clean(ROOT, as_of_date=date(2027, 1, 1))

    def test_kpi_views_reconcile_source_curated_and_reporting_layers(self):
        result = run(ROOT, as_of_date=date(2026, 9, 16))
        connection = sqlite3.connect(result["database"])
        try:
            reconciliation = connection.execute(
                """SELECT reconciliation_status, source_row_count, curated_row_count,
                          reporting_row_count, source_to_curated_value_difference,
                          curated_to_reporting_value_difference
                   FROM v_reconciliation_source_to_reporting"""
            ).fetchone()
            self.assertEqual(reconciliation, ("PASS", 6, 6, 6, 0.0, 0.0))
            trend = connection.execute(
                "SELECT energy_mom_pct, rolling_3_month_energy_kwh FROM v_monthly_portfolio_trends"
            ).fetchone()
            self.assertIsNone(trend[0])  # First available month has no valid comparison period.
            self.assertAlmostEqual(trend[1], 230988.88904, places=4)
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM v_invoice_rate_exceptions").fetchone()[0], 6
            )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
