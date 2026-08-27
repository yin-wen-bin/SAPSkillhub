from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "CO" / "sap-wbs-object-resolver" / "scripts" / "wbs_object_resolver.py"
SPEC = importlib.util.spec_from_file_location("wbs_object_resolver", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
PROFILE = json.loads(MODULE.PROFILE_PATH.read_text(encoding="utf-8"))


def _project(**overrides: str) -> dict[str, str]:
    row = {"WBSElementInternalID": "00000123", "WBSElementExternalID": "P-100.01", "CompanyCode": "1710", "ControllingArea": "A000", "ProjectInternalID": "00000042"}
    row.update(overrides)
    return row


def _financial(**overrides: str) -> dict[str, str]:
    row = {"WBSElementInternalID": "00000123", "WBSElement": "P-100.01", "WBSElementObject": "PR00000123", "CompanyCode": "1710", "ControllingArea": "A000", "ProjectInternalID": "00000042", "Project": "P-100"}
    row.update(overrides)
    return row


def _executor(project_rows=None, financial_rows=None, *, metadata_ok=True, complete=True):
    values = [project_rows if project_rows is not None else [_project()], financial_rows if financial_rows is not None else [_financial()]]
    calls = []

    def execute(source, wbs, company):
        index = len(calls)
        calls.append((source["id"], wbs, company))
        rows = values[index]
        return {"metadata_sha256": source["metadata_sha256"] if metadata_ok else "0" * 64, "rows": rows, "total_rows": len(rows), "source_complete": complete, "paging_complete": complete}

    return execute, calls


class WbsResolverTests(unittest.TestCase):
    def test_resolves_one_cross_checked_object_and_preserves_case_and_separators(self):
        executor, calls = _executor()
        result = MODULE.execute({"schema_version": 1, "wbs_external_id": "  P-100.01  ", "company_code": "1710"}, source_executor=executor, profile=PROFILE)
        self.assertEqual((result["status"], result["resolution_status"], result["validated"]), ("complete", "resolved", True))
        self.assertEqual(result["resolved_object"]["object_number"], "PR00000123")
        self.assertEqual([call[1] for call in calls], ["P-100.01", "P-100.01"])
        self.assertTrue(result["completeness"]["evidence_complete"])

    def test_complete_zero_is_not_found_without_object(self):
        executor, _ = _executor([], [])
        result = MODULE.execute({"schema_version": 1, "wbs_external_id": "P-NONE", "company_code": "1710"}, source_executor=executor, profile=PROFILE)
        self.assertEqual((result["status"], result["resolution_status"], result["resolved_object"]), ("partial", "not_found", None))
        self.assertTrue(result["completeness"]["source_complete"])
        self.assertFalse(result["completeness"]["evidence_complete"])

    def test_multiple_rows_are_ambiguous(self):
        executor, _ = _executor([_project(), _project(WBSElementInternalID="00000124")], [_financial()])
        result = MODULE.execute({"schema_version": 1, "wbs_external_id": "P-100.01", "company_code": "1710"}, source_executor=executor, profile=PROFILE)
        self.assertEqual(result["resolution_status"], "ambiguous")
        self.assertIsNone(result["resolved_object"])

    def test_relationship_conflict_does_not_return_object(self):
        executor, _ = _executor([_project(ControllingArea="B000")], [_financial()])
        result = MODULE.execute({"schema_version": 1, "wbs_external_id": "P-100.01", "company_code": "1710"}, source_executor=executor, profile=PROFILE)
        self.assertEqual(result["resolution_status"], "ambiguous")
        self.assertEqual(result["validation_issues"][0]["code"], "relationship_inconsistent")
        self.assertIsNone(result["resolved_object"])

    def test_metadata_or_paging_failure_is_source_unavailable(self):
        executor, _ = _executor(metadata_ok=False, complete=False)
        result = MODULE.execute({"schema_version": 1, "wbs_external_id": "P-100.01", "company_code": "1710"}, source_executor=executor, profile=PROFILE)
        self.assertEqual(result["resolution_status"], "source_unavailable")
        self.assertIn("metadata_incompatible", {item["code"] for item in result["validation_issues"]})
        self.assertFalse(result["completeness"]["paging_complete"])

    def test_unknown_input_controls_fail_strict_contract(self):
        executor, _ = _executor()
        result = MODULE.execute({"schema_version": 1, "wbs_external_id": "P-100.01", "company_code": "1710", "url": "https://forbidden"}, source_executor=executor, profile=PROFILE)
        self.assertEqual((result["status"], result["resolution_status"]), ("failed", "invalid_input"))
        self.assertEqual(result["validation_issues"][0]["code"], "input_contract_invalid")

    def test_public_contract_and_manifest_are_strict(self):
        skill = MODULE.SKILL_ROOT
        input_schema = json.loads((skill / "references" / "input.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((skill / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(input_schema["additionalProperties"])
        self.assertEqual(set(input_schema["properties"]), {"schema_version", "wbs_external_id", "company_code"})
        self.assertTrue(manifest["validated"])
        self.assertEqual(manifest["allowed_http_methods"], ["GET"])

    def test_odata_redirect_and_response_size_fail_closed(self):
        connection = SimpleNamespace(username="user", password="secret", base_url="https://sap.invalid", client="100", language="EN", verify=True, timeout_seconds=30)
        executor = object.__new__(MODULE.ODataExecutor)
        executor._connection = connection

        class Response:
            status_code = 302

            @staticmethod
            def iter_content(size):
                return iter(())

        executor._session = SimpleNamespace(get=lambda *args, **kwargs: Response())
        with self.assertRaisesRegex(RuntimeError, "redirect_not_allowed"):
            executor._get("https://sap.invalid/read", {"Accept": "application/json"})

        Response.status_code = 200
        Response.iter_content = staticmethod(lambda size: iter((b"x" * (MODULE.MAX_RESPONSE_BYTES + 1),)))
        with self.assertRaisesRegex(RuntimeError, "response_too_large"):
            executor._get("https://sap.invalid/read", {"Accept": "application/json"})


if __name__ == "__main__":
    unittest.main()
