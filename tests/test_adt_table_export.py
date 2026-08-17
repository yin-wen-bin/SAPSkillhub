from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
SPEC = importlib.util.spec_from_file_location("adt_table_export", MODULE_PATH)
assert SPEC and SPEC.loader
adt = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adt
SPEC.loader.exec_module(adt)


def profile(*, url_env="TEST_ADT_URL", verify_env="TEST_ADT_VERIFY"):
    return {
        "schema_version": 1,
        "profiles": {
            "test": {
                "enabled": True,
                "supported": True,
                "system_id": "TST",
                "timeout_seconds": 5,
                "connection": {
                    "base_url_env": url_env,
                    "username_env": "TEST_ADT_USER",
                    "password_env": "TEST_ADT_PASSWORD",
                    "client_env": "TEST_ADT_CLIENT",
                    "verify_ssl_env": verify_env,
                },
                "deny_object_patterns": ["USR*"],
                "deny_field_patterns": ["*SECRET*"],
                "objects": {
                    "table:TSTC": {
                        "fields": {
                            "TCODE": "string",
                            "PGMNA": "string",
                            "SECRET_VALUE": {"type": "string", "sensitive": True},
                        },
                        "stable_key": ["TCODE"],
                        "bounded_filter_fields": ["TCODE"],
                        "max_rows": 10,
                        "page_size": 2,
                    }
                },
            }
        },
    }


def task(**overrides):
    value = {
        "schema_version": 1,
        "connection_profile": "test",
        "source_type": "table",
        "object": "TSTC",
        "fields": ["TCODE", "PGMNA"],
        "filters": [{"field": "TCODE", "option": "EQ", "value": "SE16N"}],
        "order_by": [{"field": "TCODE", "direction": "asc"}],
        "max_rows": 3,
    }
    value.update(overrides)
    return value


class FakeClient:
    responses = []
    calls = []
    metadata_source = "define table tstc { key tcode : tcode not null; pgmna : program_id; secret_value : char20; }"

    def __init__(self, _connection):
        pass

    def metadata(self, source_type, object_name):
        return self.__class__.metadata_source, "/sap/bc/adt/ddic/tables/tstc/source/main"

    def preview(self, sql, row_number):
        self.__class__.calls.append((sql, row_number))
        response = self.__class__.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def preview(rows, columns=("TCODE", "PGMNA")):
    return adt.PreviewResult(columns=columns, rows=tuple(rows))


def issue_code(result):
    return result["validation_issues"][0]["code"]


class AdtTableExportTests(unittest.TestCase):
    def setUp(self):
        self.environment = mock.patch.dict(
            os.environ,
            {
                "TEST_ADT_URL": "https://sap.example.invalid:44300",
                "TEST_ADT_USER": "reader",
                "TEST_ADT_PASSWORD": "not-logged",
                "TEST_ADT_CLIENT": "100",
                "TEST_ADT_VERIFY": "true",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        FakeClient.responses = []
        FakeClient.calls = []
        FakeClient.metadata_source = "define table tstc { key tcode : tcode not null; pgmna : program_id; secret_value : char20; }"

    def test_complete_bounded_query_validates_live_columns(self):
        FakeClient.responses = [preview([{"TCODE": "SE16N", "PGMNA": "RK_SE16N"}])]
        result = adt.execute(task(), profile(), client_factory=FakeClient)
        self.assertEqual(result["status"], "complete")
        self.assertIs(result["read_only"], True)
        self.assertIs(result["validated"], True)
        self.assertIs(result["completeness"]["source_complete"], True)
        self.assertEqual(result["rows"], [{"TCODE": "SE16N", "PGMNA": "RK_SE16N"}])
        self.assertIn("SELECT TCODE, PGMNA FROM TSTC", FakeClient.calls[0][0])
        self.assertEqual(FakeClient.calls[0][1], 3)

    def test_empty_bounded_query_is_live_metadata_validated(self):
        FakeClient.responses = [preview([])]
        result = adt.execute(task(), profile(), client_factory=FakeClient)
        self.assertEqual(
            (result["status"], result["validated"], result["completeness"]["source_complete"]),
            ("complete", True, True),
        )

    def test_row_limit_is_partial_and_never_complete(self):
        FakeClient.responses = [preview([{"TCODE": key, "PGMNA": key} for key in "ABC"])]
        result = adt.execute(task(max_rows=2), profile(), client_factory=FakeClient)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["row_count"], 2)
        self.assertIs(result["completeness"]["truncated"], True)
        self.assertIs(result["completeness"]["source_complete"], False)
        self.assertEqual(issue_code(result), "row_limit_reached")

    def test_keyset_paging_merges_without_duplicates(self):
        FakeClient.responses = [
            preview([{"TCODE": key, "PGMNA": key} for key in "ABC"]),
            preview([{"TCODE": "C", "PGMNA": "C"}]),
        ]
        result = adt.execute(task(max_rows=5), profile(), client_factory=FakeClient)
        self.assertEqual(result["status"], "complete")
        self.assertEqual([row["TCODE"] for row in result["rows"]], ["A", "B", "C"])
        self.assertIn("TCODE > 'B'", FakeClient.calls[1][0])

    def test_fail_closed_input_contract(self):
        cases = [
            ({"sql": "SELECT * FROM TSTC"}, "filter_not_allowed"),
            ({"password": "bad"}, "filter_not_allowed"),
            ({"object": "USR02"}, "object_not_allowlisted"),
            ({"fields": ["NO_SUCH_FIELD"]}, "field_unavailable"),
            ({"fields": ["SECRET_VALUE"]}, "field_unavailable"),
            ({"filters": [{"field": "PGMNA", "option": "EQ", "value": "X"}]}, "filter_not_allowed"),
            ({"order_by": [{"field": "TCODE", "direction": "desc"}]}, "stable_paging_key_unavailable"),
            ({"max_rows": 11}, "row_limit_reached"),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                result = adt.execute(task(**overrides), profile(), client_factory=FakeClient)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["rows"], [])
                self.assertEqual(issue_code(result), expected)

    def test_typed_filter_compiler_escapes_quotes(self):
        request = adt._prepare_request(
            task(filters=[{"field": "TCODE", "option": "EQ", "value": "X' OR '1'='1"}]),
            profile(),
        )
        sql = adt.compile_select(request)
        self.assertIn("X'' OR ''1''=''1", sql)
        self.assertNotIn(";", adt._mask_literals(sql))

    def test_write_statements_comments_and_multiple_statements_are_unreachable(self):
        statements = [
            "UPDATE TSTC SET TCODE = 'X'",
            "SELECT TCODE FROM TSTC; DELETE FROM TSTC",
            "SELECT TCODE FROM TSTC -- comment",
            "SELECT /* comment */ TCODE FROM TSTC",
            "CALL DANGEROUS_PROCEDURE()",
        ]
        for sql in statements:
            with self.subTest(sql=sql), self.assertRaises(adt.ExportError) as raised:
                adt._validate_compiled_select(sql)
            self.assertEqual(raised.exception.code, "filter_not_allowed")

    def test_compiler_avoids_older_adt_boolean_grouping(self):
        request = adt._prepare_request(task(), profile())
        first = adt.compile_select(request)
        next_page = adt.compile_select(request, last_key=("SE16N",))
        self.assertIn("WHERE TCODE = 'SE16N' ORDER BY TCODE", first)
        self.assertNotIn("WHERE (", first)
        self.assertIn("TCODE = 'SE16N' AND TCODE > 'SE16N'", next_page)

    def test_live_data_preview_metadata_mismatch_fails_closed(self):
        FakeClient.responses = [preview([], columns=("TCODE",))]
        result = adt.execute(task(), profile(), client_factory=FakeClient)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "metadata_unavailable")

    def test_live_ddic_metadata_drift_precedes_preview(self):
        FakeClient.metadata_source = "define table tstc { key tcode : tcode not null; }"
        result = adt.execute(task(), profile(), client_factory=FakeClient)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "field_unavailable")
        self.assertEqual(FakeClient.calls, [])

    def test_duplicate_or_missing_page_boundaries_fail_closed(self):
        for next_key in ("B", "D"):
            with self.subTest(next_key=next_key):
                FakeClient.responses = [
                    preview([{"TCODE": key, "PGMNA": key} for key in "ABC"]),
                    preview([{"TCODE": next_key, "PGMNA": next_key}]),
                ]
                result = adt.execute(task(max_rows=5), profile(), client_factory=FakeClient)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["rows"], [])
                self.assertEqual(issue_code(result), "paging_incomplete")

    def test_closed_set_runtime_failures_return_no_rows(self):
        codes = [
            "authorization_denied",
            "adt_service_unavailable",
            "authentication_failed",
            "tls_validation_failed",
            "timeout",
            "unsupported_system",
        ]
        for code in codes:
            with self.subTest(code=code):
                FakeClient.responses = [adt.ExportError(code, "safe message")]
                result = adt.execute(task(), profile(), client_factory=FakeClient)
                self.assertEqual(result["status"], "failed")
                self.assertIs(result["completeness"]["source_complete"], False)
                self.assertEqual(result["rows"], [])
                self.assertEqual(issue_code(result), code)

    def test_http_and_disabled_tls_profiles_are_rejected(self):
        with mock.patch.dict(os.environ, {"TEST_ADT_URL": "http://sap.example.invalid:8000"}):
            self.assertEqual(
                issue_code(adt.execute(task(), profile(), client_factory=FakeClient)),
                "tls_validation_failed",
            )
        with mock.patch.dict(os.environ, {"TEST_ADT_VERIFY": "false"}):
            self.assertEqual(
                issue_code(adt.execute(task(), profile(), client_factory=FakeClient)),
                "tls_validation_failed",
            )

    def test_parsers_read_preview_and_ddic_metadata(self):
        xml = '<table><columns><metadata name="TCODE"/><dataSet><data>SE16N</data></dataSet></columns><columns><metadata name="PGMNA"/><dataSet><data>RK_SE16N</data></dataSet></columns></table>'
        parsed = adt.parse_preview_xml(xml)
        self.assertEqual(parsed.columns, ("TCODE", "PGMNA"))
        self.assertEqual(parsed.rows, ({"TCODE": "SE16N", "PGMNA": "RK_SE16N"},))
        fields, keys = adt.parse_live_metadata(
            "table",
            "define table tstc { key tcode : tcode not null; pgmna : program_id; }",
        )
        self.assertEqual(fields, {"TCODE", "PGMNA"})
        self.assertEqual(keys, {"TCODE"})

    def test_output_manifest_hash_matches(self):
        empty_client = lambda _connection: type(
            "Empty",
            (),
            {
                "metadata": lambda self, source_type, object_name: (
                    "define table tstc { key tcode : tcode; pgmna : program_id; }",
                    "/metadata",
                ),
                "preview": lambda self, sql, row_number: preview([]),
            },
        )()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output.json"
            adt.write_result(output, adt.execute(task(), profile(), client_factory=empty_client))
            manifest = json.loads((output.parent / "output.json.manifest.json").read_text(encoding="utf-8"))
            self.assertIs(manifest["read_only"], True)
            self.assertEqual(manifest["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_registered_endpoints_and_schemas_are_closed(self):
        skill = ROOT / "skills" / "Common" / "sap-adt-table-export"
        manifest = json.loads((skill / "manifest.json").read_text(encoding="utf-8"))
        input_schema = json.loads((skill / "references" / "input.schema.json").read_text(encoding="utf-8"))
        output_schema = json.loads((skill / "references" / "output.schema.json").read_text(encoding="utf-8"))
        self.assertIs(manifest["read_only"], True)
        self.assertEqual(manifest["allowed_http_methods"], ["GET", "POST"])
        self.assertEqual(
            manifest["allowed_endpoints"],
            [
                "/sap/bc/adt/datapreview/freestyle",
                "/sap/bc/adt/ddic/tables/{allowlisted_object}/source/main",
                "/sap/bc/adt/ddic/ddl/sources/{allowlisted_object}/source/main",
            ],
        )
        self.assertIs(input_schema["additionalProperties"], False)
        self.assertEqual(
            output_schema["properties"]["completeness"]["required"],
            ["source_complete", "total_count_known", "truncated", "paging_complete", "reason"],
        )
        client = object.__new__(adt.AdtClient)
        with self.assertRaises(adt.ExportError):
            client._request("DELETE", row_number=1, sql="SELECT TCODE FROM TSTC")


if __name__ == "__main__":
    unittest.main()
