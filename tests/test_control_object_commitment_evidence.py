from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "CO" / "sap-control-object-commitment-evidence" / "scripts" / "control_object_commitment_evidence.py"
SPEC = importlib.util.spec_from_file_location("control_object_commitment_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _task(object_type="WBS", types=None):
    prefix = "PR" if object_type == "WBS" else "OR"
    return {"schema_version": 1, "resolved_object": {"object_type": object_type, "external_id": "P-100.01" if object_type == "WBS" else "1001233", "internal_id": "00000123", "object_number": prefix + "00000123", "company_code": "1710", "controlling_area": "A000"}, "fiscal_year": "2026", "period_from": 1, "period_to": 3, "commitment_types": types or ["21", "22"]}


def _profile(object_type="WBS", *, validated=True, enabled=True):
    mapping = {"21": {"derivation": "purchase_requisition_reference"}, "22": {"derivation": "purchase_order_reference"}, "24": {"derivation": "explicit_source_value", "source_value": "24"}, "26": {"derivation": "explicit_source_value", "source_value": "26"}}
    return {"schema_version": 1, "profile_version": "test", "profile_status": "validated" if validated else "unvalidated", "sources": {object_type: {"enabled": enabled, "source_id": "test", "metadata_sha256": "a" * 64, "max_rows": 10000, "value_type_mapping": mapping}}}


def _row(key="1", **overrides):
    row = {"source_key": key, "object_number": "PR00000123", "fiscal_year": "2026", "accounting_period": 2, "commitment_type": "21", "cost_element": "400000", "purchasing_requisition": "10000001", "purchasing_requisition_item": "10", "purchasing_document": "", "purchasing_document_item": "", "amount": "12.50", "currency": "USD", "currency_role": "10"}
    row.update(overrides)
    return row


def _source(rows, **overrides):
    result = {"metadata_sha256": "a" * 64, "rows": rows, "total_rows": len(rows), "source_complete": True, "paging_complete": True, "scope_complete": True}
    result.update(overrides)
    return lambda source, normalized: result


class CommitmentEvidenceTests(unittest.TestCase):
    def test_disabled_profiles_fail_closed_per_object_mode(self):
        live = json.loads(MODULE.PROFILE_PATH.read_text(encoding="utf-8"))
        wbs = MODULE.execute(_task(), profile=live)
        order = MODULE.execute(_task("INTERNAL_ORDER"), profile=live)
        self.assertEqual(wbs["validation_issues"][0]["code"], "wbs_commitment_source_unavailable")
        self.assertEqual(order["validation_issues"][0]["code"], "internal_order_commitment_source_unavailable")
        self.assertIsNone(wbs["commitment_totals"])
        self.assertEqual(wbs["commitment_details"], [])

    def test_signed_decimal_and_multi_currency_groups_are_exact(self):
        rows = [_row(amount="10.25"), _row("2", commitment_type="22", purchasing_requisition="", purchasing_document="4500000010", amount="3.25-"), _row("3", amount="2", currency="EUR")]
        result = MODULE.execute(_task(), profile=_profile(), source_executor=_source(rows))
        self.assertEqual((result["status"], result["validated"]), ("complete", True))
        groups = {(item["commitment_type"], item["currency"]): item["amount"] for item in result["commitment_totals"]["groups"]}
        self.assertEqual(groups, {("21", "EUR"): "2", ("21", "USD"): "10.25", ("22", "USD"): "-3.25"})

    def test_invalid_amount_or_duplicate_key_suppresses_all_aggregation(self):
        rows = [_row(amount="NaN"), _row()]
        result = MODULE.execute(_task(), profile=_profile(), source_executor=_source(rows))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["commitment_details"], [])
        self.assertIsNone(result["commitment_totals"])
        self.assertFalse(result["completeness"]["evidence_complete"])

    def test_incomplete_paging_or_scope_suppresses_all_aggregation(self):
        result = MODULE.execute(_task(), profile=_profile(), source_executor=_source([_row()], paging_complete=False))
        self.assertEqual(result["validation_issues"][0]["code"], "commitment_source_incomplete")
        self.assertEqual(result["commitment_details"], [])
        self.assertIsNone(result["commitment_totals"])

    def test_authoritative_empty_with_currency_context_produces_explicit_zero(self):
        result = MODULE.execute(_task(types=["21", "24"]), profile=_profile(), source_executor=_source([], authoritative_empty=True, zero_context={"currency": "USD", "currency_role": "10"}))
        self.assertEqual(result["status"], "complete")
        self.assertTrue(all(item["synthetic_zero"] for item in result["commitment_details"]))
        self.assertEqual({item["amount"] for item in result["commitment_totals"]["groups"]}, {"0"})

    def test_empty_without_authoritative_currency_context_is_not_zero(self):
        result = MODULE.execute(_task(), profile=_profile(), source_executor=_source([]))
        self.assertEqual(result["validation_issues"][0]["code"], "zero_scope_unproven")
        self.assertIsNone(result["commitment_totals"])

    def test_complete_source_must_prove_every_requested_commitment_type(self):
        result = MODULE.execute(_task(types=["21", "22"]), profile=_profile(), source_executor=_source([_row()]))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["validation_issues"][0]["code"], "commitment_type_scope_incomplete")
        self.assertEqual(result["commitment_details"], [])

    def test_unmapped_type_and_unknown_input_are_rejected(self):
        profile = _profile()
        del profile["sources"]["WBS"]["value_type_mapping"]["26"]
        unsupported = MODULE.execute(_task(types=["26"]), profile=profile, source_executor=_source([]))
        self.assertEqual(unsupported["validation_issues"][0]["code"], "commitment_type_unsupported")
        invalid = _task()
        invalid["source"] = "COOI"
        failed = MODULE.execute(invalid, profile=_profile(), source_executor=_source([]))
        self.assertEqual(failed["status"], "failed")

    def test_xxe_is_rejected_before_xml_parsing(self):
        payload = b'<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]><Envelope><Item><Amount>&leak;</Amount></Item></Envelope>'
        with self.assertRaisesRegex(ValueError, "xml_external_entity_forbidden"):
            MODULE.parse_soap_response(payload, {"item_element": "Item", "amount": "Amount"})

    def test_object_number_must_match_internal_id(self):
        task = _task()
        task["resolved_object"]["object_number"] = "PR99999999"
        result = MODULE.execute(task, profile=_profile(), source_executor=_source([]))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["validation_issues"][0]["code"], "resolved_object_relationship_invalid")

    def test_wbs_requires_external_identifier_for_standard_service(self):
        task = _task()
        del task["resolved_object"]["external_id"]
        result = MODULE.execute(task, profile=_profile(), source_executor=_source([]))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["validation_issues"][0]["code"], "resolved_object_external_id_missing")

    def test_soap_action_redirect_csrf_and_response_bounds_fail_closed(self):
        connection = SimpleNamespace(username="user", password="secret", base_url="https://sap.invalid", client="100", verify=True, timeout_seconds=30)
        executor = object.__new__(MODULE.SoapExecutor)
        executor._connection = connection
        normalized = MODULE._validate_task(_task())
        source = {"endpoint_path": "/sap/bc/srt/read", "operation": "Read", "soap_action": "urn:read", "approved_read_action": "urn:other"}
        with self.assertRaisesRegex(RuntimeError, "soap_action_not_allowed"):
            executor(source, normalized)

        class Response:
            status_code = 302

            @staticmethod
            def iter_content(size):
                return iter(())

        executor._session = SimpleNamespace(post=lambda *args, **kwargs: Response())
        source["approved_read_action"] = "urn:read"
        with self.assertRaisesRegex(RuntimeError, "redirect_not_allowed"):
            executor(source, normalized)

        Response.status_code = 403
        with self.assertRaisesRegex(RuntimeError, "authorization_denied"):
            executor(source, normalized)

        Response.status_code = 200
        Response.iter_content = staticmethod(lambda size: iter((b"x" * (MODULE.MAX_RESPONSE_BYTES + 1),)))
        with self.assertRaisesRegex(RuntimeError, "response_too_large"):
            executor(source, normalized)

    def test_soap_uses_external_wbs_id_and_follows_bounded_continuation(self):
        connection = SimpleNamespace(username="user", password="secret", base_url="https://sap.invalid", client="100", verify=True, timeout_seconds=30)
        executor = object.__new__(MODULE.SoapExecutor)
        executor._connection = connection
        payloads = []

        def page(item_key, more, token):
            return (
                "<Envelope><Body><Item><SourceKey>" + item_key + "</SourceKey></Item>"
                "<More>" + more + "</More><Next>" + token + "</Next></Body></Envelope>"
            ).encode()

        responses = [
            SimpleNamespace(status_code=200, iter_content=lambda size: iter((page("A", "true", "TOKEN-1"),))),
            SimpleNamespace(status_code=200, iter_content=lambda size: iter((page("B", "false", ""),))),
        ]

        def post(*args, **kwargs):
            payloads.append(kwargs["data"])
            return responses.pop(0)

        executor._session = SimpleNamespace(post=post)
        source = {
            "endpoint_path": "/sap/bc/srt/read",
            "operation": "Read",
            "soap_action": "urn:read",
            "approved_read_action": "urn:read",
            "page_size": 10,
            "max_rows": 100,
            "field_mapping": {"item_element": "Item", "source_key": "SourceKey"},
            "pagination": {
                "mode": "continuation",
                "page_size_element": "MaximumNumberOfRecords",
                "request_token_element": "LastReturnedObjectID",
                "response_token_element": "Next",
                "more_data_element": "More",
            },
        }
        result = executor(source, MODULE._validate_task(_task()))

        self.assertEqual([row["source_key"] for row in result["rows"]], ["A", "B"])
        self.assertIn(b"P-100.01", payloads[0])
        self.assertNotIn(b"00000123</ProjectElementID>", payloads[0])
        self.assertIn(b"TOKEN-1", payloads[1])

    def test_public_contract_is_nullable_and_manifest_unvalidated(self):
        skill = MODULE.SKILL_ROOT
        output_schema = json.loads((skill / "references" / "output.schema.json").read_text(encoding="utf-8"))
        input_schema = json.loads((skill / "references" / "input.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((skill / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(input_schema["additionalProperties"])
        self.assertEqual(output_schema["properties"]["commitment_totals"]["type"], ["object", "null"])
        self.assertFalse(manifest["validated"])


if __name__ == "__main__":
    unittest.main()
