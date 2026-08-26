from __future__ import annotations

import argparse
from dataclasses import replace
import decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import uuid
from datetime import datetime, timezone


SCHEMA_VERSION = 1
SKILL_ID = "sap-production-order-cost-analysis"
MAX_COST_ROWS = 10_000
CDS_SOURCE = "I_MfgOrderActlPlanTgtLdgrCost"
PREVIEW_ROW_LIMIT = MAX_COST_ROWS + 1
CDS_PARAMETERS = (
    "P_FromFiscalYearPeriod",
    "P_ToFiscalYearPeriod",
    "P_Ledger",
    "P_CurrencyRole",
    "P_TargetCostVariant",
)
CDS_FIELDS = (
    "OrderID",
    "GLAccount",
    "Ledger",
    "ControllingArea",
    "CompanyCode",
    "DisplayCurrency",
    "CreditPlanCostInDspCrcy",
    "DebitPlanCostInDspCrcy",
    "CrdtTargetCostInDspCrcy",
    "DebitTargetCostInDspCrcy",
    "CreditActlCostInDspCrcy",
    "DebitActlCostInDspCrcy",
)
CDS_PARAMETER_TYPES = {
    "P_FromFiscalYearPeriod": "fins_fyearperiod",
    "P_ToFiscalYearPeriod": "fins_fyearperiod",
    "P_Ledger": "fins_ledger",
    "P_CurrencyRole": "fac_crcyrole",
    "P_TargetCostVariant": "fis_awvrs",
}
CDS_AMOUNT_TYPES = {
    "CreditPlanCostInDspCrcy": "fis_cr_plancost_in_dspcrcy",
    "DebitPlanCostInDspCrcy": "fis_dr_plancost_in_dspcrcy",
    "CrdtTargetCostInDspCrcy": "fis_cr_tgtcost_in_dspcrcy",
    "DebitTargetCostInDspCrcy": "fis_dr_tgtcost_in_dspcrcy",
    "CreditActlCostInDspCrcy": "fis_cr_actlcost_in_dspcrcy",
    "DebitActlCostInDspCrcy": "fis_dr_actlcost_in_dspcrcy",
}


JsonObject = dict[str, Any]
TableExecutor = Callable[[JsonObject], JsonObject]
CdsExecutor = Callable[[JsonObject, Any, Any], JsonObject]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _decimal(value: Any) -> decimal.Decimal | None:
    if value in {None, ""}:
        return None
    rendered = str(value).strip()
    if rendered.endswith("-") and rendered.count("-") == 1:
        rendered = "-" + rendered[:-1]
    elif rendered.endswith("+") and rendered.count("+") == 1:
        rendered = rendered[:-1]
    try:
        parsed = decimal.Decimal(rendered)
    except (decimal.InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _exact(value: decimal.Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _validate_task(task: JsonObject) -> JsonObject:
    if set(task) - {
        "schema_version",
        "manufacturing_order",
        "fiscal_year",
        "period",
        "analysis_period_from",
        "analysis_period_to",
        "target_cost_variant",
    }:
        raise ValueError("input_contains_unsupported_fields")
    if task.get("schema_version") != 1:
        raise ValueError("schema_version_invalid")
    order = str(task.get("manufacturing_order") or "").strip().upper()
    if not re.fullmatch(r"[0-9A-Z_-]{1,12}", order):
        raise ValueError("manufacturing_order_invalid")
    fiscal_year = str(task.get("fiscal_year") or "").strip()
    if fiscal_year and not re.fullmatch(r"[0-9]{4}", fiscal_year):
        raise ValueError("fiscal_year_invalid")
    period_value = task.get("period")
    if period_value in {None, ""}:
        period = None
    elif isinstance(period_value, bool):
        raise ValueError("period_invalid")
    else:
        try:
            period = int(period_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("period_invalid") from exc
        if str(period) != str(period_value).lstrip("0") and not (
            isinstance(period_value, str) and period_value.isdigit()
        ):
            raise ValueError("period_invalid")
        if not 1 <= period <= 16:
            raise ValueError("period_invalid")
    if period is not None and not fiscal_year:
        raise ValueError("fiscal_year_required_with_period")
    if task.get("target_cost_variant") != 1:
        raise ValueError("target_cost_variant_must_be_1")
    analysis_from = str(task.get("analysis_period_from") or "").strip()
    analysis_to = str(task.get("analysis_period_to") or "").strip()
    if bool(analysis_from) != bool(analysis_to):
        raise ValueError("analysis_period_range_incomplete")
    for value in (analysis_from, analysis_to):
        if value and (
            not re.fullmatch(r"[0-9]{7}", value)
            or not 1 <= int(value[-3:]) <= 16
        ):
            raise ValueError("analysis_period_range_invalid")
    if analysis_from and analysis_from > analysis_to:
        raise ValueError("analysis_period_range_invalid")
    if analysis_from and (fiscal_year or period is not None):
        raise ValueError("analysis_period_scope_conflict")
    return {
        "schema_version": 1,
        "manufacturing_order": order,
        "adt_order": order.zfill(12) if order.isdigit() else order,
        "fiscal_year": fiscal_year or None,
        "period": period,
        "analysis_period_from": analysis_from or None,
        "analysis_period_to": analysis_to or None,
        "target_cost_variant": 1,
    }


def _table_task(
    object_name: str,
    fields: list[str],
    filters: list[JsonObject],
    order_by: list[str],
    max_rows: int,
) -> JsonObject:
    return {
        "schema_version": 1,
        "source_type": "table",
        "object": object_name,
        "fields": fields,
        "filters": filters,
        "order_by": order_by,
        "max_rows": max_rows,
    }


def _complete(value: JsonObject) -> bool:
    completeness = value.get("completeness") if isinstance(value.get("completeness"), dict) else {}
    return bool(
        value.get("status") == "complete"
        and value.get("validated") is True
        and value.get("read_only") is True
        and completeness.get("source_complete") is True
        and completeness.get("paging_complete") is True
    )


def _period_scope(task: JsonObject, posting_headers: list[JsonObject]) -> tuple[str | None, str | None, list[JsonObject]]:
    issues: list[JsonObject] = []
    if task.get("analysis_period_from") and task.get("analysis_period_to"):
        return str(task["analysis_period_from"]), str(task["analysis_period_to"]), issues
    year = task.get("fiscal_year")
    period = task.get("period")
    if year and period is not None:
        token = f"{year}{period:03d}"
        return token, token, issues
    if year:
        return f"{year}001", f"{year}016", issues
    observed: list[tuple[int, int]] = []
    for row in posting_headers:
        row_year = str(row.get("GJAHR") or "").strip()
        row_period = str(row.get("MONAT") or "").strip()
        if not row_year.isdigit() or len(row_year) != 4 or not row_period.isdigit():
            issues.append({"code": "actual_cost_period_invalid", "message": "An actual-cost row lacks a valid fiscal year or period."})
            continue
        parsed_period = int(row_period)
        if not 1 <= parsed_period <= 16:
            issues.append({"code": "actual_cost_period_invalid", "message": "An actual-cost row has a period outside 001-016."})
            continue
        observed.append((int(row_year), parsed_period))
    if not observed:
        issues.append({"code": "analysis_period_not_derivable", "message": "No complete actual posting period was available to derive the analysis scope."})
        return None, None, issues
    low, high = min(observed), max(observed)
    return f"{low[0]:04d}{low[1]:03d}", f"{high[0]:04d}{high[1]:03d}", issues


def _posting_period_headers(
    actual_rows: list[JsonObject],
    *,
    table_executor: TableExecutor,
) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject]]:
    """Read BKPF posting periods for the exact ACDOCA document keys."""

    expected = {
        (
            str(row.get("RBUKRS") or "").strip(),
            str(row.get("GJAHR") or "").strip(),
            str(row.get("BELNR") or "").strip(),
        )
        for row in actual_rows
    }
    expected.discard(("", "", ""))
    if not expected:
        return [], [], []
    headers: list[JsonObject] = []
    artifacts: list[JsonObject] = []
    issues: list[JsonObject] = []
    by_company_year: dict[tuple[str, str], list[str]] = {}
    for company, year, document in sorted(expected):
        by_company_year.setdefault((company, year), []).append(document)
    for (company, year), documents in by_company_year.items():
        for offset in range(0, len(documents), 100):
            chunk = documents[offset : offset + 100]
            result = table_executor(
                _table_task(
                    "BKPF",
                    ["MANDT", "BUKRS", "BELNR", "GJAHR", "MONAT"],
                    [
                        {"field": "BUKRS", "operator": "eq", "value": company},
                        {"field": "GJAHR", "operator": "eq", "value": year},
                        {"field": "BELNR", "operator": "in", "values": chunk},
                    ],
                    ["MANDT", "BUKRS", "BELNR", "GJAHR"],
                    len(chunk) + 1,
                )
            )
            artifacts.append({"object": "BKPF", "scope": result.get("scope") or {}})
            if not _complete(result):
                issues.append({"code": "posting_period_evidence_incomplete", "message": "A bounded BKPF posting-period query is incomplete."})
                continue
            headers.extend(dict(row) for row in result.get("rows") or [] if isinstance(row, dict))
    returned = {
        (
            str(row.get("BUKRS") or "").strip(),
            str(row.get("GJAHR") or "").strip(),
            str(row.get("BELNR") or "").strip(),
        )
        for row in headers
    }
    if expected - returned:
        issues.append({"code": "posting_period_relationship_incomplete", "message": "BKPF did not cover every exact ACDOCA accounting-document key."})
    return headers, artifacts, issues


def _declared_type(ddl: str, name: str, *, cast_alias: bool = False) -> str | None:
    if cast_alias:
        pattern = rf"cast\s*\([^)]*?\bas\s+([A-Za-z0-9_/]+)\s*\)\s+as\s+{re.escape(name)}\b"
    else:
        pattern = rf"\b{re.escape(name)}\s*:\s*([A-Za-z0-9_/]+)"
    match = re.search(pattern, ddl, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).lower() if match else None


def _validate_cost_cds_contract(ddl: str) -> list[str]:
    mismatches: list[str] = []
    for name, expected in CDS_PARAMETER_TYPES.items():
        if _declared_type(ddl, name) != expected:
            mismatches.append(name)
    for field in CDS_FIELDS:
        if not re.search(rf"\b{re.escape(field)}\b", ddl, flags=re.IGNORECASE):
            mismatches.append(field)
    for name, expected in CDS_AMOUNT_TYPES.items():
        if _declared_type(ddl, name, cast_alias=True) != expected:
            mismatches.append(name)
    return sorted(set(mismatches))


def _cost_sql(task: JsonObject) -> str:
    parameters = {
        "P_FromFiscalYearPeriod": task["analysis_period_from"],
        "P_ToFiscalYearPeriod": task["analysis_period_to"],
        "P_Ledger": "0L",
        "P_CurrencyRole": "10",
        "P_TargetCostVariant": "001",
    }
    lines = ["SELECT"]
    lines.extend(
        f"  {field}{',' if index < len(CDS_FIELDS) - 1 else ''}"
        for index, field in enumerate(CDS_FIELDS)
    )
    lines.append(f"FROM {CDS_SOURCE}(")
    for index, name in enumerate(CDS_PARAMETERS):
        value = str(parameters[name]).replace("'", "''")
        lines.append(f"  {name} = '{value}'{',' if index < len(CDS_PARAMETERS) - 1 else ''}")
    lines.append(")")
    order = str(task["adt_order"]).replace("'", "''")
    lines.append(f"WHERE OrderID = '{order}'")
    if any(len(line) > 120 for line in lines):
        raise RuntimeError("generated_query_line_too_long")
    return "\n".join(lines)


def _safe_cds_failure(code: str) -> tuple[str, str]:
    messages = {
        "query_line_truncated": "SAP rejected a query line because it exceeded the supported length.",
        "query_syntax_invalid": "SAP rejected the structured query syntax.",
        "query_column_invalid": "SAP could not resolve a selected query column.",
        "query_execution_failed": "SAP rejected the parameterized production-cost query.",
        "timeout": "The SAP ADT production-cost request timed out.",
        "authorization_denied": "SAP denied the production-cost ADT request.",
        "authentication_failed": "SAP ADT authentication failed.",
        "tls_validation_failed": "SAP ADT TLS certificate validation failed.",
        "adt_service_unavailable": "SAP ADT Data Preview is unavailable.",
        "metadata_unavailable": "SAP ADT metadata is unavailable.",
        "released_cost_cds_contract_mismatch": "The live production-cost CDS contract does not match the validated interface.",
        "released_cost_cds_column_mismatch": "The production-cost query returned an unexpected column contract.",
    }
    if code not in messages:
        code = "query_execution_failed"
    return code, messages[code]


def _live_cds_executor(task: JsonObject, adt_module: Any, profile: Any) -> JsonObject:
    connection = replace(
        profile.connection,
        timeout_seconds=max(120, profile.connection.timeout_seconds),
    )
    client = adt_module.AdtClient(connection)
    metadata_hash: str | None = None
    query_hash: str | None = None
    try:
        ddl, _path = client.metadata("cds", CDS_SOURCE)
        metadata_hash = _sha256(ddl.encode("utf-8"))
        mismatches = _validate_cost_cds_contract(ddl)
        if mismatches:
            raise adt_module.ExportError(
                "released_cost_cds_contract_mismatch",
                "The live production-cost CDS contract does not match the validated interface.",
            )
        sql = _cost_sql(task)
        adt_module._validate_compiled_select(sql)
        query_hash = _sha256(sql.encode("utf-8"))
        preview = client.preview(sql, PREVIEW_ROW_LIMIT, prefer_post=True)
        expected = tuple(field.upper() for field in CDS_FIELDS)
        returned = tuple(str(field).upper() for field in preview.columns)
        if returned != expected:
            raise adt_module.ExportError(
                "released_cost_cds_column_mismatch",
                "The production-cost query returned an unexpected column contract.",
            )
        normalized_rows = []
        for row in preview.rows:
            upper_row = {str(key).upper(): value for key, value in row.items()}
            normalized_rows.append(
                {field: upper_row.get(field.upper(), "") for field in CDS_FIELDS}
            )
        total_rows = preview.total_rows
        returned_rows = len(normalized_rows)
        issues: list[JsonObject] = []
        if total_rows is None:
            issues.append({"code": "source_total_unavailable", "message": "SAP did not provide a usable total row count."})
        else:
            expected_returned = min(total_rows, PREVIEW_ROW_LIMIT)
            if returned_rows != expected_returned:
                issues.append({"code": "row_count_mismatch", "message": "The SAP total row count does not match the returned row count."})
            if total_rows > MAX_COST_ROWS:
                issues.append({"code": "row_limit_reached", "message": "The production-cost CDS exceeded the bounded result limit."})
        source_complete = not issues
        return {
            "status": "complete" if source_complete else "partial",
            "validated": True,
            "read_only": True,
            "source": CDS_SOURCE,
            "rows": normalized_rows if source_complete else [],
            "completeness": {
                "source_complete": source_complete,
                "paging_complete": source_complete,
                "total_rows": total_rows,
                "returned_rows": returned_rows,
                "requested_row_limit": PREVIEW_ROW_LIMIT,
                "truncated": total_rows is not None and total_rows > MAX_COST_ROWS,
            },
            "metadata_sha256": metadata_hash,
            "query_sha256": query_hash,
            "validation_issues": issues,
        }
    except Exception as exc:
        code, message = _safe_cds_failure(str(getattr(exc, "code", "query_execution_failed")))
        return {
            "status": "failed",
            "validated": False,
            "read_only": True,
            "source": CDS_SOURCE,
            "rows": [],
            "completeness": {
                "source_complete": False,
                "paging_complete": False,
                "total_rows": None,
                "returned_rows": 0,
                "requested_row_limit": PREVIEW_ROW_LIMIT,
                "truncated": False,
            },
            **({"metadata_sha256": metadata_hash} if metadata_hash else {}),
            **({"query_sha256": query_hash} if query_hash else {}),
            "validation_issues": [{"code": code, "message": message}],
        }


def _aggregate_cds_rows(
    rows: list[JsonObject],
    scope: JsonObject,
    order_row: JsonObject,
    adt_order: str,
    source: str,
) -> tuple[list[JsonObject], JsonObject, list[JsonObject]]:
    groups: dict[tuple[str, str, str, str, str], dict[str, decimal.Decimal]] = {}
    issues: list[JsonObject] = []
    expected_company = str(order_row.get("BUKRS") or "").strip()
    expected_controlling_area = str(order_row.get("KOKRS") or "").strip()
    currencies: set[str] = set()
    for row in rows:
        if str(row.get("OrderID") or "").strip() != adt_order:
            issues.append({"code": "production_cost_order_mismatch", "message": "A cost row belongs to a different manufacturing order."})
        if (
            str(row.get("CompanyCode") or "").strip() != expected_company
            or str(row.get("ControllingArea") or "").strip() != expected_controlling_area
        ):
            issues.append({"code": "production_cost_relationship_conflict", "message": "A cost row conflicts with the AUFK company code or controlling area."})
        if str(row.get("Ledger") or "").strip() != "0L":
            issues.append({"code": "cost_ledger_mismatch", "message": "A cost row is outside fixed ledger 0L."})
        currency = str(row.get("DisplayCurrency") or "").strip()
        if not currency:
            issues.append({"code": "cost_currency_invalid", "message": "A cost row lacks display currency."})
        else:
            currencies.add(currency)
        key = tuple(
            str(row.get(field) or "").strip()
            for field in ("CompanyCode", "ControllingArea", "Ledger", "DisplayCurrency", "GLAccount")
        )
        if not all(key):
            issues.append({"code": "cost_element_business_key_incomplete", "message": "A CDS cost row lacks company, controlling area, ledger, currency, or G/L account."})
            continue
        values: list[decimal.Decimal] = []
        for field in (
            "CreditPlanCostInDspCrcy",
            "DebitPlanCostInDspCrcy",
            "CrdtTargetCostInDspCrcy",
            "DebitTargetCostInDspCrcy",
            "CreditActlCostInDspCrcy",
            "DebitActlCostInDspCrcy",
        ):
            value = _decimal(row.get(field))
            if value is None:
                issues.append({"code": "cost_amount_invalid", "message": f"A CDS cost row contains an invalid {field} amount."})
            else:
                values.append(value)
        if len(values) != 6:
            continue
        bucket = groups.setdefault(
            key,
            {"plan": decimal.Decimal(0), "target": decimal.Decimal(0), "actual": decimal.Decimal(0)},
        )
        bucket["plan"] += values[0] + values[1]
        bucket["target"] += values[2] + values[3]
        bucket["actual"] += values[4] + values[5]
    if len(currencies) > 1:
        issues.append({"code": "cost_scope_not_comparable", "message": "Cost rows span multiple display currencies."})
    if issues:
        unique = {item["code"]: item for item in issues}
        return [], {}, [unique[code] for code in sorted(unique)]
    details: list[JsonObject] = []
    for key, values in sorted(groups.items()):
        company_code, controlling_area, ledger, currency, cost_element = key
        variance = values["actual"] - values["target"]
        details.append(
            {
                "company_code": company_code,
                "controlling_area": controlling_area,
                "ledger": ledger,
                "currency_role": "10",
                "cost_element": cost_element,
                "plan_cost": _exact(values["plan"]),
                "target_cost": _exact(values["target"]),
                "actual_cost": _exact(values["actual"]),
                "actual_target_variance": _exact(variance),
                "currency": currency,
                "analysis_period_from": scope["analysis_period_from"],
                "analysis_period_to": scope["analysis_period_to"],
                "evidence_source": source,
            }
        )
    plan = sum((decimal.Decimal(item["plan_cost"]) for item in details), decimal.Decimal(0))
    target = sum((decimal.Decimal(item["target_cost"]) for item in details), decimal.Decimal(0))
    actual = sum((decimal.Decimal(item["actual_cost"]) for item in details), decimal.Decimal(0))
    totals = {
        "plan_cost_total": _exact(plan),
        "target_cost_total": _exact(target),
        "actual_cost_total": _exact(actual),
        "actual_target_variance": _exact(actual - target),
        "currency": next(iter(currencies), None),
    }
    return details, totals, issues


def execute(
    task: JsonObject,
    *,
    table_executor: TableExecutor,
    cds_executor: CdsExecutor,
    adt_module: Any = None,
    profile: Any = None,
    run_id: str | None = None,
    started_at: str | None = None,
) -> JsonObject:
    started_at = started_at or _now()
    run_id = run_id or uuid.uuid4().hex
    base: JsonObject = {
        "schema_version": SCHEMA_VERSION,
        "skill_id": SKILL_ID,
        "run_id": run_id,
        "status": "failed",
        "read_only": True,
        "validated": False,
        "order_context": {},
        "analysis_scope": {},
        "cost_element_details": [],
        "totals": {},
        "relationship_evidence": {},
        "completeness": {
            "source_complete": False,
            "evidence_complete": False,
            "paging_complete": False,
            "total_rows": None,
            "returned_rows": 0,
            "requested_row_limit": PREVIEW_ROW_LIMIT,
            "truncated": False,
        },
        "validation_issues": [],
        "started_at": started_at,
        "completed_at": started_at,
        "artifacts": [{"type": "input", "sha256": _sha256(_canonical_bytes(task))}],
    }
    try:
        normalized = _validate_task(task)
    except ValueError as exc:
        base["validation_issues"] = [{"code": str(exc), "message": "The structured input failed the fixed production-order cost contract."}]
        base["completed_at"] = _now()
        return base

    order_result = table_executor(
        _table_task(
            "AUFK",
            ["MANDT", "AUFNR", "OBJNR", "KOKRS", "BUKRS", "LOEKZ", "PHAS3"],
            [{"field": "AUFNR", "operator": "eq", "value": normalized["adt_order"]}],
            ["MANDT", "AUFNR"],
            2,
        )
    )
    order_rows = [dict(row) for row in order_result.get("rows") or [] if isinstance(row, dict)]
    if not _complete(order_result) or len(order_rows) != 1:
        base["validation_issues"] = [
            {
                "code": "production_cost_relationship_unproven",
                "message": "AUFK did not return exactly one complete, validated production-order relationship row.",
            }
        ]
        base["completed_at"] = _now()
        return base
    order_row = order_rows[0]
    if not all(str(order_row.get(field) or "").strip() for field in ("AUFNR", "OBJNR", "KOKRS", "BUKRS")):
        base["validation_issues"] = [{"code": "production_cost_relationship_incomplete", "message": "AUFK lacks AUFNR, OBJNR, KOKRS, or BUKRS."}]
        base["completed_at"] = _now()
        return base

    actual_filters: list[JsonObject] = [
        {"field": "AUFNR", "operator": "eq", "value": normalized["adt_order"]}
    ]
    if normalized["fiscal_year"]:
        actual_filters.append({"field": "GJAHR", "operator": "eq", "value": normalized["fiscal_year"]})
    if normalized["period"] is not None:
        # ACDOCA in some supported releases does not expose POPER. The exact
        # document keys are resolved to BKPF-MONAT after the order-scoped read.
        pass
    actual_result = table_executor(
        _table_task(
            "ACDOCA",
            ["RCLNT", "RLDNR", "RBUKRS", "GJAHR", "BELNR", "DOCLN", "AUFNR", "RACCT", "HSL", "RHCUR"],
            actual_filters,
            ["RCLNT", "RLDNR", "RBUKRS", "GJAHR", "BELNR", "DOCLN"],
            MAX_COST_ROWS,
        )
    )
    actual_rows = [dict(row) for row in actual_result.get("rows") or [] if isinstance(row, dict)]
    issues: list[JsonObject] = []
    actual_complete = _complete(actual_result)
    if (
        not actual_complete
        and not normalized["fiscal_year"]
        and not normalized["analysis_period_from"]
    ):
        issues.append({"code": "actual_cost_evidence_incomplete", "message": "The exact-order ACDOCA query or paging is incomplete, so the analysis period cannot be derived."})
    posting_headers: list[JsonObject] = []
    posting_artifacts: list[JsonObject] = []
    if actual_complete and actual_rows and not normalized["fiscal_year"]:
        posting_headers, posting_artifacts, posting_issues = _posting_period_headers(
            actual_rows,
            table_executor=table_executor,
        )
        issues.extend(posting_issues)
    period_from, period_to, period_issues = _period_scope(normalized, posting_headers)
    issues.extend(period_issues)
    scope = {
        "analysis_period_from": period_from,
        "analysis_period_to": period_to,
        "ledger": "0L",
        "currency_role": "10",
        "target_cost_variant": 1,
    }
    cds_result: JsonObject = {
        "status": "failed",
        "validated": False,
        "read_only": True,
        "rows": [],
        "completeness": {
            "source_complete": False,
            "paging_complete": False,
            "total_rows": None,
            "returned_rows": 0,
            "requested_row_limit": PREVIEW_ROW_LIMIT,
            "truncated": False,
        },
        "validation_issues": [],
    }
    if period_from and period_to and not period_issues:
        cds_result = cds_executor(
            {**normalized, **scope},
            adt_module,
            profile,
        )
    if not _complete(cds_result):
        issues.extend(
            [dict(item) for item in cds_result.get("validation_issues") or [] if isinstance(item, dict)]
            or [{"code": "production_cost_evidence", "message": "Released plan, target, and actual production-order cost evidence is incomplete."}]
        )
    cds_rows = [dict(row) for row in cds_result.get("rows") or [] if isinstance(row, dict)]
    details, totals, aggregation_issues = (
        _aggregate_cds_rows(
            cds_rows,
            scope,
            order_row,
            normalized["adt_order"],
            str(cds_result.get("source") or CDS_SOURCE),
        )
        if _complete(cds_result) and cds_rows
        else ([], {}, [])
    )
    issues.extend(aggregation_issues)
    if _complete(cds_result) and not cds_rows:
        issues.append({"code": "production_cost_evidence_empty", "message": "The complete CDS query returned no plan, target, or actual cost element rows."})

    cds_completeness = (
        cds_result.get("completeness")
        if isinstance(cds_result.get("completeness"), dict)
        else {}
    )
    actual_required_for_scope = not normalized["fiscal_year"] and not normalized["analysis_period_from"]
    source_complete = bool(
        _complete(order_result)
        and cds_completeness.get("source_complete") is True
        and (actual_complete or not actual_required_for_scope)
    )
    evidence_complete = bool(source_complete and details and not issues)

    base.update(
        {
            "status": "complete" if evidence_complete else "partial",
            "validated": evidence_complete,
            "order_context": {
                "manufacturing_order": normalized["manufacturing_order"],
                "company_code": str(order_row.get("BUKRS") or "").strip(),
                "controlling_area": str(order_row.get("KOKRS") or "").strip(),
                "object_number": str(order_row.get("OBJNR") or "").strip(),
            },
            "analysis_scope": scope,
            "cost_element_details": details,
            "totals": totals,
            "relationship_evidence": {
                "source": "AUFK",
                "source_complete": True,
                "relationship_fields": ["AUFNR", "OBJNR", "KOKRS", "BUKRS"],
                "actual_fallback_source": "ACDOCA",
                "released_cost_source": cds_result.get("source"),
            },
            "completeness": {
                "source_complete": source_complete,
                "evidence_complete": evidence_complete,
                "paging_complete": source_complete,
                "total_rows": cds_completeness.get("total_rows"),
                "returned_rows": int(cds_completeness.get("returned_rows") or 0),
                "requested_row_limit": PREVIEW_ROW_LIMIT,
                "truncated": bool(cds_completeness.get("truncated")),
            },
            "validation_issues": issues,
            "artifacts": [
                {"type": "input", "sha256": _sha256(_canonical_bytes(task))},
                {"type": "aufk_contract", "sha256": _sha256(_canonical_bytes(order_result.get("scope") or {}))},
                {"type": "acdoca_contract", "sha256": _sha256(_canonical_bytes(actual_result.get("scope") or {}))},
                *(
                    [{"type": "bkpf_contract", "sha256": _sha256(_canonical_bytes(posting_artifacts))}]
                    if posting_artifacts
                    else []
                ),
                *(
                    [{"type": "cds_metadata", "sha256": str(cds_result["metadata_sha256"])}]
                    if cds_result.get("metadata_sha256")
                    else []
                ),
                *(
                    [{"type": "generated_query", "sha256": str(cds_result["query_sha256"])}]
                    if cds_result.get("query_sha256")
                    else []
                ),
                {"type": "cost_rows", "sha256": _sha256(_canonical_bytes(details))},
            ],
        }
    )
    base["completed_at"] = _now()
    return base


def _load_common_runtime() -> tuple[Any, Mapping[str, Any], Mapping[str, str], Any]:
    skill_root = Path(__file__).resolve().parents[1]
    common_script = skill_root.parents[1] / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
    spec = importlib.util.spec_from_file_location("sapskillhub_adt_table_export", common_script)
    if spec is None or spec.loader is None:
        raise RuntimeError("adt_runtime_unavailable")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    env_path = common_script.parents[1] / ".env"
    profiles, internal_values = module.load_internal_configuration(env_path)
    probe_task = _table_task(
        "AUFK",
        ["MANDT", "AUFNR"],
        [{"field": "AUFNR", "operator": "eq", "value": "000000000000"}],
        ["MANDT", "AUFNR"],
        1,
    )
    _source_type, _object_name, profile = module._task_identity(probe_task, profiles, internal_values)
    return module, profiles, internal_values, profile


def write_result(path: Path, result: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(payload.encode("utf-8"))
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "skill_id": SKILL_ID,
        "run_id": result.get("run_id"),
        "read_only": True,
        "status": result.get("status"),
        "output_file": path.name,
        "output_sha256": _sha256(payload.encode("utf-8")),
        "created_at": _now(),
    }
    path.with_name(path.name + ".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strictly read-only production-order cost analysis")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    started_at = _now()
    run_id = uuid.uuid4().hex
    try:
        task = json.loads(args.input.read_text(encoding="utf-8"))
        module, profiles, internal_values, profile = _load_common_runtime()

        def table_executor(value: JsonObject) -> JsonObject:
            return module.execute(value, profiles, internal_values=internal_values)

        result = execute(
            task,
            table_executor=table_executor,
            cds_executor=_live_cds_executor,
            adt_module=module,
            profile=profile,
            run_id=run_id,
            started_at=started_at,
        )
    except Exception as exc:
        result = {
            "schema_version": SCHEMA_VERSION,
            "skill_id": SKILL_ID,
            "run_id": run_id,
            "status": "failed",
            "read_only": True,
            "validated": False,
            "order_context": {},
            "analysis_scope": {},
            "cost_element_details": [],
            "totals": {},
            "relationship_evidence": {},
            "completeness": {
                "source_complete": False,
                "evidence_complete": False,
                "paging_complete": False,
                "total_rows": None,
                "returned_rows": 0,
                "requested_row_limit": PREVIEW_ROW_LIMIT,
                "truncated": False,
            },
            "validation_issues": [{"code": "runtime_failure", "message": f"The cost-analysis runtime failed closed: {type(exc).__name__}."}],
            "started_at": started_at,
            "completed_at": _now(),
            "artifacts": [],
        }
    write_result(args.output, result)
    return 0 if result["status"] in {"complete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
