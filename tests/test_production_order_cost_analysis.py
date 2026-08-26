from __future__ import annotations

import importlib.util
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from types import SimpleNamespace
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


def _cost_row(gl_account: str = "400000", **overrides: str) -> dict[str, str]:
    row = {
        "OrderID": "000001001233",
        "CompanyCode": "1710",
        "ControllingArea": "A000",
        "Ledger": "0L",
        "DisplayCurrency": "USD",
        "GLAccount": gl_account,
        "CreditPlanCostInDspCrcy": "5-",
        "DebitPlanCostInDspCrcy": "105",
        "CrdtTargetCostInDspCrcy": "0",
        "DebitTargetCostInDspCrcy": "90",
        "CreditActlCostInDspCrcy": "10-",
        "DebitActlCostInDspCrcy": "90",
    }
    row.update(overrides)
    return row


def _cds_result(rows: list[dict[str, str]], *, complete: bool = True) -> dict[str, object]:
    return {
        "status": "complete" if complete else "partial",
        "validated": True,
        "read_only": True,
        "source": MODULE.CDS_SOURCE,
        "rows": rows if complete else [],
        "completeness": {
            "source_complete": complete,
            "paging_complete": complete,
            "total_rows": len(rows),
            "returned_rows": len(rows),
            "requested_row_limit": MODULE.PREVIEW_ROW_LIMIT,
            "truncated": not complete,
        },
        "validation_issues": [] if complete else [{"code": "row_limit_reached", "message": "Partial"}],
        "metadata_sha256": "a" * 64,
        "query_sha256": "b" * 64,
    }


LIVE_DDL = """
define view entity I_MfgOrderActlPlanTgtLdgrCost
  with parameters
    P_FromFiscalYearPeriod : fins_fyearperiod,
    P_ToFiscalYearPeriod : fins_fyearperiod,
    P_Ledger : fins_ledger,
    P_CurrencyRole : fac_crcyrole,
    P_TargetCostVariant : fis_awvrs
as select from source {
  key OrderID,
  key GLAccount,
  cast( :P_Ledger as fins_ledger ) as Ledger,
  ControllingArea,
  CompanyCode,
  DisplayCurrency,
  cast( plan_credit as fis_cr_plancost_in_dspcrcy ) as CreditPlanCostInDspCrcy,
  cast( plan_debit as fis_dr_plancost_in_dspcrcy ) as DebitPlanCostInDspCrcy,
  cast( target_credit as fis_cr_tgtcost_in_dspcrcy ) as CrdtTargetCostInDspCrcy,
  cast( target_debit as fis_dr_tgtcost_in_dspcrcy ) as DebitTargetCostInDspCrcy,
  cast( actual_credit as fis_cr_actlcost_in_dspcrcy ) as CreditActlCostInDspCrcy,
  cast( actual_debit as fis_dr_actlcost_in_dspcrcy ) as DebitActlCostInDspCrcy
}
"""


@dataclass(frozen=True)
class FakeConnection:
    timeout_seconds: int = 30


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
        return _cds_result(
            [
                _cost_row(),
                _cost_row(
                    "500000",
                    CreditPlanCostInDspCrcy="0",
                    DebitPlanCostInDspCrcy="30",
                    CrdtTargetCostInDspCrcy="-2",
                    DebitTargetCostInDspCrcy="22",
                    CreditActlCostInDspCrcy="0",
                    DebitActlCostInDspCrcy="20",
                ),
            ]
        )

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
        self.assertEqual(MODULE._decimal("1233.68-"), MODULE.decimal.Decimal("-1233.68"))
        self.assertIsNone(MODULE._decimal(""))

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

    def test_live_cds_query_is_multiline_post_only_and_has_exact_contract(self):
        captured = {}

        class Preview:
            columns = tuple(field.upper() for field in MODULE.CDS_FIELDS)
            rows = tuple(_cost_row().items())
            total_rows = 1

        Preview.rows = (_cost_row(),)

        class Client:
            def __init__(self, connection):
                captured["timeout"] = connection.timeout_seconds

            def metadata(self, source_type, source):
                captured["metadata"] = (source_type, source)
                return LIVE_DDL, "/redacted"

            def preview(self, sql, row_number, *, prefer_post=False):
                captured["sql"] = sql
                captured["row_number"] = row_number
                captured["prefer_post"] = prefer_post
                return Preview()

        class ExportError(Exception):
            def __init__(self, code, message):
                self.code = code
                self.message = message

        module = SimpleNamespace(
            AdtClient=Client,
            ExportError=ExportError,
            _validate_compiled_select=lambda sql: captured.setdefault("validated_sql", sql),
        )
        result = MODULE._live_cds_executor(
            {
                "analysis_period_from": "2020011",
                "analysis_period_to": "2020011",
                "adt_order": "000001001233",
            },
            module,
            SimpleNamespace(connection=FakeConnection()),
        )
        sql = captured["sql"]
        self.assertEqual(result["status"], "complete")
        self.assertEqual(captured["metadata"], ("cds", MODULE.CDS_SOURCE))
        self.assertEqual(captured["timeout"], 120)
        self.assertTrue(captured["prefer_post"])
        self.assertEqual(captured["row_number"], 10001)
        self.assertNotIn("ORDER BY", sql.upper())
        self.assertNotIn("C_MfgOrdActlPlnTgtLdgrCost", sql)
        self.assertTrue(all(len(line) <= 120 for line in sql.splitlines()))
        self.assertEqual(
            [line.strip().rstrip(",") for line in sql.splitlines()[1 : 1 + len(MODULE.CDS_FIELDS)]],
            list(MODULE.CDS_FIELDS),
        )

    def test_live_cds_total_row_contract_fails_closed(self):
        class ExportError(Exception):
            def __init__(self, code, message):
                self.code = code
                self.message = message

        for total_rows, response_count, expected_code in (
            (None, 1, "source_total_unavailable"),
            (2, 1, "row_count_mismatch"),
            (10001, 10001, "row_limit_reached"),
        ):
            with self.subTest(total_rows=total_rows, response_count=response_count):
                preview = SimpleNamespace(
                    columns=tuple(field.upper() for field in MODULE.CDS_FIELDS),
                    rows=tuple(_cost_row(str(400000 + index)) for index in range(response_count)),
                    total_rows=total_rows,
                )

                class Client:
                    def __init__(self, _connection):
                        pass

                    def metadata(self, _source_type, _source):
                        return LIVE_DDL, "/redacted"

                    def preview(self, _sql, _row_number, *, prefer_post=False):
                        self.prefer_post = prefer_post
                        return preview

                module = SimpleNamespace(
                    AdtClient=Client,
                    ExportError=ExportError,
                    _validate_compiled_select=lambda _sql: None,
                )
                result = MODULE._live_cds_executor(
                    {"analysis_period_from": "2020011", "analysis_period_to": "2020011", "adt_order": "000001001233"},
                    module,
                    SimpleNamespace(connection=FakeConnection()),
                )
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["rows"], [])
                self.assertIn(expected_code, {item["code"] for item in result["validation_issues"]})

    def test_invalid_or_conflicting_cost_rows_never_produce_totals(self):
        cases = (
            (_cost_row(CreditPlanCostInDspCrcy=""), "cost_amount_invalid"),
            (_cost_row(CompanyCode="9999"), "production_cost_relationship_conflict"),
            (_cost_row(OrderID="000009999999"), "production_cost_order_mismatch"),
            (_cost_row(Ledger="2L"), "cost_ledger_mismatch"),
        )
        for row, code in cases:
            with self.subTest(code=code):
                result = MODULE.execute(
                    {"schema_version": 1, "manufacturing_order": "1001233", "fiscal_year": "2020", "period": 11, "target_cost_variant": 1},
                    table_executor=self.table_executor,
                    cds_executor=lambda _task, _module, _profile, row=row: _cds_result([row]),
                )
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["cost_element_details"], [])
                self.assertEqual(result["totals"], {})
                self.assertTrue(result["completeness"]["source_complete"])
                self.assertFalse(result["completeness"]["evidence_complete"])
                self.assertIn(code, {item["code"] for item in result["validation_issues"]})

    def test_empty_complete_cost_source_is_partial_but_source_complete(self):
        result = MODULE.execute(
            {"schema_version": 1, "manufacturing_order": "1001233", "fiscal_year": "2020", "period": 11, "target_cost_variant": 1},
            table_executor=self.table_executor,
            cds_executor=lambda _task, _module, _profile: _cds_result([]),
        )
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["completeness"]["source_complete"])
        self.assertFalse(result["completeness"]["evidence_complete"])
        self.assertEqual(result["completeness"]["total_rows"], 0)
        self.assertEqual(result["totals"], {})
        self.assertIn("production_cost_evidence_empty", {item["code"] for item in result["validation_issues"]})

    def test_live_contract_rejects_incompatible_parameter_type(self):
        broken = LIVE_DDL.replace("P_Ledger : fins_ledger", "P_Ledger : char10")
        self.assertEqual(MODULE._validate_cost_cds_contract(LIVE_DDL), [])
        self.assertIn("P_Ledger", MODULE._validate_cost_cds_contract(broken))

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
