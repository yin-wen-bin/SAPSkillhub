from __future__ import annotations

from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "skills"
    / "FI"
    / "sap-bank-receipt-evidence"
    / "scripts"
    / "bank_receipt_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("bank_receipt_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _profile(*, validated: bool = True) -> dict[str, object]:
    document = json.loads((MODULE_PATH.parents[1] / "references" / "source-profiles.json").read_text(encoding="utf-8"))
    profile = dict(document["profiles"][document["active_profile_id"]])
    profile.update(
        {
            "profile_id": document["active_profile_id"],
            "profile_version": document["profile_version"],
            "profile_status": "validated" if validated else "unvalidated",
            "enabled": validated,
            "profile_sha256": "a" * 64,
        }
    )
    return profile


def _task(**overrides: object) -> dict[str, object]:
    task: dict[str, object] = {
        "schema_version": 1,
        "company_code": "1710",
        "date_from": "2023-11-01",
        "date_to": "2023-11-30",
    }
    task.update(overrides)
    return task


def _row(statement: str = "00000001", item: str = "00001", **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "BANKSTATEMENTSHORTID": statement,
        "BANKSTATEMENTITEM": item,
        "COMPANYCODE": "1710",
        "VALUEDATE": "20231123",
        "POSTINGDATE": "20231124",
        "AMOUNTINTRANSACTIONCURRENCY": "100.10",
        "TRANSACTIONCURRENCY": "USD",
        "DEBITCREDITCODE": "H",
        "BANKSTATEMENTSTATUS": "8",
        "BANKSTATEMENTITEMLIFECYCSTS": "G",
        "ISCOMPLETED": "X",
        "ISINPROCESS": "",
        "POSTINGERRORSTATUS": "",
        "BANKLEDGERDOCUMENT": "",
        "SUBLEDGERDOCUMENT": "",
        "FISCALYEAR": "2023",
        "BUSINESSPARTNERNAME": "Example Payer",
        "PARTNERBANKACCOUNT": "",
        "PARTNERBANKIBAN": "DE00 0000 0000 0000 1234",
        "BANKREFERENCE": "EXAMPLE-REF",
    }
    row.update(overrides)
    return row


def _source(rows: list[dict[str, object]], *, complete: bool = True, total_rows: int | None = None) -> dict[str, object]:
    total = len(rows) if total_rows is None and complete else total_rows
    return {
        "status": "complete" if complete else "partial",
        "rows": rows if complete else [],
        "metadata_sha256": "b" * 64,
        "query_template_sha256": "c" * 64,
        "completeness": {
            "source_complete": complete,
            "paging_complete": complete,
            "total_rows": total,
            "returned_rows": len(rows),
            "truncated": not complete,
        },
        "validation_issues": [] if complete else [{"code": "paging_incomplete", "message": MODULE.SAFE_MESSAGES["paging_incomplete"]}],
    }


class FakeExportError(Exception):
    def __init__(self, code: str, message: str = "safe"):
        super().__init__(message)
        self.code = code


class BankReceiptEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.hash_key = b"k" * 32
        self.current_date = date(2026, 9, 3)

    def execute(self, rows: list[dict[str, object]], **kwargs: object) -> dict[str, object]:
        return MODULE.execute(
            _task(),
            profile=_profile(),
            source_reader=lambda _task, _profile: _source(rows),
            hash_key=self.hash_key,
            current_date=self.current_date,
            **kwargs,
        )

    def test_complete_rows_preserve_decimal_and_separate_reversals(self):
        result = self.execute(
            [
                _row(),
                _row(
                    "00000002",
                    "00001",
                    AMOUNTINTRANSACTIONCURRENCY="25.50-",
                    TRANSACTIONCURRENCY="EUR",
                    BANKSTATEMENTSTATUS="R",
                    BANKSTATEMENTITEMLIFECYCSTS="R",
                    ISCOMPLETED="",
                    PARTNERBANKIBAN="",
                    PARTNERBANKACCOUNT="00009999",
                    BANKLEDGERDOCUMENT="1900000012",
                    SUBLEDGERDOCUMENT="1400000012",
                ),
            ]
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["evidence_status"], "available")
        self.assertTrue(result["completeness"]["evidence_complete"])
        self.assertEqual(result["receipts"][0]["payer_account_masked"], "****1234")
        self.assertEqual(result["receipts"][1]["payer_account_masked"], "****9999")
        self.assertEqual(result["receipts"][1]["reversal_status"], "reversed")
        self.assertEqual(result["receipts"][1]["posting_status"], "completed")
        self.assertEqual(result["receipts"][1]["amount"], "-25.5")
        by_currency = {item["currency"]: item for item in result["currency_summaries"]}
        self.assertEqual(by_currency["USD"]["active_receipt_amount"], "100.1")
        self.assertEqual(by_currency["EUR"]["reversed_receipt_amount"], "-25.5")
        self.assertEqual(
            result["receipts"][0]["payer_account_hash"],
            MODULE._account_evidence(_row(), self.hash_key)[1],
        )

    def test_complete_zero_is_authoritative_not_found(self):
        result = self.execute([])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["evidence_status"], "not_found")
        self.assertEqual(result["receipts"], [])
        self.assertEqual(result["currency_summaries"], [])
        self.assertTrue(result["completeness"]["source_complete"])
        self.assertTrue(result["completeness"]["evidence_complete"])
        self.assertEqual(result["completeness"]["total_rows"], 0)

    def test_unvalidated_profile_never_calls_source(self):
        calls: list[object] = []
        result = MODULE.execute(
            _task(),
            profile=_profile(validated=False),
            source_reader=lambda *args: calls.append(args),
            hash_key=self.hash_key,
            current_date=self.current_date,
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["validation_issues"][0]["code"], "profile_unvalidated")
        self.assertEqual(calls, [])

    def test_incomplete_source_never_leaks_partial_details(self):
        result = MODULE.execute(
            _task(),
            profile=_profile(),
            source_reader=lambda _task, _profile: _source([_row()], complete=False, total_rows=2),
            hash_key=self.hash_key,
            current_date=self.current_date,
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["receipts"], [])
        self.assertEqual(result["currency_summaries"], [])
        self.assertFalse(result["completeness"]["evidence_complete"])

    def test_strict_input_and_date_contract(self):
        cases = (
            (_task(sql="SELECT *"), "invalid_input"),
            (_task(company_code="1710 "), "invalid_input"),
            (_task(date_from="2023-01-01", date_to="2023-02-01"), "date_range_invalid"),
            (_task(date_from="2026-09-01", date_to="2026-09-04"), "future_date_not_allowed"),
            (_task(receipt_reference="*"), "invalid_input"),
            (_task(receipt_reference="   "), "invalid_input"),
        )
        for task, code in cases:
            with self.subTest(code=code, task=task):
                result = MODULE.execute(
                    task,
                    profile=_profile(),
                    source_reader=lambda *_args: self.fail("source must not be called"),
                    hash_key=self.hash_key,
                    current_date=self.current_date,
                )
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["validation_issues"][0]["code"], code)

    def test_exact_reference_only_narrows_fixed_multiline_query(self):
        normalized = MODULE._validate_task(
            _task(receipt_reference="Case-Sensitive-01"),
            current_date=self.current_date,
        )
        query = MODULE.build_query(normalized, ("00000001", "00001"))
        self.assertIn("FROM I_ArBankStatementItem", query)
        self.assertIn("DebitCreditCode = 'H'", query)
        self.assertIn("BankReference = 'Case-Sensitive-01'", query)
        self.assertIn("ORDER BY BankStatementShortID, BankStatementItem", query)
        self.assertNotIn("PaymentAdvice", query)
        self.assertTrue(all(len(line) <= 120 for line in query.splitlines()))
        self.assertEqual([line.strip().rstrip(",") for line in query.splitlines()[1:21]], list(MODULE.SOURCE_FIELDS))

    def test_invalid_rows_fail_closed_without_totals(self):
        cases = (
            (_row(DEBITCREDITCODE="S"), "debit_row_returned"),
            (_row(COMPANYCODE="9999"), "relationship_conflict"),
            (_row(AMOUNTINTRANSACTIONCURRENCY="NaN"), "amount_invalid"),
            (_row(TRANSACTIONCURRENCY=""), "row_required_field_missing"),
            (_row(VALUEDATE="20231340"), "date_invalid"),
            (_row(BANKSTATEMENTSTATUS="Z"), "status_mapping_unknown"),
            (_row(BANKSTATEMENTITEMLIFECYCSTS="Z"), "status_mapping_unknown"),
            (_row(BANKLEDGERDOCUMENT="1900000012", FISCALYEAR=""), "row_required_field_missing"),
            (_row(BUSINESSPARTNERNAME="Bad\nText"), "row_text_invalid"),
        )
        for row, code in cases:
            with self.subTest(code=code):
                result = self.execute([row])
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["receipts"], [])
                self.assertEqual(result["currency_summaries"], [])
                self.assertEqual(result["validation_issues"][0]["code"], code)

    def test_missing_or_short_hash_key_fails_before_source(self):
        calls: list[object] = []
        for key in (None, b"short"):
            with self.subTest(key=key):
                result = MODULE.execute(
                    _task(),
                    profile=_profile(),
                    source_reader=lambda *args: calls.append(args),
                    hash_key=key,
                    current_date=self.current_date,
                )
                self.assertEqual(result["validation_issues"][0]["code"], "hash_key_unavailable")
        self.assertEqual(calls, [])

    def _metadata_fixture(self) -> tuple[str, str, dict[str, object]]:
        source = "define view I_ArBankStatementItem {\n" + "\n".join(MODULE.SOURCE_FIELDS) + "\n}"
        dependency = "define view P_ARBankStatementItemIDBS {\nkey BankStatementShortID,\nkey BankStatementItem\n}"
        profile = _profile()
        profile["metadata_sha256"] = hashlib.sha256(source.encode()).hexdigest()
        profile["dependency_metadata_sha256"] = {
            MODULE.SOURCE_DEPENDENCY: hashlib.sha256(dependency.encode()).hexdigest()
        }
        return source, dependency, profile

    def test_live_reader_proves_keyset_pages_and_counts(self):
        source, dependency, profile = self._metadata_fixture()
        all_rows = [
            {"BANKSTATEMENTSHORTID": f"{index:08d}", "BANKSTATEMENTITEM": "00001"}
            for index in range(1002)
        ]
        previews = [
            SimpleNamespace(columns=MODULE.SOURCE_COLUMNS, rows=all_rows[:1001], total_rows=1002),
            SimpleNamespace(columns=MODULE.SOURCE_COLUMNS, rows=all_rows[1000:], total_rows=2),
        ]

        class Client:
            def metadata(self, _source_type, name):
                return (source if name == MODULE.SOURCE_OBJECT else dependency), "/redacted"

            def preview(self, query, row_number, *, prefer_post=False):
                self.assertions.append((query, row_number, prefer_post))
                return previews.pop(0)

            assertions: list[tuple[str, int, bool]] = []

        common = SimpleNamespace(_validate_compiled_select=lambda query: self.assertNotIn(";", query), ExportError=FakeExportError)
        client = Client()
        result = MODULE.read_source_with_client(
            MODULE._validate_task(_task(), current_date=self.current_date),
            profile,
            client=client,
            common_module=common,
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["completeness"]["total_rows"], 1002)
        self.assertEqual(result["completeness"]["returned_rows"], 1002)
        self.assertEqual(len(client.assertions), 2)
        self.assertTrue(all(call[1:] == (1001, True) for call in client.assertions))

    def test_live_reader_rejects_total_metadata_key_and_column_failures(self):
        source, dependency, profile = self._metadata_fixture()
        normalized = MODULE._validate_task(_task(), current_date=self.current_date)
        cases = (
            ("total", source, dependency, SimpleNamespace(columns=MODULE.SOURCE_COLUMNS, rows=[], total_rows=None), "source_total_unavailable"),
            ("columns", source, dependency, SimpleNamespace(columns=("WRONG",), rows=[], total_rows=0), "source_column_mismatch"),
            ("duplicate", source, dependency, SimpleNamespace(columns=MODULE.SOURCE_COLUMNS, rows=[{"BANKSTATEMENTSHORTID": "1", "BANKSTATEMENTITEM": "1"}, {"BANKSTATEMENTSHORTID": "1", "BANKSTATEMENTITEM": "1"}], total_rows=2), "paging_incomplete"),
            ("metadata", source + " drift", dependency, SimpleNamespace(columns=MODULE.SOURCE_COLUMNS, rows=[], total_rows=0), "metadata_incompatible"),
        )
        for label, live_source, live_dependency, preview, code in cases:
            with self.subTest(label=label):
                class Client:
                    def metadata(self, _source_type, name):
                        return (live_source if name == MODULE.SOURCE_OBJECT else live_dependency), "/redacted"

                    def preview(self, *_args, **_kwargs):
                        return preview

                result = MODULE.read_source_with_client(
                    normalized,
                    profile,
                    client=Client(),
                    common_module=SimpleNamespace(_validate_compiled_select=lambda _query: None, ExportError=FakeExportError),
                )
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["rows"], [])
                self.assertEqual(result["validation_issues"][0]["code"], code)

    def test_bounded_client_uses_post_body_blocks_redirects_and_caps_response(self):
        class Response:
            status_code = 200
            headers = {"Content-Length": "2"}
            _content = b""
            _content_consumed = False

            def iter_content(self, chunk_size):
                del chunk_size
                yield b"ok"

            def close(self):
                self.closed = True

        class Session:
            def __init__(self):
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append((method, url, kwargs))
                return Response()

        common = SimpleNamespace(AdtClient=object, ExportError=FakeExportError, ACCEPT="application/xml")
        client_type = MODULE._bounded_client_class(common)
        client = client_type.__new__(client_type)
        client._session = Session()
        client._url = "https://redacted.invalid/adt"
        client._connection = SimpleNamespace(client="100", language="EN", verify=True, timeout_seconds=120, base_url="https://redacted.invalid")
        response = client._request("POST", row_number=1001, sql="SELECT X FROM Y")
        self.assertEqual(response._content, b"ok")
        method, _url, kwargs = client._session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(kwargs["params"], {"rowNumber": 1001})
        self.assertEqual(kwargs["data"], b"SELECT X FROM Y")
        self.assertFalse(kwargs["allow_redirects"])

        class LargeSession(Session):
            def request(self, method, url, **kwargs):
                response = Response()
                response.headers = {"Content-Length": str(MODULE.MAX_RESPONSE_BYTES + 1)}
                return response

        client._session = LargeSession()
        with self.assertRaises(FakeExportError) as raised:
            client._request("POST", row_number=1, sql="SELECT X FROM Y")
        self.assertEqual(raised.exception.code, "response_too_large")

    def test_csrf_token_requires_token_and_disallows_redirect(self):
        class Response:
            def __init__(self, status, token=None):
                self.status_code = status
                self.headers = {"x-csrf-token": token} if token else {}

        common = SimpleNamespace(AdtClient=object, ExportError=FakeExportError, ACCEPT="application/xml")
        client_type = MODULE._bounded_client_class(common)
        client = client_type.__new__(client_type)
        client._url = "https://redacted.invalid/adt"
        client._connection = SimpleNamespace(client="100", verify=True, timeout_seconds=120)
        client._bounded_request = lambda *_args, **_kwargs: Response(200, "token")
        self.assertEqual(client._csrf_token(), "token")
        client._bounded_request = lambda *_args, **_kwargs: Response(302)
        with self.assertRaises(FakeExportError):
            client._csrf_token()

    def test_artifact_paths_and_manifest_never_echo_sensitive_rows(self):
        self.assertTrue(MODULE._is_allowed_artifact_path(ROOT / ".codex-tmp" / "x.json", must_exist=False))
        self.assertFalse(MODULE._is_allowed_artifact_path(ROOT / "x.json", must_exist=False))
        result = self.execute([_row()])
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as directory:
            output = Path(directory) / "output.json"
            MODULE.write_result(output, result)
            manifest = output.with_name("output.json.manifest.json").read_text(encoding="utf-8")
            for secret in ("Example Payer", "EXAMPLE-REF", "0000 1234", "SELECT", "https://"):
                self.assertNotIn(secret, manifest)
            self.assertEqual(json.loads(manifest)["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_manifest_schema_and_profile_are_fail_closed(self):
        skill = MODULE_PATH.parents[1]
        manifest = json.loads((skill / "manifest.json").read_text(encoding="utf-8"))
        input_schema = json.loads((skill / "references" / "input.schema.json").read_text(encoding="utf-8"))
        output_schema = json.loads((skill / "references" / "output.schema.json").read_text(encoding="utf-8"))
        source_profiles = json.loads((skill / "references" / "source-profiles.json").read_text(encoding="utf-8"))
        active = source_profiles["profiles"][source_profiles["active_profile_id"]]
        self.assertTrue(manifest["read_only"])
        self.assertFalse(manifest["validated"])
        self.assertEqual(manifest["allowed_http_methods"], ["GET", "POST"])
        self.assertNotIn("connection", input_schema["properties"])
        self.assertNotIn("url", input_schema["properties"])
        self.assertNotIn("sql", input_schema["properties"])
        self.assertFalse(active["enabled"])
        self.assertEqual(source_profiles["profile_status"], "unvalidated")
        self.assertIn("requested_scope", output_schema["properties"])
        self.assertIn("validated", output_schema["properties"])

    def test_public_entrypoint_returns_unvalidated_without_sap(self):
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output.json"
            input_path.write_text(json.dumps(_task()), encoding="utf-8")
            self.assertEqual(MODULE.main(["--input", str(input_path), "--output", str(output_path)]), 0)
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["validation_issues"][0]["code"], "profile_unvalidated")


if __name__ == "__main__":
    unittest.main()
