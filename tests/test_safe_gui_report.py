from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from sapskillhub_export.safe_gui_report import (  # noqa: E402
    SafeGuiReportRunner,
    SafetyViolation,
)


class Control:
    def __init__(self, *, selected=False, text=""):
        self.Selected = selected
        self.Text = text
        self.pressed = False

    def Press(self):
        self.pressed = True

    def SendVKey(self, key):
        self.key = key


class Children:
    def __init__(self, count=1):
        self.Count = count


class Session:
    Busy = False

    def __init__(self, count=1):
        self.controls = {}
        self.Children = Children(count)

    def FindById(self, control_id):
        if control_id not in self.controls:
            raise KeyError(control_id)
        return self.controls[control_id]


def profile():
    return {
        "schema_version": 1,
        "transaction": "MR11",
        "command": "cmd",
        "main_window": "wnd",
        "fields": {"company_code": "company"},
        "modes": {
            "simulation": {
                "required_true": ["test"],
                "required_false": ["post"],
                "execute": "execute",
            }
        },
        "forbidden_controls": ["post"],
        "result_count": "count",
        "grid": "grid",
        "required_columns": ["EBELN", "DMBTR", "WAERS"],
        "amount_field": "DMBTR",
        "currency_field": "WAERS",
    }


class SafeGuiReportTests(unittest.TestCase):
    def configured(self, count="1"):
        session = Session()
        for name in ("cmd", "wnd", "company", "test", "post", "execute"):
            session.controls[name] = Control()
        session.controls["count"] = Control(text=count)
        session.controls["grid"] = Control()
        return session, SafeGuiReportRunner(session, profile(), "MR11")

    def test_candidate_result_and_currency_totals(self):
        session, runner = self.configured()
        runner.enforce_mode("simulation")
        self.assertTrue(session.controls["test"].Selected)
        self.assertFalse(session.controls["post"].Selected)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate.xlsx"

            def fake_export(_session, _grid, path, _overwrite):
                book = openpyxl.Workbook()
                sheet = book.active
                sheet.append(["PO", "Amount", "Currency"])
                sheet.append(["4500001", "20", "CNY"])
                book.save(path)
                book.close()

            with (
                patch("sapskillhub_export.safe_gui_report.export_alv", side_effect=fake_export),
                patch("sapskillhub_export.safe_gui_report.grid_column_ids", return_value=["EBELN", "DMBTR", "WAERS"]),
            ):
                result = runner.export(output)
        self.assertEqual(result.row_count, 1)
        self.assertEqual(result.totals_by_currency, {"CNY": "20"})

    def test_zero_result_uses_verified_numeric_counter(self):
        _session, runner = self.configured(count="0")
        with tempfile.TemporaryDirectory() as directory:
            result = runner.export(Path(directory) / "zero.xlsx")
        self.assertEqual(result.row_count, 0)
        self.assertEqual(result.columns, ("EBELN", "DMBTR", "WAERS"))

    def test_warning_status_does_not_bypass_safety(self):
        session, runner = self.configured()
        with patch("sapskillhub_export.safe_gui_report.status_error", return_value=""):
            runner.enforce_mode("simulation")
            runner.execute("simulation")
        self.assertTrue(session.controls["execute"].pressed)

    def test_error_status_stops(self):
        _session, runner = self.configured()
        with patch("sapskillhub_export.safe_gui_report.status_error", return_value="invalid selection"):
            with self.assertRaisesRegex(RuntimeError, "invalid selection"):
                runner.execute("simulation")

    def test_active_posting_control_and_unknown_dialog_fail_closed(self):
        session, runner = self.configured()
        session.controls["post"].Selected = True
        # Remove it from required_false to prove the independent forbidden check.
        runner.profile["modes"]["simulation"]["required_false"] = []
        with self.assertRaisesRegex(SafetyViolation, "posting/update"):
            runner.enforce_mode("simulation")
        session.controls["post"].Selected = False
        session.Children.Count = 2
        with self.assertRaisesRegex(SafetyViolation, "unexpected dialog"):
            runner.enforce_mode("simulation")


if __name__ == "__main__":
    unittest.main()
