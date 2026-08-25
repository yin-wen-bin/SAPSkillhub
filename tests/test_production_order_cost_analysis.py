from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "skills"
    / "CO"
    / "sap-production-order-cost-analysis"
    / "scripts"
    / "production_order_cost_analysis.py"
)
SPEC = importlib.util.spec_from_file_location("production_order_cost_analysis", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _table_result(object_name: str, rows: list[dict[str, str]], *, complete: bool = True) -> dict[str, object]:
    return {
        "status": "complete" if complete else "partial",
        "validated": True,
        "read_only": True,
        "rows": rows,
        "scope": {"object": object_name},
        "completeness": {"source_complete": complete, "paging_complete": complete},
    }


class ProductionOrderCostAnalysisTests(unittest.TestCase):
    def table_executor(self, task):
        if task["object"] == "AUFK":
            self.assertEqual(task["filters"][0]["value"], "000001001233")
            return _table_result(
                "AUFK",
                [{"AUFNR": "000001001233", "OBJNR": "OR000001001233", "KOKRS": "A000", "BUKRS": "1710", "LOEKZ": "", "PHAS3": "X"}],
            )
        if task["object"] == "ACDOCA":
            return _table_result(
                "ACDOCA",
                [
                    {"RLDNR": "0L", "RBUKRS": "1710", "GJAHR": "2020", "BELNR": "1", "DOCLN": "1", "AUFNR": "000001001233", "RACCT": "400000", "HSL": "80", "RHCUR": "USD"},
                    {"RLDNR": "0L", "RBUKRS": "1710", "GJAHR": "2020", "BELNR": "2", "DOCLN": "1", "AUFNR": "000001001233", "RACCT": "500000", "HSL": "20", "RHCUR": "USD"},
                ],
            )
        self.assertEqual(task["object"], "BKPF")
        return _table_result(
            "BKPF",
            [
                {"BUKRS": "1710", "GJAHR": "2020", "BELNR": "1", "MONAT": "003"},
                {"BUKRS": "1710", "GJAHR": "2020", "BELNR": "2", "MONAT": "004"},
            ],
        )

    @staticmethod
    def cds_executor(task, _module, _profile):
        assert task["analysis_period_from"] == "2020003"
        assert task["analysis_period_to"] == "2020004"
        return {
            "status": "complete",
            "validated": True,
            "read_only": True,
            "source": "C_MfgOrdActlPlnTgtLdgrCost",
            "rows": [
                {
                    "CompanyCode": "1710",
                    "ControllingArea": "A000",
                    "Ledger": "0L",
                    "DisplayCurrency": "USD",
                    "GLAccount": "400000",
                    "CreditPlanCostInDspCrcy": "-5",
                    "DebitPlanCostInDspCrcy": "105",
                    "CrdtTargetCostInDspCrcy": "0",
                    "DebitTargetCostInDspCrcy": "90",
                    "CreditActlCostInDspCrcy": "-10",
                    "DebitActlCostInDspCrcy": "90",
                },
                {
                    "CompanyCode": "1710",
                    "ControllingArea": "A000",
                    "Ledger": "0L",
                    "DisplayCurrency": "USD",
                    "GLAccount": "500000",
                    "CreditPlanCostInDspCrcy": "0",
                    "DebitPlanCostInDspCrcy": "30",
                    "CrdtTargetCostInDspCrcy": "-2",
                    "DebitTargetCostInDspCrcy": "22",
                    "CreditActlCostInDspCrcy": "0",
                    "DebitActlCostInDspCrcy": "20",
                },
            ],
            "completeness": {"source_complete": True, "paging_complete": True},
            "validation_issues": [],
            "metadata_sha256": "a" * 64,
            "query_sha256": "b" * 64,
        }

    def test_complete_result_derives_period_and_aggregates_signed_costs(self):
        result = MODULE.execute(
            {"schema_version": 1, "manufacturing_order": "1001233", "target_cost_variant": 1},
            table_executor=self.table_executor,
            cds_executor=self.cds_executor,
        )
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["validated"])
        self.assertEqual(result["analysis_scope"]["analysis_period_from"], "2020003")
        self.assertEqual(result["analysis_scope"]["analysis_period_to"], "2020004")
        self.assertEqual(result["totals"]["plan_cost_total"], "130")
        self.assertEqual(result["totals"]["target_cost_total"], "110")
        self.assertEqual(result["totals"]["actual_cost_total"], "100")
        self.assertEqual(result["totals"]["actual_target_variance"], "-10")
        self.assertEqual(len(result["cost_element_details"]), 2)
        self.assertTrue(result["completeness"]["evidence_complete"])

    def test_year_scope_is_001_through_016(self):
        def cds(task, _module, _profile):
            self.assertEqual(task["analysis_period_from"], "2020001")
            self.assertEqual(task["analysis_period_to"], "2020016")
            return self.cds_executor({**task, "analysis_period_from": "2020003", "analysis_period_to": "2020004"}, _module, _profile)

        result = MODULE.execute(
            {"schema_version": 1, "manufacturing_order": "1001233", "fiscal_year": "2020", "target_cost_variant": 1},
            table_executor=self.table_executor,
            cds_executor=cds,
        )
        self.assertEqual(result["status"], "complete")

    def test_period_without_year_is_rejected_before_sap(self):
        calls = []
        result = MODULE.execute(
            {"schema_version": 1, "manufacturing_order": "1001233", "period": 3, "target_cost_variant": 1},
            table_executor=lambda task: calls.append(task),
            cds_executor=self.cds_executor,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["validation_issues"][0]["code"], "fiscal_year_required_with_period")
        self.assertEqual(calls, [])

    def test_complete_actual_without_target_cost_is_partial_not_zero(self):
        def failed_cds(_task, _module, _profile):
            return {
                "status": "failed",
                "validated": False,
                "read_only": True,
                "rows": [],
                "completeness": {"source_complete": False, "paging_complete": False},
                "validation_issues": [{"code": "parameterized_production_cost_cds_unavailable", "message": "Unavailable"}],
            }

        result = MODULE.execute(
            {"schema_version": 1, "manufacturing_order": "1001233", "target_cost_variant": 1},
            table_executor=self.table_executor,
            cds_executor=failed_cds,
        )
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["completeness"]["evidence_complete"])
        self.assertEqual(result["totals"], {})
        self.assertIn("parameterized_production_cost_cds_unavailable", {item["code"] for item in result["validation_issues"]})

    def test_manifest_exposes_only_the_fixed_read_only_contract(self):
        skill = MODULE_PATH.parents[1]
        manifest = json.loads((skill / "manifest.json").read_text(encoding="utf-8"))
        input_schema = json.loads((skill / "references/input.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["read_only"])
        self.assertTrue(manifest["validated"])
        self.assertNotIn("connection", input_schema["properties"])
        self.assertNotIn("object", input_schema["properties"])
        self.assertEqual(input_schema["properties"]["target_cost_variant"]["const"], 1)


if __name__ == "__main__":
    unittest.main()
