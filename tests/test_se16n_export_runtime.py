from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/Common/sap-se16n-export/scripts/se16n_export.py"
spec = importlib.util.spec_from_file_location("se16n_runtime", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

batch_spec = importlib.util.spec_from_file_location(
    "se16n_batch_runtime",
    ROOT / "skills/Common/sap-se16n-export/scripts/se16n_batch.py",
)
batch_module = importlib.util.module_from_spec(batch_spec)
assert batch_spec and batch_spec.loader
batch_spec.loader.exec_module(batch_module)


class Control:
    def __init__(self):
        self.Text = ""
        self.Key = ""
        self.pressed = False

    def Press(self):
        self.pressed = True


class Scrollbar:
    Position = 0


class SelectionTable:
    def __init__(self, rows, visible_rows=None):
        self.RowCount = rows
        self.VisibleRowCount = visible_rows or rows
        self.VerticalScrollbar = Scrollbar()


class Session:
    def __init__(self):
        self.controls = {}

    def FindById(self, control_id):
        return self.controls.setdefault(control_id, Control())


class Window(Control):
    def __init__(self):
        super().__init__()
        self.keys = []

    def SendVKey(self, key):
        self.keys.append(key)


class Se16nRuntimeTests(unittest.TestCase):
    def test_default_mode_is_validation_and_legacy_maxhits_is_explicit(self):
        args = module.build_parser().parse_args([])
        self.assertEqual("validate", args.mode)
        self.assertIsNone(args.maxhits)
        args = module.build_parser().parse_args(["--maxhits", "90000"])
        self.assertEqual(90000, args.maxhits)

    def test_filter_cells_are_entered_and_read_back(self):
        session = Session()
        session.controls["table"] = SelectionTable(2)
        session.controls["field-0"] = Control()
        session.controls["field-0"].Text = "BUKRS"
        session.controls["field-1"] = Control()
        session.controls["field-1"].Text = "BUDAT"
        profile = {
            "selection_table": "table",
            "selection_rows": {
                name: name + "-{row}"
                for name in ("field", "low", "high", "multiple")
            },
        }
        filters = [module.Filter("BUKRS", "I", "EQ", "1710"), module.Filter("BUDAT", "I", "BT", "2026-01-01", "2026-01-31")]
        module.apply_filters(session, filters, profile)
        self.assertEqual("1710", session.controls["low-0"].Text)
        self.assertEqual("2026-01-31", session.controls["high-1"].Text)

    def test_multivalue_and_exclusion_use_multiple_selection_controls(self):
        session = Session()
        session.controls["table"] = SelectionTable(1)
        session.controls["field-0"] = Control()
        session.controls["field-0"].Text = "LIFNR"
        profile = {
            "selection_table": "table",
            "selection_rows": {
                name: name + "-{row}"
                for name in ("field", "low", "high", "multiple")
            },
            "multiple_selection": {
                "accept": "accept",
                "rows": {
                    name: "dialog-" + name + "-{row}"
                    for name in ("sign", "option", "low", "high")
                },
            },
        }
        module.apply_filters(
            session,
            [
                module.Filter("LIFNR", "I", "EQ", "1"),
                module.Filter("LIFNR", "E", "CP", "9*"),
            ],
            profile,
        )
        self.assertTrue(session.controls["multiple-0"].pressed)
        self.assertEqual("E", session.controls["dialog-sign-1"].Key)
        self.assertEqual("CP", session.controls["dialog-option-1"].Key)
        self.assertTrue(session.controls["accept"].pressed)

    def test_chunk_replaces_only_includes_and_preserves_exclusions(self):
        selection = module.Selection(
            1,
            (
                module.Filter("BELNR", "I", "BT", "0001", "9999"),
                module.Filter("BELNR", "E", "EQ", "0100"),
                module.Filter("BUKRS", "I", "EQ", "1710"),
            ),
            (), (), None, (),
        )
        chunked = module.with_chunk(selection, "BELNR", "0001", "4999")
        self.assertIn(module.Filter("BELNR", "E", "EQ", "0100"), chunked.filters)
        self.assertIn(module.Filter("BELNR", "I", "BT", "0001", "4999"), chunked.filters)

    def test_reset_uses_current_transaction_only(self):
        session = Session()
        session.Busy = False
        session.controls["wnd"] = Window()
        profile = {"command": "cmd", "main_window": "wnd"}
        module.reset_se16n_session(session, profile)
        self.assertEqual(session.controls["cmd"].Text, "/nSE16N")
        self.assertEqual(session.controls["wnd"].keys, [0])

    def test_batch_runs_jobs_sequentially_and_stops_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "batch.json"
            path.write_text(json.dumps({"jobs": [
                {"table": "AFRU", "where": ["WERKS=1000"]},
                {"table": "RESB", "where": ["WERKS=1000"]},
                {"table": "MARA"},
            ]}), encoding="utf-8")
            calls = []

            def fake_main(argv):
                calls.append(argv)
                return 2 if "RESB" in argv else 0

            original = batch_module.export_main
            batch_module.export_main = fake_main
            try:
                code = batch_module.main(["--batch-file", str(path)])
            finally:
                batch_module.export_main = original
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 2)
        self.assertIn("--where", calls[0])


if __name__ == "__main__":
    unittest.main()
