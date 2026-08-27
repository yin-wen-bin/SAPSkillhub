from __future__ import annotations

import argparse
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
SKILL_ID = "sap-wbs-object-resolver"
SKILL_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = SKILL_ROOT / "references" / "source-profiles.json"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
SourceExecutor = Callable[[Mapping[str, Any], str, str], Mapping[str, Any]]


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


def _validate_task(task: Any, profile: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(task, dict) or set(task) != {"schema_version", "wbs_external_id", "company_code"}:
        raise ValueError("input_contract_invalid")
    if task.get("schema_version") != 1:
        raise ValueError("schema_version_invalid")
    raw_wbs = task.get("wbs_external_id")
    raw_company = task.get("company_code")
    if not isinstance(raw_wbs, str) or not isinstance(raw_company, str):
        raise ValueError("input_contract_invalid")
    wbs = raw_wbs.strip()
    company = raw_company.strip().upper()
    if not wbs or len(wbs) > 64 or any(ord(ch) < 32 for ch in wbs):
        raise ValueError("wbs_external_id_invalid")
    if not re.fullmatch(r"[A-Z0-9]{4}", company):
        raise ValueError("company_code_invalid")
    if profile.get("case_insensitive_external_id") is True:
        wbs = wbs.upper()
    return {"wbs_external_id": wbs, "company_code": company}


def _base(run_id: str, started_at: str, profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "skill_id": SKILL_ID,
        "run_id": run_id,
        "status": "partial",
        "resolution_status": "source_unavailable",
        "read_only": True,
        "validated": False,
        "requested_scope": {},
        "resolved_object": None,
        "relationship_evidence": {},
        "source_profile": {"version": str(profile.get("profile_version") or ""), "sha256": _sha256(_canonical(profile))},
        "completeness": {"source_complete": False, "evidence_complete": False, "paging_complete": False, "total_rows": None, "returned_rows": 0, "truncated": False},
        "validation_issues": [],
        "started_at": started_at,
        "completed_at": started_at,
        "artifacts": [],
    }


def _rows(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in result.get("rows", []) if isinstance(row, dict)]


def _source_is_complete(result: Mapping[str, Any], row_count: int) -> bool:
    total = result.get("total_rows")
    return bool(result.get("source_complete") is True and result.get("paging_complete") is True and isinstance(total, int) and total >= 0 and total == row_count and row_count <= 2)


def execute(task: Any, *, source_executor: SourceExecutor, profile: Mapping[str, Any] | None = None, run_id: str | None = None, started_at: str | None = None) -> dict[str, Any]:
    active_profile = dict(profile or json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
    run_id = run_id or uuid.uuid4().hex
    started_at = started_at or _now()
    output = _base(run_id, started_at, active_profile)
    output["artifacts"].append({"type": "input", "sha256": _sha256(_canonical(task))})
    try:
        normalized = _validate_task(task, active_profile)
    except ValueError as exc:
        output.update({"status": "failed", "resolution_status": "invalid_input", "validation_issues": [_issue(str(exc), "The resolver input or safety contract is invalid.")], "completed_at": _now()})
        return output
    output["requested_scope"] = normalized
    sources = [item for item in active_profile.get("sources", []) if isinstance(item, dict) and item.get("enabled") is True]
    if len(sources) != 2:
        output["validation_issues"] = [_issue("source_unavailable", "The fixed WBS resolver source profile is unavailable.")]
        output["completed_at"] = _now()
        return output
    results: list[Mapping[str, Any]] = []
    rows_by_source: list[list[dict[str, Any]]] = []
    for source in sources:
        try:
            result = source_executor(source, normalized["wbs_external_id"], normalized["company_code"])
        except Exception as exc:
            result = {"issues": [_issue("source_unavailable", f"The fixed WBS source failed closed: {type(exc).__name__}.")]}
        results.append(result)
        current_rows = _rows(result)
        rows_by_source.append(current_rows)
        if str(result.get("metadata_sha256") or "") != str(source.get("metadata_sha256") or ""):
            output["validation_issues"].append(_issue("metadata_incompatible", "A live WBS source metadata fingerprint does not match the validated profile."))
        if not _source_is_complete(result, len(current_rows)):
            output["validation_issues"].extend([dict(item) for item in result.get("issues", []) if isinstance(item, dict)] or [_issue("source_unavailable", "A required WBS source or its pagination evidence is incomplete.")])
    returned = sum(len(rows) for rows in rows_by_source)
    totals = [result.get("total_rows") for result in results]
    technically_complete = not output["validation_issues"] and all(_source_is_complete(result, len(rows)) for result, rows in zip(results, rows_by_source))
    output["completeness"].update({"source_complete": technically_complete, "paging_complete": technically_complete, "total_rows": sum(int(value) for value in totals) if all(isinstance(value, int) for value in totals) else None, "returned_rows": returned, "truncated": any(len(rows) > 1 for rows in rows_by_source)})
    if not technically_complete:
        output["completed_at"] = _now()
        return output
    if all(not rows for rows in rows_by_source):
        output.update({"resolution_status": "not_found", "validation_issues": [_issue("not_found", "No exact WBS object matched the requested external ID and company code.")], "completed_at": _now()})
        return output
    if any(len(rows) != 1 for rows in rows_by_source):
        output.update({"resolution_status": "ambiguous", "validation_issues": [_issue("ambiguous", "The exact WBS lookup did not produce one unique row in every required source.")], "completed_at": _now()})
        return output
    project, financial = rows_by_source[0][0], rows_by_source[1][0]
    candidate = {
        "object_type": "WBS",
        "external_id": str(financial.get("WBSElement") or "").strip(),
        "internal_id": str(financial.get("WBSElementInternalID") or "").strip(),
        "object_number": str(financial.get("WBSElementObject") or "").strip(),
        "company_code": str(financial.get("CompanyCode") or "").strip().upper(),
        "controlling_area": str(financial.get("ControllingArea") or "").strip().upper(),
        "project_internal_id": str(financial.get("ProjectInternalID") or "").strip(),
        "project_external_id": str(financial.get("Project") or "").strip(),
    }
    comparisons = {
        "external_id": str(project.get("WBSElementExternalID") or "").strip() == candidate["external_id"] == normalized["wbs_external_id"],
        "internal_id": str(project.get("WBSElementInternalID") or "").strip() == candidate["internal_id"],
        "company_code": str(project.get("CompanyCode") or "").strip().upper() == candidate["company_code"] == normalized["company_code"],
        "controlling_area": bool(candidate["controlling_area"]) and str(project.get("ControllingArea") or "").strip().upper() == candidate["controlling_area"],
        "project_internal_id": bool(candidate["project_internal_id"]) and str(project.get("ProjectInternalID") or "").strip() == candidate["project_internal_id"],
        "object_number": bool(re.fullmatch(r"PR[0-9A-Za-z]{1,30}", candidate["object_number"])),
    }
    if not all(comparisons.values()) or not candidate["project_external_id"]:
        output.update({"resolution_status": "ambiguous", "validation_issues": [_issue("relationship_inconsistent", "The required WBS sources disagree or omit an authoritative relationship field.")], "relationship_evidence": {"checks": comparisons, "sources": [str(source.get("id")) for source in sources]}, "completed_at": _now()})
        return output
    output.update({
        "status": "complete",
        "resolution_status": "resolved",
        "validated": True,
        "resolved_object": candidate,
        "relationship_evidence": {"sources": [str(source.get("id")) for source in sources], "checks": comparisons, "relationship_fields": ["external_id", "internal_id", "object_number", "company_code", "controlling_area", "project_internal_id", "project_external_id"]},
        "validation_issues": [],
        "completed_at": _now(),
    })
    output["completeness"]["evidence_complete"] = True
    for source, result in zip(sources, results):
        output["artifacts"].append({"type": "metadata", "source": str(source.get("id")), "sha256": str(result.get("metadata_sha256"))})
        output["artifacts"].append({"type": "relationship_rows", "source": str(source.get("id")), "sha256": _sha256(_canonical(_rows(result)))})
    return output


def _load_common_connection() -> Any:
    common = SKILL_ROOT.parents[1] / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
    spec = importlib.util.spec_from_file_location("sapskillhub_wbs_common", common)
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


class ODataExecutor:
    def __init__(self, connection: Any):
        import requests
        self._session = requests.Session()
        self._session.auth = (connection.username, connection.password)
        self._connection = connection

    def __call__(self, source: Mapping[str, Any], wbs: str, company: str) -> Mapping[str, Any]:
        service, entity = str(source["service"]), str(source["entity_set"])
        root = f"{self._connection.base_url}/sap/opu/odata/sap/{service}"
        headers = {"Accept": "application/json", "X-SAP-Client": self._connection.client, "Accept-Language": self._connection.language}
        # The validated metadata fingerprint is language-neutral. SAP adds
        # localized annotations when Accept-Language is sent, which changes
        # the bytes without changing the service contract.
        metadata_headers = {"Accept": "application/xml", "X-SAP-Client": self._connection.client}
        metadata_hash = _sha256(self._get(root + "/$metadata", metadata_headers))
        if metadata_hash != source.get("metadata_sha256"):
            return {"metadata_sha256": metadata_hash, "rows": [], "total_rows": None, "source_complete": False, "paging_complete": False, "issues": [_issue("metadata_incompatible", "A live WBS source metadata fingerprint does not match the validated profile.")]}
        escaped_wbs, escaped_company = wbs.replace("'", "''"), company.replace("'", "''")
        params = {"$select": ",".join(str(item) for item in source["fields"]), "$filter": f"{source['external_id_field']} eq '{escaped_wbs}' and CompanyCode eq '{escaped_company}'", "$top": "2", "$inlinecount": "allpages", "$format": "json"}
        payload = json.loads(self._get(root + "/" + entity, headers, params=params).decode("utf-8-sig"))
        envelope = payload.get("d", payload) if isinstance(payload, dict) else {}
        rows = envelope.get("results", []) if isinstance(envelope, dict) else []
        count = envelope.get("__count") if isinstance(envelope, dict) else None
        total = int(count) if isinstance(count, str) and count.isdigit() else len(rows) if isinstance(rows, list) else None
        next_link = envelope.get("__next") if isinstance(envelope, dict) else None
        return {"metadata_sha256": metadata_hash, "rows": rows if isinstance(rows, list) else [], "total_rows": total, "source_complete": not next_link and total is not None and total <= 2, "paging_complete": not next_link and total is not None and total <= 2}

    def _get(self, url: str, headers: Mapping[str, str], params: Mapping[str, str] | None = None) -> bytes:
        try:
            response = self._session.get(url, headers=headers, params=params, verify=self._connection.verify, timeout=min(max(int(self._connection.timeout_seconds), 30), 120), allow_redirects=False, stream=True)
        except Exception as exc:
            raise RuntimeError(type(exc).__name__) from exc
        if response.status_code in {301, 302, 303, 307, 308}:
            raise RuntimeError("redirect_not_allowed")
        if response.status_code == 401:
            raise RuntimeError("authentication_failed")
        if response.status_code == 403:
            raise RuntimeError("authorization_denied")
        if response.status_code >= 400:
            raise RuntimeError("source_unavailable")
        body = bytearray()
        for chunk in response.iter_content(65536):
            body.extend(chunk)
            if len(body) > MAX_RESPONSE_BYTES:
                raise RuntimeError("response_too_large")
        return bytes(body)


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
    parser = argparse.ArgumentParser(description="Resolve one SAP WBS object through fixed read-only sources")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    run_id, started_at = uuid.uuid4().hex, _now()
    try:
        task = json.loads(args.input.read_text(encoding="utf-8"))
        result = execute(task, source_executor=ODataExecutor(_load_common_connection()), profile=profile, run_id=run_id, started_at=started_at)
    except Exception as exc:
        result = _base(run_id, started_at, profile)
        result.update({"status": "partial", "resolution_status": "source_unavailable", "validation_issues": [_issue("source_unavailable", f"The resolver runtime failed closed: {type(exc).__name__}.")], "completed_at": _now()})
    write_result(args.output, result)
    return 0 if result["status"] in {"complete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
