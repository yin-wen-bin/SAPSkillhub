from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import uuid
from datetime import datetime, timezone
import xml.etree.ElementTree as ET


SCHEMA_VERSION = 1
SKILL_ID = "sap-control-object-commitment-evidence"
SKILL_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = SKILL_ROOT / "references" / "source-profiles.json"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {"21", "22", "24", "26"}
SourceExecutor = Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _issue(code: str, message: str, http_status_category: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "message": message}
    if http_status_category:
        item["http_status_category"] = http_status_category
    return item


def _decimal(value: Any) -> Decimal | None:
    if value in {None, ""}:
        return None
    rendered = str(value).strip()
    if rendered.endswith("-") and rendered.count("-") == 1:
        rendered = "-" + rendered[:-1]
    elif rendered.endswith("+") and rendered.count("+") == 1:
        rendered = rendered[:-1]
    try:
        parsed = Decimal(rendered)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _exact(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _validate_task(task: Any) -> dict[str, Any]:
    expected = {"schema_version", "resolved_object", "fiscal_year", "period_from", "period_to", "commitment_types"}
    if not isinstance(task, dict) or set(task) != expected or task.get("schema_version") != 1:
        raise ValueError("input_contract_invalid")
    resolved = task.get("resolved_object")
    allowed_resolved = {"object_type", "external_id", "internal_id", "object_number", "company_code", "controlling_area", "project_internal_id", "project_external_id"}
    required_resolved = {"object_type", "internal_id", "object_number", "company_code", "controlling_area"}
    if not isinstance(resolved, dict) or set(resolved) - allowed_resolved or not required_resolved.issubset(resolved):
        raise ValueError("resolved_object_invalid")
    object_type = str(resolved.get("object_type") or "")
    if object_type not in {"WBS", "INTERNAL_ORDER"}:
        raise ValueError("resolved_object_invalid")
    normalized_object = {key: str(value).strip() for key, value in resolved.items()}
    normalized_object["object_type"] = object_type
    normalized_object["company_code"] = normalized_object["company_code"].upper()
    normalized_object["controlling_area"] = normalized_object["controlling_area"].upper()
    if not normalized_object["internal_id"] or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", normalized_object["internal_id"]):
        raise ValueError("resolved_object_invalid")
    if not re.fullmatch(r"[A-Z0-9]{4}", normalized_object["company_code"]) or not re.fullmatch(r"[A-Z0-9]{4}", normalized_object["controlling_area"]):
        raise ValueError("resolved_object_invalid")
    prefix = "PR" if object_type == "WBS" else "OR"
    object_number = normalized_object["object_number"].upper()
    if not re.fullmatch(prefix + r"[A-Z0-9_-]{1,30}", object_number):
        raise ValueError("resolved_object_relationship_invalid")
    suffix = object_number[len(prefix):]
    internal_id = normalized_object["internal_id"].upper()
    if suffix.lstrip("0") != internal_id.lstrip("0"):
        raise ValueError("resolved_object_relationship_invalid")
    normalized_object["object_number"] = object_number
    if object_type == "WBS" and not normalized_object.get("external_id"):
        raise ValueError("resolved_object_external_id_missing")
    year = task.get("fiscal_year")
    period_from, period_to = task.get("period_from"), task.get("period_to")
    types = task.get("commitment_types")
    if not isinstance(year, str) or not re.fullmatch(r"[0-9]{4}", year):
        raise ValueError("fiscal_year_invalid")
    if isinstance(period_from, bool) or isinstance(period_to, bool) or not isinstance(period_from, int) or not isinstance(period_to, int) or not 1 <= period_from <= period_to <= 16:
        raise ValueError("accounting_period_invalid")
    if not isinstance(types, list) or not types or len(types) > 4 or len(set(types)) != len(types) or any(str(item) not in ALLOWED_TYPES for item in types):
        raise ValueError("commitment_type_invalid")
    return {"resolved_object": normalized_object, "fiscal_year": year, "period_from": period_from, "period_to": period_to, "commitment_types": sorted(str(item) for item in types)}


def _base(run_id: str, started_at: str, profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "skill_id": SKILL_ID,
        "run_id": run_id,
        "status": "partial",
        "read_only": True,
        "validated": False,
        "resolved_object": {},
        "analysis_scope": {},
        "relationship_evidence": {},
        "source_profile": {"version": str(profile.get("profile_version") or ""), "status": str(profile.get("profile_status") or "unavailable"), "sha256": _sha256(_canonical(profile))},
        "commitment_details": [],
        "commitment_totals": None,
        "completeness": {"source_complete": False, "evidence_complete": False, "paging_complete": False, "scope_complete": False, "total_rows": None, "returned_rows": 0, "truncated": False},
        "validation_issues": [],
        "started_at": started_at,
        "completed_at": started_at,
        "artifacts": [],
    }


def _derive_type(row: Mapping[str, Any], mappings: Mapping[str, Any]) -> str | None:
    requisition = str(row.get("purchasing_requisition") or "").strip()
    purchase_order = str(row.get("purchasing_document") or "").strip()
    explicit = str(row.get("commitment_type") or "").strip()
    candidates: list[str] = []
    if requisition and isinstance(mappings.get("21"), dict) and mappings["21"].get("derivation") == "purchase_requisition_reference":
        candidates.append("21")
    if purchase_order and isinstance(mappings.get("22"), dict) and mappings["22"].get("derivation") == "purchase_order_reference":
        candidates.append("22")
    if explicit in ALLOWED_TYPES:
        mapping = mappings.get(explicit)
        if isinstance(mapping, dict) and mapping.get("derivation") == "explicit_source_value" and str(mapping.get("source_value")) == explicit:
            candidates.append(explicit)
    return candidates[0] if len(candidates) == 1 else None


def _aggregate(rows: list[dict[str, Any]], normalized: Mapping[str, Any], source: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    stable_keys: set[str] = set()
    mappings = source.get("value_type_mapping") if isinstance(source.get("value_type_mapping"), dict) else {}
    target = normalized["resolved_object"]
    for row in rows:
        stable_key = str(row.get("source_key") or "").strip()
        amount = _decimal(row.get("amount"))
        commitment_type = _derive_type(row, mappings)
        period_raw = row.get("accounting_period")
        try:
            period = int(period_raw) if not isinstance(period_raw, bool) else -1
        except (TypeError, ValueError):
            period = -1
        checks = {
            "stable_key": bool(stable_key) and stable_key not in stable_keys,
            "object_number": str(row.get("object_number") or "").strip().upper() == target["object_number"],
            "fiscal_year": str(row.get("fiscal_year") or "").strip() == normalized["fiscal_year"],
            "accounting_period": normalized["period_from"] <= period <= normalized["period_to"],
            "commitment_type": commitment_type in normalized["commitment_types"],
            "amount": amount is not None,
            "currency": bool(str(row.get("currency") or "").strip()),
            "currency_role": bool(str(row.get("currency_role") or "").strip()),
        }
        if not all(checks.values()):
            code = "amount_invalid" if not checks["amount"] else "commitment_type_unsupported" if not checks["commitment_type"] else "stable_key_invalid" if not checks["stable_key"] else "evidence_scope_inconsistent"
            issues.append(_issue(code, "A commitment row failed the strict relationship, period, type, amount, currency, or stable-key contract."))
            continue
        stable_keys.add(stable_key)
        details.append({
            "source_key": stable_key,
            "object_number": target["object_number"],
            "fiscal_year": normalized["fiscal_year"],
            "accounting_period": period,
            "commitment_type": commitment_type,
            "cost_element": str(row.get("cost_element") or "").strip(),
            "purchasing_requisition": str(row.get("purchasing_requisition") or "").strip(),
            "purchasing_requisition_item": str(row.get("purchasing_requisition_item") or "").strip(),
            "purchasing_document": str(row.get("purchasing_document") or "").strip(),
            "purchasing_document_item": str(row.get("purchasing_document_item") or "").strip(),
            "amount": _exact(amount),
            "currency": str(row.get("currency") or "").strip().upper(),
            "currency_role": str(row.get("currency_role") or "").strip().upper(),
            "synthetic_zero": False,
        })
    if issues:
        return [], None, issues
    details.sort(key=lambda row: (row["commitment_type"], row["currency"], row["currency_role"], row["accounting_period"], row["cost_element"], row["source_key"]))
    totals_map: dict[tuple[str, str, str], Decimal] = {}
    for row in details:
        key = (row["commitment_type"], row["currency"], row["currency_role"])
        totals_map[key] = totals_map.get(key, Decimal("0")) + Decimal(row["amount"])
    groups = [{"commitment_type": key[0], "currency": key[1], "currency_role": key[2], "amount": _exact(value)} for key, value in sorted(totals_map.items())]
    represented_types = {row["commitment_type"] for row in details}
    if represented_types != set(normalized["commitment_types"]):
        return [], None, [_issue("commitment_type_scope_incomplete", "The complete source result does not prove every requested commitment type, including explicit zero evidence where applicable.")]
    return details, {"groups": groups}, []


def execute(task: Any, *, source_executor: SourceExecutor | None = None, profile: Mapping[str, Any] | None = None, run_id: str | None = None, started_at: str | None = None) -> dict[str, Any]:
    active_profile = dict(profile or json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
    run_id, started_at = run_id or uuid.uuid4().hex, started_at or _now()
    output = _base(run_id, started_at, active_profile)
    output["artifacts"].append({"type": "input", "sha256": _sha256(_canonical(task))})
    try:
        normalized = _validate_task(task)
    except ValueError as exc:
        output.update({"status": "failed", "validation_issues": [_issue(str(exc), "The commitment input or resolved-object safety contract is invalid.")], "completed_at": _now()})
        return output
    output["resolved_object"] = normalized["resolved_object"]
    output["analysis_scope"] = {key: normalized[key] for key in ("fiscal_year", "period_from", "period_to", "commitment_types")}
    object_type = normalized["resolved_object"]["object_type"]
    sources = active_profile.get("sources") if isinstance(active_profile.get("sources"), dict) else {}
    source = sources.get(object_type) if isinstance(sources.get(object_type), dict) else None
    unavailable_code = "internal_order_commitment_source_unavailable" if object_type == "INTERNAL_ORDER" else "wbs_commitment_source_unavailable"
    if not source or source.get("enabled") is not True or active_profile.get("profile_status") != "validated":
        output.update({"relationship_evidence": {"object_type": object_type, "object_number_prefix_valid": True}, "validation_issues": [_issue(unavailable_code, "No validated authoritative period-bearing commitment source is available for this object type.")], "completed_at": _now()})
        return output
    mappings = source.get("value_type_mapping") if isinstance(source.get("value_type_mapping"), dict) else {}
    unsupported = [item for item in normalized["commitment_types"] if item not in mappings]
    if unsupported:
        output.update({"validation_issues": [_issue("commitment_type_unsupported", "The active source profile does not prove every requested commitment type mapping.")], "completed_at": _now()})
        return output
    if source_executor is None:
        output.update({"validation_issues": [_issue(unavailable_code, "No validated runtime executor is available for this commitment source.")], "completed_at": _now()})
        return output
    try:
        result = source_executor(source, normalized)
    except Exception as exc:
        output.update({"validation_issues": [_issue("source_unavailable", f"The approved commitment query failed closed: {type(exc).__name__}.")], "completed_at": _now()})
        return output
    rows = [dict(row) for row in result.get("rows", []) if isinstance(row, dict)]
    total_rows = result.get("total_rows")
    metadata_match = not source.get("metadata_sha256") or result.get("metadata_sha256") == source.get("metadata_sha256")
    source_complete = bool(result.get("source_complete") is True and metadata_match and isinstance(total_rows, int) and total_rows >= 0 and total_rows == len(rows) and total_rows <= int(source.get("max_rows", 10000)))
    paging_complete = bool(source_complete and result.get("paging_complete") is True)
    scope_complete = bool(source_complete and result.get("scope_complete") is True)
    output["completeness"].update({"source_complete": source_complete, "paging_complete": paging_complete, "scope_complete": scope_complete, "total_rows": total_rows if isinstance(total_rows, int) and total_rows >= 0 else None, "returned_rows": len(rows), "truncated": bool(isinstance(total_rows, int) and total_rows > int(source.get("max_rows", 10000)))})
    if not metadata_match:
        output["validation_issues"] = [_issue("metadata_incompatible", "The live commitment metadata fingerprint does not match the validated source profile.")]
    elif not source_complete or not paging_complete or not scope_complete:
        output["validation_issues"] = [_issue("commitment_source_incomplete", "The commitment source, requested period scope, row count, or pagination is incomplete.")]
    if output["validation_issues"]:
        output["completed_at"] = _now()
        return output
    if not rows:
        zero = result.get("zero_context") if isinstance(result.get("zero_context"), dict) else {}
        currency, role = str(zero.get("currency") or "").strip().upper(), str(zero.get("currency_role") or "").strip().upper()
        if not currency or not role or result.get("authoritative_empty") is not True:
            output.update({"validation_issues": [_issue("zero_scope_unproven", "A complete empty response lacks authoritative zero and currency context.")], "completed_at": _now()})
            return output
        rows = [{"source_key": f"ZERO-{item}", "object_number": normalized["resolved_object"]["object_number"], "fiscal_year": normalized["fiscal_year"], "accounting_period": normalized["period_from"], "commitment_type": item, "purchasing_requisition": "ZERO" if item == "21" else "", "purchasing_document": "ZERO" if item == "22" else "", "amount": "0", "currency": currency, "currency_role": role} for item in normalized["commitment_types"]]
    details, totals, aggregation_issues = _aggregate(rows, normalized, source)
    if aggregation_issues:
        output.update({"validation_issues": aggregation_issues, "completed_at": _now()})
        return output
    if result.get("authoritative_empty") is True:
        for detail in details:
            detail["synthetic_zero"] = True
    output.update({
        "status": "complete",
        "validated": True,
        "relationship_evidence": {"object_type": object_type, "object_number_prefix_valid": True, "company_code": normalized["resolved_object"]["company_code"], "controlling_area": normalized["resolved_object"]["controlling_area"], "source_id": str(source.get("source_id") or "")},
        "commitment_details": details,
        "commitment_totals": totals,
        "validation_issues": [],
        "completed_at": _now(),
    })
    output["completeness"]["evidence_complete"] = True
    output["artifacts"].append({"type": "commitment_rows", "sha256": _sha256(_canonical(details))})
    if result.get("metadata_sha256"):
        output["artifacts"].append({"type": "metadata", "sha256": str(result["metadata_sha256"])})
    return output


def parse_soap_response(xml_bytes: bytes, field_mapping: Mapping[str, str]) -> list[dict[str, str]]:
    upper = xml_bytes.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("xml_external_entity_forbidden")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("soap_response_invalid") from exc
    local = lambda tag: tag.rsplit("}", 1)[-1]
    item_name = str(field_mapping.get("item_element") or "Item")
    rows: list[dict[str, str]] = []
    for item in root.iter():
        if local(item.tag) != item_name:
            continue
        descendants = {local(child.tag): (child.text or "").strip() for child in item.iter() if child is not item}
        rows.append({target: descendants.get(source, "") for target, source in field_mapping.items() if target != "item_element"})
    return rows


def _soap_marker(xml_bytes: bytes, element_name: str | None) -> str:
    if not element_name:
        return ""
    upper = xml_bytes.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("xml_external_entity_forbidden")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("soap_response_invalid") from exc
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == element_name:
            return (element.text or "").strip()
    return ""


def _soap_boolean(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "x", "yes"}:
        return True
    if normalized in {"false", "0", "", "no"}:
        return False
    return None


class SoapExecutor:
    def __init__(self, connection: Any):
        import requests
        self._session = requests.Session()
        self._session.auth = (connection.username, connection.password)
        self._connection = connection

    def __call__(self, source: Mapping[str, Any], normalized: Mapping[str, Any]) -> Mapping[str, Any]:
        path, action = source.get("endpoint_path"), source.get("soap_action")
        if not isinstance(path, str) or not path.startswith("/sap/bc/srt/") or not isinstance(action, str) or action != source.get("approved_read_action"):
            raise RuntimeError("soap_action_not_allowed")
        if normalized["resolved_object"]["object_type"] != "WBS":
            raise RuntimeError("soap_object_type_not_allowed")
        request_mapping = source.get("request_mapping") if isinstance(source.get("request_mapping"), dict) else {}
        required_names = {
            "project_element_id": str(request_mapping.get("project_element_id") or "ProjectElementID"),
            "fiscal_year": str(request_mapping.get("fiscal_year") or "FiscalYear"),
            "period_from": str(request_mapping.get("period_from") or "AccountingPeriodFrom"),
            "period_to": str(request_mapping.get("period_to") or "AccountingPeriodTo"),
        }
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}", value) for value in required_names.values()):
            raise RuntimeError("soap_mapping_invalid")
        pagination = source.get("pagination") if isinstance(source.get("pagination"), dict) else {}
        paging_mode = str(pagination.get("mode") or "single_page")
        if paging_mode not in {"single_page", "continuation"}:
            raise RuntimeError("soap_paging_invalid")
        page_size = int(source.get("page_size") or 1000)
        max_rows = int(source.get("max_rows") or 10000)
        if not 1 <= page_size <= max_rows <= 10000:
            raise RuntimeError("soap_paging_invalid")
        continuation = ""
        seen_tokens: set[str] = set()
        rows: list[dict[str, str]] = []
        page_count = 0
        while True:
            page_count += 1
            if page_count > (max_rows // page_size) + 2:
                raise RuntimeError("paging_incomplete")
            envelope = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
            body = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
            operation_namespace = str(source.get("operation_namespace") or "").strip()
            operation_name = str(source["operation"])
            query_tag = f"{{{operation_namespace}}}{operation_name}" if operation_namespace else operation_name
            query = ET.SubElement(body, query_tag)
            request_values = {
                "project_element_id": normalized["resolved_object"]["external_id"],
                "fiscal_year": normalized["fiscal_year"],
                "period_from": str(normalized["period_from"]),
                "period_to": str(normalized["period_to"]),
            }
            for key, value in request_values.items():
                ET.SubElement(query, required_names[key]).text = value
            page_size_element = str(pagination.get("page_size_element") or "").strip()
            if page_size_element:
                ET.SubElement(query, page_size_element).text = str(page_size)
            request_token_element = str(pagination.get("request_token_element") or "").strip()
            if continuation:
                if not request_token_element:
                    raise RuntimeError("soap_paging_invalid")
                ET.SubElement(query, request_token_element).text = continuation
            payload = ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
            response = self._session.post(self._connection.base_url + path, data=payload, headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": action, "X-SAP-Client": self._connection.client}, verify=self._connection.verify, timeout=min(max(int(self._connection.timeout_seconds), 30), 180), allow_redirects=False, stream=True)
            if response.status_code in {301, 302, 303, 307, 308}:
                raise RuntimeError("redirect_not_allowed")
            if response.status_code == 401:
                raise RuntimeError("authentication_failed")
            if response.status_code == 403:
                raise RuntimeError("authorization_denied")
            if response.status_code >= 400:
                raise RuntimeError("source_unavailable")
            raw = bytearray()
            for chunk in response.iter_content(65536):
                raw.extend(chunk)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise RuntimeError("response_too_large")
            raw_bytes = bytes(raw)
            page_rows = parse_soap_response(raw_bytes, source.get("field_mapping", {}))
            rows.extend(page_rows)
            if len(rows) > max_rows:
                raise RuntimeError("row_limit_reached")
            if paging_mode == "single_page":
                break
            more_name = str(pagination.get("more_data_element") or "").strip()
            token_name = str(pagination.get("response_token_element") or "").strip()
            more = _soap_boolean(_soap_marker(raw_bytes, more_name))
            if more is None:
                raise RuntimeError("paging_incomplete")
            if not more:
                break
            next_token = _soap_marker(raw_bytes, token_name)
            if not next_token or next_token in seen_tokens:
                raise RuntimeError("paging_incomplete")
            seen_tokens.add(next_token)
            continuation = next_token
        return {"rows": rows, "total_rows": len(rows), "source_complete": True, "paging_complete": True, "scope_complete": True, "metadata_sha256": source.get("metadata_sha256")}


def _load_common_connection() -> Any:
    common = SKILL_ROOT.parents[1] / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
    spec = importlib.util.spec_from_file_location("sapskillhub_commitment_common", common)
    if spec is None or spec.loader is None:
        raise RuntimeError("source_unavailable")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    profiles, values = module.load_internal_configuration(common.parents[1] / ".env")
    probe = {"schema_version": 1, "source_type": "table", "object": "AUFK", "fields": ["MANDT", "AUFNR"], "filters": [{"field": "AUFNR", "operator": "eq", "value": "000000000000"}], "order_by": ["MANDT", "AUFNR"], "max_rows": 1}
    _type, _name, resolved = module._task_identity(probe, profiles, values)
    return resolved.connection


def write_result(path: Path, result: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    manifest = {"schema_version": 1, "skill_id": SKILL_ID, "run_id": result.get("run_id"), "read_only": True, "status": result.get("status"), "output_file": path.name, "output_sha256": _sha256(payload.encode("utf-8")), "created_at": _now()}
    path.with_name(path.name + ".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read strict SAP control-object commitment evidence")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    run_id, started_at = uuid.uuid4().hex, _now()
    try:
        task = json.loads(args.input.read_text(encoding="utf-8"))
        sources = profile.get("sources", {})
        has_enabled_source = any(isinstance(value, dict) and value.get("enabled") is True for value in sources.values()) if isinstance(sources, dict) else False
        executor = SoapExecutor(_load_common_connection()) if has_enabled_source else None
        result = execute(task, source_executor=executor, profile=profile, run_id=run_id, started_at=started_at)
    except Exception as exc:
        result = _base(run_id, started_at, profile)
        result.update({"status": "partial", "validation_issues": [_issue("source_unavailable", f"The commitment runtime failed closed: {type(exc).__name__}.")], "completed_at": _now()})
    write_result(args.output, result)
    return 0 if result["status"] in {"complete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
