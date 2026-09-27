import csv
import io
import json
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from ledger import importing, reporting, storage


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "ledger.sqlite3"
        self.db = storage.connect(self.db_path)
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_payment_requires_exact_invoice_identity(self):
        result = importing.import_csv(
            self.db,
            "payment_id,customer_id,invoice_number,amount\n"
            "P-ID-1,MAPLE,DOES-NOT-EXIST,1250.00\n",
            "payments",
        )
        self.assertEqual(result["imported"], 1)
        row = self.db.execute(
            "SELECT invoice_id FROM payments WHERE payment_id=?", ("P-ID-1",)
        ).fetchone()
        self.assertIsNone(row["invoice_id"])
        self.assertEqual(len(reporting.overview(self.db)["unmatched_payments"]), 1)

    def test_invoice_identity_is_idempotent_but_changed_details_reject(self):
        same = importing.import_csv(
            self.db,
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-100,1250.00,2026-09-01\n",
            "invoices",
        )
        self.assertEqual((same["imported"], same["skipped"], same["rejected"]), (0, 1, 0))

        changed = importing.import_csv(
            self.db,
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-100,1251.00,2026-09-01\n",
            "invoices",
        )
        self.assertEqual((changed["imported"], changed["skipped"], changed["rejected"]), (0, 0, 1))
        row = self.db.execute(
            "SELECT amount FROM invoices WHERE customer_id=? AND invoice_number=?",
            ("HARBOR", "INV-100"),
        ).fetchone()
        self.assertEqual(row["amount"], 1250.0)

    def test_invalid_data_row_does_not_discard_valid_rows(self):
        result = importing.import_csv(
            self.db,
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,GOOD-1,10.00,2026-09-12\n"
            "BAD,BAD-1,20.00,2026-09-12\n"
            "HARBOR,GOOD-2,30.00,2026-09-13\n",
            "invoices",
        )
        self.assertEqual((result["imported"], result["skipped"], result["rejected"]), (2, 0, 1))
        self.assertEqual(result["errors"][0]["line"], 3)
        numbers = {r["invoice_number"] for r in reporting.invoices(self.db)}
        self.assertTrue({"GOOD-1", "GOOD-2"}.issubset(numbers))

    def test_invalid_header_rejects_whole_import(self):
        result = None
        with self.assertRaises(ValueError):
            importing.import_csv(
                self.db,
                "invoice_number,customer_id,amount,due_date\n"
                "NEW,HARBOR,10.00,2026-09-12\n",
                "invoices",
            )
        self.assertIsNone(result)
        self.assertEqual(len(reporting.invoices(self.db)), 6)

    def test_status_filters_are_disjoint(self):
        self.assertEqual([r["invoice_number"] for r in reporting.invoices(self.db, "open")],
                         ["INV-100", "INV-200", "INV-300", "INV-201", "INV-301"])
        self.assertEqual([r["invoice_number"] for r in reporting.invoices(self.db, "paid")],
                         ["INV-101"])

    def test_money_preserves_cents_and_overpayment(self):
        importing.import_csv(
            self.db,
            "customer_id,invoice_number,amount,due_date\n"
            "NORTH,CENT-1,0.30,2026-09-12\n",
            "invoices",
        )
        importing.import_csv(
            self.db,
            "payment_id,customer_id,invoice_number,amount\n"
            "CENT-P1,NORTH,CENT-1,0.10\n"
            "CENT-P2,NORTH,CENT-1,0.20\n",
            "payments",
        )
        row = next(r for r in reporting.invoices(self.db) if r["invoice_number"] == "CENT-1")
        self.assertEqual((row["amount"], row["paid"], row["balance"], row["status"]), (0.3, 0.3, 0.0, "paid"))

        importing.import_csv(
            self.db,
            "customer_id,invoice_number,amount,due_date\n"
            "NORTH,OVER-1,10.00,2026-09-12\n",
            "invoices",
        )
        importing.import_csv(
            self.db,
            "payment_id,customer_id,invoice_number,amount\n"
            "OVER-P1,NORTH,OVER-1,10.01\n",
            "payments",
        )
        row = next(r for r in reporting.invoices(self.db) if r["invoice_number"] == "OVER-1")
        self.assertEqual((row["balance"], row["status"]), (-0.01, "paid"))

    def test_payment_duplicate_identity(self):
        csv_text = "payment_id,customer_id,invoice_number,amount\nP-DUP,HARBOR,INV-100,20.00\n"
        first = importing.import_csv(self.db, csv_text, "payments")
        second = importing.import_csv(self.db, csv_text, "payments")
        changed = importing.import_csv(
            self.db,
            "payment_id,customer_id,invoice_number,amount\nP-DUP,HARBOR,INV-100,21.00\n",
            "payments",
        )
        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(changed["rejected"], 1)

    def test_export_rounds_to_two_decimal_places(self):
        importing.import_csv(
            self.db,
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,EXPORT-1,10.10,2026-09-12\n",
            "invoices",
        )
        row = next(r for r in reporting.export_csv(self.db).splitlines() if "EXPORT-1" in r)
        self.assertIn("10.10,0.00,10.10,open", row)

    def test_filtered_export_improvement(self):
        self.assertIn("INV-101", reporting.export_csv(self.db, "paid"))
        self.assertNotIn("INV-100", reporting.export_csv(self.db, "paid"))

    def test_fixture_preservation(self):
        fixture = Path(__file__).parents[1] / "fixtures" / "existing-register.sqlite3"
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "existing.sqlite3"
            shutil.copy2(fixture, work)
            db = storage.connect(work)
            expected = json.loads(
                (fixture.parent / "expected-records.json").read_text(encoding="utf-8")
            )
            actual_invoices = [dict(r) for r in db.execute(
                "SELECT id, customer_id, invoice_number, amount, due_date FROM invoices ORDER BY id"
            )]
            actual_payments = [dict(r) for r in db.execute(
                "SELECT payment_id, customer_id, invoice_number, amount, invoice_id FROM payments ORDER BY payment_id"
            )]
            self.assertEqual(
                [(r["id"], r["customer_id"], r["invoice_number"], f'{r["amount"]:.2f}', r["due_date"]) for r in actual_invoices],
                [(r["id"], r["customer_id"], r["invoice_number"], r["amount"], r["due_date"]) for r in expected["invoices"]],
            )
            self.assertEqual(
                [(r["payment_id"], r["customer_id"], r["invoice_number"], f'{r["amount"]:.2f}', r["invoice_id"]) for r in actual_payments],
                [(r["payment_id"], r["customer_id"], r["invoice_number"], r["amount"], r["invoice_id"]) for r in expected["payments"]],
            )
            db.close()


if __name__ == "__main__":
    unittest.main()
