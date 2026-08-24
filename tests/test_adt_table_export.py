from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
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
        "default_profile": "private-qas-secret-profile",
        "profiles": {
            "private-qas-secret-profile": {
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
        "source_type": "table",
        "object": "TSTC",
        "fields": ["TCODE", "PGMNA"],
        "filters": [{"field": "TCODE", "option": "EQ", "value": "SE16N"}],
        "order_by": [{"field": "TCODE", "direction": "asc"}],
        "max_rows": 3,
    }
    value.update(overrides)
    return value


def dynamic_profile():
    return {
        "schema_version": 1,
        "default_profile": "private-qas-secret-profile",
        "profiles": {
            "private-qas-secret-profile": {
                "enabled": True,
                "supported": True,
                "system_id": "TST",
                "timeout_seconds": 5,
                "dynamic_objects": True,
                "max_rows": 30000,
                "page_size": 1000,
                "connection": {
                    "base_url_env": "TEST_ADT_URL",
                    "username_env": "TEST_ADT_USER",
                    "password_env": "TEST_ADT_PASSWORD",
                    "client_env": "TEST_ADT_CLIENT",
                    "verify_ssl_env": "TEST_ADT_VERIFY",
                },
            }
        },
    }


class FakeClient:
    responses = []
    calls = []
    connections = []
    metadata_source = "define table tstc { key tcode : tcode not null; pgmna : program_id; secret_value : char20; }"
    structure_sources = {}
    structure_calls = []

    def __init__(self, connection):
        self.__class__.connections.append(connection)

    def metadata(self, source_type, object_name):
        return self.__class__.metadata_source, "/sap/bc/adt/ddic/tables/tstc/source/main"

    def data_element(self, name):
        return (
            f'<dataElement name="{name}"><dataType>CHAR</dataType></dataElement>',
            f"/sap/bc/adt/ddic/dataelements/{name.lower()}",
        )

    def structure_metadata(self, name):
        self.__class__.structure_calls.append(name)
        source = self.__class__.structure_sources.get(name)
        if source is None:
            raise adt.ExportError("metadata_unavailable", "Structure metadata unavailable.")
        return source, f"/sap/bc/adt/ddic/structures/{name.lower()}/source/main"

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


def write_internal_configuration(directory: Path, profiles=None) -> Path:
    profile_path = directory / "protected-profiles.json"
    profile_path.write_text(json.dumps(profiles or dynamic_profile()), encoding="utf-8")
    env_path = directory / ".env"
    env_path.write_text(
        "\n".join(
            [
                f"SAP_ADT_PROFILES_FILE={profile_path}",
                "TEST_ADT_URL=https://sap.private.invalid:44300",
                "TEST_ADT_USER=private-reader",
                "TEST_ADT_PASSWORD=private-not-logged",
                "TEST_ADT_CLIENT=987",
                "TEST_ADT_VERIFY=true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return env_path


class AdtTableExportTests(unittest.TestCase):
    def setUp(self):
        self.internal_values = {
            "TEST_ADT_URL": "https://sap.private.invalid:44300",
            "TEST_ADT_USER": "private-reader",
            "TEST_ADT_PASSWORD": "private-not-logged",
            "TEST_ADT_CLIENT": "987",
            "TEST_ADT_VERIFY": "true",
        }
        FakeClient.responses = []
        FakeClient.calls = []
        FakeClient.connections = []
        FakeClient.structure_sources = {}
        FakeClient.structure_calls = []
        FakeClient.metadata_source = "define table tstc { key tcode : tcode not null; pgmna : program_id; secret_value : char20; }"

    def test_complete_bounded_query_validates_live_columns(self):
        FakeClient.responses = [preview([{"TCODE": "SE16N", "PGMNA": "RK_SE16N"}])]
        result = adt.execute(task(), profile(), client_factory=FakeClient, internal_values=self.internal_values)
        self.assertEqual(result["status"], "complete")
        self.assertIs(result["read_only"], True)
        self.assertIs(result["validated"], True)
        self.assertIs(result["completeness"]["source_complete"], True)
        self.assertEqual(result["rows"], [{"TCODE": "SE16N", "PGMNA": "RK_SE16N"}])
        self.assertIn("SELECT TCODE, PGMNA FROM TSTC", FakeClient.calls[0][0])
        self.assertEqual(FakeClient.calls[0][1], 3)

    def test_empty_bounded_query_is_live_metadata_validated(self):
        FakeClient.responses = [preview([])]
        result = adt.execute(task(), profile(), client_factory=FakeClient, internal_values=self.internal_values)
        self.assertEqual(
            (result["status"], result["validated"], result["completeness"]["source_complete"]),
            ("complete", True, True),
        )

    def test_row_limit_is_partial_and_never_complete(self):
        FakeClient.responses = [preview([{"TCODE": key, "PGMNA": key} for key in "ABC"])]
        result = adt.execute(task(max_rows=2), profile(), client_factory=FakeClient, internal_values=self.internal_values)
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
        result = adt.execute(task(max_rows=5), profile(), client_factory=FakeClient, internal_values=self.internal_values)
        self.assertEqual(result["status"], "complete")
        self.assertEqual([row["TCODE"] for row in result["rows"]], ["A", "B", "C"])
        self.assertIn("TCODE > 'B'", FakeClient.calls[1][0])

    def test_fail_closed_input_contract(self):
        cases = [
            ({"connection_profile": "caller-selected"}, "filter_not_allowed"),
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
                result = adt.execute(task(**overrides), profile(), client_factory=FakeClient, internal_values=self.internal_values)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["rows"], [])
                self.assertEqual(issue_code(result), expected)

    def test_typed_filter_compiler_escapes_quotes(self):
        request = adt._prepare_request(
            task(filters=[{"field": "TCODE", "option": "EQ", "value": "X' OR '1'='1"}]),
            profile(),
            internal_values=self.internal_values,
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
        request = adt._prepare_request(task(), profile(), internal_values=self.internal_values)
        first = adt.compile_select(request)
        next_page = adt.compile_select(request, last_key=("SE16N",))
        self.assertIn("WHERE TCODE = 'SE16N' ORDER BY TCODE", first)
        self.assertNotIn("WHERE (", first)
        self.assertIn("TCODE = 'SE16N' AND TCODE > 'SE16N'", next_page)

    def test_live_data_preview_metadata_mismatch_fails_closed(self):
        FakeClient.responses = [preview([], columns=("TCODE",))]
        result = adt.execute(task(), profile(), client_factory=FakeClient, internal_values=self.internal_values)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "metadata_unavailable")

    def test_live_ddic_metadata_drift_precedes_preview(self):
        FakeClient.metadata_source = "define table tstc { key tcode : tcode not null; }"
        result = adt.execute(task(), profile(), client_factory=FakeClient, internal_values=self.internal_values)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "field_unavailable")
        self.assertEqual(FakeClient.calls, [])

    def test_dynamic_profile_uses_live_ddic_without_object_field_or_filter_allowlists(self):
        FakeClient.responses = [preview([{"TCODE": "SE16N", "PGMNA": "RK_SE16N"}])]
        dynamic_task = task(filters=[{"field": "PGMNA", "option": "EQ", "value": "RK_SE16N"}])
        dynamic_task.pop("order_by")
        result = adt.execute(
            dynamic_task,
            dynamic_profile(),
            client_factory=FakeClient,
            internal_values=self.internal_values,
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["row_count"], 1)
        self.assertIn("PGMNA = 'RK_SE16N'", FakeClient.calls[0][0])

    def test_dynamic_profile_rejects_fields_absent_from_live_ddic_before_preview(self):
        result = adt.execute(
            task(fields=["TCODE", "NOT_A_FIELD"]),
            dynamic_profile(),
            client_factory=FakeClient,
            internal_values=self.internal_values,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "field_unavailable")
        self.assertEqual(FakeClient.calls, [])

    def test_dynamic_profile_expands_live_ddic_include_before_preview(self):
        FakeClient.metadata_source = (
            "define table mch1 { key mandt : mandt; key matnr : matnr; "
            "key charg : charg; include mchi1 not null; }"
        )
        FakeClient.structure_sources = {
            "MCHI1": "define structure mchi1 { vfdat : vfdat not null; }"
        }
        FakeClient.responses = [
            adt.PreviewResult(
                columns=("MATNR", "CHARG", "VFDAT", "MANDT"),
                rows=(
                    {
                        "MATNR": "FG29",
                        "CHARG": "0000000026",
                        "VFDAT": "",
                        "MANDT": "100",
                    },
                ),
            )
        ]
        include_task = {
            "schema_version": 1,
            "source_type": "table",
            "object": "MCH1",
            "fields": ["MATNR", "CHARG", "VFDAT"],
            "filters": [{"field": "MATNR", "operator": "eq", "value": "FG29"}],
            "max_rows": 100,
        }

        result = adt.execute(
            include_task,
            dynamic_profile(),
            client_factory=FakeClient,
            internal_values=self.internal_values,
        )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(FakeClient.structure_calls, ["MCHI1"])
        self.assertTrue(any(item["type"] == "structure_metadata" for item in result["artifacts"]))
        self.assertIn("VFDAT", FakeClient.calls[0][0])

    def test_dynamic_profile_rejects_recursive_ddic_include_cycle(self):
        FakeClient.metadata_source = (
            "define table mch1 { key mandt : mandt; key matnr : matnr; "
            "key charg : charg; include mchi1 not null; }"
        )
        FakeClient.structure_sources = {
            "MCHI1": "define structure mchi1 { include mchi2; }",
            "MCHI2": "define structure mchi2 { include mchi1; }",
        }

        result = adt.execute(
            task(object="MCH1", fields=["MATNR", "CHARG", "VFDAT"]),
            dynamic_profile(),
            client_factory=FakeClient,
            internal_values=self.internal_values,
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "metadata_unavailable")
        self.assertEqual(FakeClient.calls, [])

    def test_dynamic_profile_allows_30000_rows_but_rejects_30001(self):
        metadata = adt.parse_live_metadata_details("table", FakeClient.metadata_source)
        request = adt._prepare_request(
            task(max_rows=30000),
            dynamic_profile(),
            live_metadata=metadata,
            internal_values=self.internal_values,
        )
        self.assertEqual(request.max_rows, 30000)
        with self.assertRaises(adt.ExportError) as raised:
            adt._prepare_request(
                task(max_rows=30001),
                dynamic_profile(),
                live_metadata=metadata,
                internal_values=self.internal_values,
            )
        self.assertEqual(raised.exception.code, "row_limit_reached")

    def test_dynamic_profile_requires_live_declared_ascending_key(self):
        FakeClient.metadata_source = "define table tstc { tcode : tcode not null; pgmna : program_id; }"
        result = adt.execute(task(), dynamic_profile(), client_factory=FakeClient, internal_values=self.internal_values)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(issue_code(result), "stable_paging_key_unavailable")
        self.assertEqual(FakeClient.calls, [])

    def test_duplicate_or_missing_page_boundaries_fail_closed(self):
        for next_key in ("B", "D"):
            with self.subTest(next_key=next_key):
                FakeClient.responses = [
                    preview([{"TCODE": key, "PGMNA": key} for key in "ABC"]),
                    preview([{"TCODE": next_key, "PGMNA": next_key}]),
                ]
                result = adt.execute(task(max_rows=5), profile(), client_factory=FakeClient, internal_values=self.internal_values)
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
                result = adt.execute(task(), profile(), client_factory=FakeClient, internal_values=self.internal_values)
                self.assertEqual(result["status"], "failed")
                self.assertIs(result["completeness"]["source_complete"], False)
                self.assertEqual(result["rows"], [])
                self.assertEqual(issue_code(result), code)

    def test_http_and_disabled_tls_profiles_are_rejected(self):
        invalid_url = {**self.internal_values, "TEST_ADT_URL": "http://sap.private.invalid:8000"}
        self.assertEqual(
            issue_code(adt.execute(task(), profile(), client_factory=FakeClient, internal_values=invalid_url)),
            "tls_validation_failed",
        )
        disabled_tls = {**self.internal_values, "TEST_ADT_VERIFY": "false"}
        self.assertEqual(
            issue_code(adt.execute(task(), profile(), client_factory=FakeClient, internal_values=disabled_tls)),
            "tls_validation_failed",
        )

    def test_default_profile_failures_are_unsupported_and_do_not_leak_configuration(self):
        missing_default = profile()
        missing_default.pop("default_profile")
        disabled_default = profile()
        disabled_default["profiles"][disabled_default["default_profile"]]["enabled"] = False
        invalid_default = profile()
        invalid_default["default_profile"] = "missing-private-profile"
        for profiles in (missing_default, disabled_default, invalid_default):
            with self.subTest(profiles=profiles):
                result = adt.execute(
                    task(),
                    profiles,
                    client_factory=FakeClient,
                    internal_values=self.internal_values,
                )
                self.assertEqual(issue_code(result), "unsupported_system")
                payload = json.dumps(result)
                for forbidden in (
                    "private-qas-secret-profile",
                    "missing-private-profile",
                    "sap.private.invalid",
                    "private-reader",
                    "private-not-logged",
                ):
                    self.assertNotIn(forbidden, payload)

    def test_caller_environment_cannot_override_internal_connection(self):
        FakeClient.responses = [preview([])]
        hostile = {
            "TEST_ADT_URL": "https://caller-controlled.invalid:44300",
            "TEST_ADT_USER": "caller-user",
            "TEST_ADT_PASSWORD": "caller-password",
            "TEST_ADT_CLIENT": "666",
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            result = adt.execute(
                task(),
                profile(),
                client_factory=FakeClient,
                internal_values=self.internal_values,
            )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(FakeClient.connections[-1].base_url, self.internal_values["TEST_ADT_URL"])
        payload = json.dumps(result)
        for forbidden in (
            "private-qas-secret-profile",
            "sap.private.invalid",
            "private-reader",
            "private-not-logged",
            "caller-controlled.invalid",
            "caller-user",
            "caller-password",
            adt.ENDPOINT,
            "/sap/bc/adt/ddic/tables/tstc/source/main",
        ):
            self.assertNotIn(forbidden, payload)
        for forbidden_key in ("connection_profile", "system_alias", "client", "endpoint", "metadata_endpoint"):
            self.assertNotIn(forbidden_key, result["source"])

    def test_direct_cli_succeeds_without_profile_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            env_path = write_internal_configuration(directory)
            input_path = directory / "input.json"
            output_path = directory / "output.json"
            input_path.write_text(json.dumps(task()), encoding="utf-8")
            FakeClient.responses = [preview([{"TCODE": "SE16N", "PGMNA": "RK_SE16N"}])]
            with mock.patch.object(adt, "INTERNAL_ENV_FILE", env_path), mock.patch.object(adt, "AdtClient", FakeClient):
                exit_code = adt.main(["--input", str(input_path), "--output", str(output_path)])
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(result["status"], "complete")
            self.assertNotIn("connection_profile", result["source"])

    def test_external_process_succeeds_with_same_profile_free_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            env_path = write_internal_configuration(directory)
            input_path = directory / "input.json"
            output_path = directory / "output.json"
            runner_path = directory / "external_runner.py"
            input_path.write_text(json.dumps(task()), encoding="utf-8")
            runner_path.write_text(
                "\n".join(
                    [
                        "import importlib.util, sys",
                        "from pathlib import Path",
                        f"module_path = Path({str(MODULE_PATH)!r})",
                        "spec = importlib.util.spec_from_file_location('external_adt', module_path)",
                        "adt = importlib.util.module_from_spec(spec)",
                        "sys.modules[spec.name] = adt",
                        "spec.loader.exec_module(adt)",
                        "class FakeClient:",
                        "    def __init__(self, connection): pass",
                        "    def metadata(self, source_type, object_name):",
                        "        return 'define table tstc { key tcode : tcode not null; pgmna : program_id; }', '/private/metadata/path'",
                        "    def data_element(self, name):",
                        "        return f'<dataElement name=\"{name}\"><dataType>CHAR</dataType></dataElement>', '/private/data-element/path'",
                        "    def preview(self, sql, row_number):",
                        "        return adt.PreviewResult(columns=('TCODE', 'PGMNA'), rows=({'TCODE': 'SE16N', 'PGMNA': 'RK_SE16N'},))",
                        "adt.INTERNAL_ENV_FILE = Path(sys.argv[1])",
                        "adt.AdtClient = FakeClient",
                        "raise SystemExit(adt.main(['--input', sys.argv[2], '--output', sys.argv[3]]))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            caller_environment = dict(os.environ)
            caller_environment.update(
                {
                    "SAP_ADT_PROFILES_FILE": str(directory / "caller-selected-profiles.json"),
                    "TEST_ADT_URL": "https://caller-controlled.invalid:44300",
                    "TEST_ADT_USER": "caller-user",
                    "TEST_ADT_PASSWORD": "caller-password",
                }
            )
            completed = subprocess.run(
                [sys.executable, str(runner_path), str(env_path), str(input_path), str(output_path)],
                cwd=directory,
                env=caller_environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result_text = output_path.read_text(encoding="utf-8")
            manifest_text = (directory / "output.json.manifest.json").read_text(encoding="utf-8")
            result = json.loads(result_text)
            self.assertEqual(result["status"], "complete")
            combined = result_text + manifest_text + completed.stdout + completed.stderr
            for forbidden in (
                "private-qas-secret-profile",
                "sap.private.invalid",
                "private-reader",
                "private-not-logged",
                "caller-controlled.invalid",
                "caller-user",
                "caller-password",
                "/private/metadata/path",
                "/private/data-element/path",
            ):
                self.assertNotIn(forbidden, combined)

    def test_missing_skill_env_returns_sanitized_unsupported_system(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            missing_env = directory / "private-missing.env"
            input_path = directory / "input.json"
            output_path = directory / "output.json"
            input_path.write_text(json.dumps(task()), encoding="utf-8")
            with mock.patch.object(adt, "INTERNAL_ENV_FILE", missing_env):
                exit_code = adt.main(["--input", str(input_path), "--output", str(output_path)])
            result_text = output_path.read_text(encoding="utf-8")
            result = json.loads(result_text)
            self.assertEqual(exit_code, 1)
            self.assertEqual(issue_code(result), "unsupported_system")
            self.assertNotIn(str(missing_env), result_text)

    def test_cli_has_no_profile_override_option(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            adt.main(["--profiles", "caller.json", "--input", "input.json", "--output", "output.json"])

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
        self.assertEqual(
            adt.parse_data_element_type(
                '<dataElement name="VFDAT"><dataType>DATS</dataType></dataElement>',
                "VFDAT",
            ),
            "date",
        )

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
            adt.write_result(
                output,
                adt.execute(task(), profile(), client_factory=empty_client, internal_values=self.internal_values),
            )
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
                "/sap/bc/adt/ddic/tables/{ddic_object}/source/main",
                "/sap/bc/adt/ddic/structures/{ddic_object}/source/main",
                "/sap/bc/adt/ddic/ddl/sources/{ddic_object}/source/main",
                "/sap/bc/adt/ddic/dataelements/{data_element}",
            ],
        )
        self.assertIs(input_schema["additionalProperties"], False)
        self.assertNotIn("connection_profile", input_schema["properties"])
        self.assertNotIn("connection_profile", input_schema["required"])
        self.assertIn("default_profile", json.loads((skill / "references" / "profiles.example.json").read_text(encoding="utf-8")))
        self.assertEqual(
            output_schema["properties"]["completeness"]["required"],
            ["source_complete", "total_count_known", "truncated", "paging_complete", "reason"],
        )
        client = object.__new__(adt.AdtClient)
        with self.assertRaises(adt.ExportError):
            client._request("DELETE", row_number=1, sql="SELECT TCODE FROM TSTC")


if __name__ == "__main__":
    unittest.main()
