from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from sapskillhub_export.core import (  # noqa: E402
    ChunkRange,
    ChunkSpec,
    Filter,
    grouped_filter_semantics,
    load_selection,
    merge_workbooks,
    policy_for,
    recursive_chunks,
    validate_chunk_coverage,
    write_manifest,
    ExportCompletionTimeout,
    wait_export_complete,
)


def workbook(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    book.save(path)
    book.close()


class ExportCoreTests(unittest.TestCase):
    def test_two_sequential_exports_wait_for_stable_file_and_idle_session(self):
        class Session:
            Busy = False

        with tempfile.TemporaryDirectory() as directory:
            for name in ("first.xlsx", "second.xlsx"):
                target = Path(directory) / name

                def writer(path=target):
                    path.write_bytes(b"a")
                    time.sleep(0.03)
                    path.write_bytes(b"abcdef")

                thread = threading.Thread(target=writer)
                thread.start()
                wait_export_complete(
                    Session(), target, timeout=1, stable_for=0.05, poll_interval=0.01
                )
                thread.join()
                self.assertEqual(target.stat().st_size, 6)

    def test_created_file_with_busy_sap_returns_distinct_timeout(self):
        class Session:
            Busy = True

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "created.xlsx"
            target.write_bytes(b"created-but-com-not-finished")
            with self.assertRaisesRegex(ExportCompletionTimeout, "remains busy"):
                wait_export_complete(
                    Session(), target, timeout=0.08, stable_for=0.01, poll_interval=0.01
                )

    def test_json_cli_and_filter_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selection.json"
            path.write_text(json.dumps({"schema_version": 1, "filters": [{"field": "BUKRS", "low": "1710"}]}), encoding="utf-8")
            selection = load_selection(path, ["LIFNR=1,2", "BUDAT=2026-01-01..2026-01-31"], ["BLART=SA"])
        grouped = grouped_filter_semantics(selection.filters)
        self.assertEqual(2, len(grouped["LIFNR"]["include_or"]))
        self.assertEqual("BT", grouped["BUDAT"]["include_or"][0]["option"])
        self.assertEqual("SA", grouped["BLART"]["exclude"][0]["low"])

    def test_all_operators_are_accepted_and_ranges_require_high(self):
        for option in ("EQ", "NE", "GE", "GT", "LE", "LT", "CP", "NP"):
            Filter.from_mapping({"field": "BELNR", "option": option, "low": "1"})
        Filter.from_mapping({"field": "BELNR", "option": "BT", "low": "1", "high": "2"})
        with self.assertRaises(ValueError):
            Filter.from_mapping({"field": "BELNR", "option": "NB", "low": "1"})

    def test_audited_policy_and_unknown_table(self):
        selection = load_selection(where=["BUKRS=1710", "GJAHR=2026", "BELNR=0000000001..0000009999"])
        chunk, keys = policy_for("BSEG", selection)
        self.assertEqual("BELNR", chunk.field)
        self.assertEqual(("BUKRS", "GJAHR", "BELNR", "BUZEI"), keys)
        unknown = load_selection(where=["MATNR=1"])
        self.assertEqual((None, ()), policy_for("MARA", unknown))

    def test_audited_policy_rejects_unbounded_or_wrong_strategy(self):
        with self.assertRaisesRegex(ValueError, "bounded BELNR"):
            policy_for("BSEG", load_selection(where=["BUKRS=1710", "GJAHR=2026"]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selection.json"
            path.write_text(json.dumps({
                "schema_version": 1,
                "filters": [{"field": "BUKRS", "sign": "I", "option": "EQ", "low": "1710"}, {"field": "GJAHR", "sign": "I", "option": "EQ", "low": "2026"}],
                "chunk": {"field": "BUZEI", "type": "integer", "low": "1", "high": "999"},
                "key_fields": ["BUKRS", "GJAHR", "BELNR", "BUZEI"]
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires chunk field/type"):
                policy_for("BSEG", load_selection(path))

    def test_recursive_chunking_and_coverage(self):
        spec = ChunkSpec("BELNR", "padded_integer", "0000", "0099")
        leaves = recursive_chunks(spec, lambda value, limit: int(value.high) - int(value.low) + 1, chunk_size=25)
        self.assertEqual(4, len(leaves))
        validate_chunk_coverage([value for value, _ in leaves], spec)
        with self.assertRaises(ValueError):
            validate_chunk_coverage([ChunkRange("0000", "0010"), ChunkRange("0012", "0099")], spec)

    def test_merge_sort_duplicate_and_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.xlsx", root / "b.xlsx"
            workbook(first, ["K", "V"], [["2", "b"]])
            workbook(second, ["K", "V"], [["1", "a"]])
            output, csv_path = root / "out.xlsx", root / "out.csv"
            result = merge_workbooks([first, second], output, csv_path, ["K"])
            self.assertEqual(2, result["rows"])
            with self.assertRaises(FileExistsError):
                merge_workbooks([first], output, csv_path, ["K"])
            duplicate = root / "duplicate.xlsx"
            workbook(duplicate, ["K", "V"], [["2", "c"]])
            with self.assertRaisesRegex(ValueError, "duplicate business key"):
                merge_workbooks([first, duplicate], root / "d.xlsx", root / "d.csv", ["K"])

    def test_layout_normalization_and_manifest_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "run.manifest.json"
            write_manifest(target, {"status": "complete"})
            with self.assertRaises(FileExistsError):
                write_manifest(target, {"status": "failed"})

    def test_merge_projects_requested_columns_without_csv_extras(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part.xlsx"
            workbook(part, ["K", "V", "EXTRA"], [["1", "a", "drop"]])
            result = merge_workbooks([part], root / "out.xlsx", root / "out.csv", ["K"], output_columns=["K", "V"])
            self.assertEqual(["K", "V"], result["columns"])
            self.assertNotIn("EXTRA", (root / "out.csv").read_text(encoding="utf-8-sig"))

if __name__ == "__main__":
    unittest.main()
