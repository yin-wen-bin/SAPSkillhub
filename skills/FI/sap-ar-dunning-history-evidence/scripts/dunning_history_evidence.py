from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence
import uuid


SCHEMA_VERSION = 1
SKILL_ID = "sap-ar-dunning-history-evidence"
SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
PROFILE_PATH = SKILL_ROOT / "references" / "source-profiles.json"
PAGE_SIZE = 500
MAX_ROWS = 30_000
ALLOWED_ARTIFACT_ROOTS = (REPO_ROOT / ".artifacts", REPO_ROOT / ".codex-tmp")
COMPANY_CODE = re.compile(r"^[A-Z0-9]{4}$")
CUSTOMER = re.compile(r"^[A-Z0-9_-]{1,10}$")
DUNNING_AREA = re.compile(r"^[A-Z0-9_-]{1,2}$")
ITEM_FIELDS = (
    "MANDT", "LAUFD", "LAUFI", "KOART", "BUKRS", "KUNNR", "LIFNR", "CPDKY",
    "SKNRZE", "SMABER", "SMAHSK", "BBUKRS", "BELNR", "GJAHR", "BUZEI", "GSBER",
    "XBLNR", "MABER", "MADAT", "MAHNS", "MAHNN", "MANSP", "UMSKZ", "SHKZG",
    "WAERS", "DMSHB", "WRSHB",
)
HEADER_FIELDS = (
    "MANDT", "LAUFD", "LAUFI", "KOART", "BUKRS", "KUNNR", "LIFNR", "CPDKY",
    "SKNRZE", "SMABER", "SMAHSK", "BUSAB", "AUSDT", "PRNDT", "MAHNS", "MANSP", "WAERS",
)
SAFE_MESSAGES = {
    "invalid_input": "The structured input failed the fixed dunning-history evidence contract.",
    "future_date_not_allowed": "The as-of date cannot be after the current business date.",
    "profile_unvalidated": "The target-system dunning source profile has not been independently validated.",
    "metadata_incompatible": "Live SAP DDIC metadata does not match the pinned profile.",
    "source_unavailable": "The fixed dunning-history source is unavailable.",
    "row_limit_reached": "The fixed dunning-history row limit was reached.",
    "paging_incomplete": "Stable keyset pagination could not be proven complete.",
    "duplicate_stable_key": "The dunning source returned a duplicate stable key.",
    "source_column_mismatch": "The SAP response columns do not match the fixed source contract.",
    "row_count_mismatch": "The SAP row count does not match the bounded result.",
    "relationship_conflict": "A dunning event conflicts with the requested scope or header relationship.",
    "sequence_ambiguous": "Multiple same-day dunning events have no authoritative business sequence.",
    "amount_invalid": "A dunning amount is not a finite Decimal value.",
    "date_invalid": "A dunning date is invalid.",
    "artifact_path_not_allowed": "Input and output files must stay under an approved ignored artifact directory.",
    "authentication_failed": "SAP authentication failed.",
    "authorization_denied": "SAP denied the read-only request.",
    "timeout": "The bounded SAP read timed out.",
    "query_execution_failed": "SAP rejected the fixed read-only dunning query.",
    "runtime_failure": "The dunning-history runtime failed closed.",
}

JsonObject = dict[str, Any]
SourceReader = Callable[[JsonObject, Mapping[str, Any]], JsonObject]


class DunningError(Exception):
    def __init__(self, code: str):
        self.code = code if code in SAFE_MESSAGES else "source_unavailable"
        super().__init__(SAFE_MESSAGES[self.code])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _issue(code: str) -> JsonObject:
    safe = code if code in SAFE_MESSAGES else "source_unavailable"
    return {"code": safe, "message": SAFE_MESSAGES[safe]}


def _date(value: Any, *, required: bool) -> str | None:
    text = str(value or "").strip()
    if not text:
        if required:
            raise DunningError("date_invalid")
        return None
    for pattern in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    raise DunningError("date_invalid")


def _decimal(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith("-") and text.count("-") == 1:
        text = "-" + text[:-1]
    try:
        parsed = Decimal(text or "0")
    except (InvalidOperation, ValueError) as exc:
        raise DunningError("amount_invalid") from exc
    if not parsed.is_finite():
        raise DunningError("amount_invalid")
    rendered = format(parsed, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _validate_task(task: Any, *, current_date: date | None = None) -> JsonObject:
    allowed = {"schema_version", "company_code", "customers", "as_of", "dunning_area"}
    if not isinstance(task, dict) or set(task) - allowed or task.get("schema_version") != 1:
        raise DunningError("invalid_input")
    company = str(task.get("company_code") or "").strip().upper()
    raw_customers = task.get("customers")
    if not COMPANY_CODE.fullmatch(company) or not isinstance(raw_customers, list) or not 1 <= len(raw_customers) <= 50:
        raise DunningError("invalid_input")
    customers = [str(value or "").strip().upper() for value in raw_customers]
    if any(not CUSTOMER.fullmatch(value) for value in customers) or len(set(customers)) != len(customers):
        raise DunningError("invalid_input")
    try:
        as_of = date.fromisoformat(str(task.get("as_of") or ""))
    except ValueError as exc:
        raise DunningError("invalid_input") from exc
    if as_of > (current_date or datetime.now().astimezone().date()):
        raise DunningError("future_date_not_allowed")
    area = str(task.get("dunning_area") or "").strip().upper() or None
    if area and not DUNNING_AREA.fullmatch(area):
        raise DunningError("invalid_input")
    return {
        "schema_version": 1,
        "company_code": company,
        "customers": customers,
        "as_of": as_of.isoformat(),
        "sap_as_of": as_of.strftime("%Y%m%d"),
        "dunning_area": area,
    }


def _load_profile(path: Path = PROFILE_PATH) -> JsonObject:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        active = document["profiles"][document["active_profile_id"]]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DunningError("metadata_incompatible") from exc
    profile = dict(active)
    profile.update(
        profile_id=document["active_profile_id"],
        profile_version=document.get("profile_version"),
        profile_status=document.get("profile_status"),
        profile_sha256=_sha256(_canonical_bytes(document)),
    )
    return profile


def _base(profile: Mapping[str, Any] | None, run_id: str, started: str) -> JsonObject:
    profile = profile or {}
    return {
        "schema_version": 1,
        "skill_id": SKILL_ID,
        "run_id": run_id,
        "status": "failed",
        "evidence_status": "invalid_input",
        "read_only": True,
        "validated": bool(profile.get("enabled") is True and profile.get("profile_status") == "validated"),
        "requested_scope": {},
        "events": [],
        "restricted_rows": [],
        "historical_dunning_master_status": "not_assessed",
        "source_profile": {
            "profile_id": str(profile.get("profile_id") or ""),
            "version": str(profile.get("profile_version") or ""),
            "status": str(profile.get("profile_status") or "unavailable"),
            "source_id": str(profile.get("source_id") or ""),
            "profile_sha256": str(profile.get("profile_sha256") or ""),
            "item_metadata_sha256": str(profile.get("item_metadata_sha256") or ""),
            "header_metadata_sha256": str(profile.get("header_metadata_sha256") or ""),
        },
        "completeness": {"source_complete": False, "evidence_complete": False, "paging_complete": False, "total_rows": None, "returned_rows": 0, "truncated": False},
        "limitations": ["historical_dunning_master_snapshot_not_available"],
        "validation_issues": [],
        "started_at": started,
        "completed_at": started,
        "artifacts": [],
    }


def _row_key(row: Mapping[str, Any], fields: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(row.get(field) or "") for field in fields)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _keyset_predicate(fields: Sequence[str], key: Sequence[str]) -> str:
    branches = []
    for index, field in enumerate(fields):
        equals = [f"{fields[pos]} = {_sql_literal(key[pos])}" for pos in range(index)]
        branches.append("(" + " AND ".join([*equals, f"{field} > {_sql_literal(key[index])}"]) + ")")
    return "(" + " OR ".join(branches) + ")"


def _read_table(client: Any, common: Any, *, object_name: str, fields: Sequence[str], stable_key: Sequence[str], metadata_sha256: str, normalized: Mapping[str, Any]) -> JsonObject:
    source, _path = client.metadata("table", object_name)
    if _sha256(source.encode("utf-8")) != metadata_sha256:
        raise DunningError("metadata_incompatible")
    selected = list(dict.fromkeys([*fields, *stable_key]))
    predicates = ["KOART = 'D'", f"BUKRS = {_sql_literal(str(normalized['company_code']))}", f"LAUFD <= {_sql_literal(str(normalized['sap_as_of']))}"]
    customers = ", ".join(_sql_literal(str(value)) for value in normalized["customers"])
    predicates.append(f"KUNNR IN ({customers})")
    if normalized.get("dunning_area") and object_name == "MHND":
        predicates.append(f"MABER = {_sql_literal(str(normalized['dunning_area']))}")
    rows: list[JsonObject] = []
    seen: set[tuple[str, ...]] = set()
    last_key: tuple[str, ...] | None = None
    total_rows: int | None = None
    while True:
        page_predicates = list(predicates)
        if last_key is not None:
            page_predicates.append(_keyset_predicate(stable_key, last_key))
        sql = f"SELECT {', '.join(selected)} FROM {object_name} WHERE {' AND '.join(page_predicates)} ORDER BY {', '.join(stable_key)}"
        common._validate_compiled_select(sql)
        preview = client.preview(sql, PAGE_SIZE + 1, prefer_post=True)
        if tuple(str(column).upper() for column in preview.columns) != tuple(field.upper() for field in selected):
            raise DunningError("source_column_mismatch")
        page = [dict(row) for row in preview.rows]
        if not isinstance(preview.total_rows, int) or preview.total_rows < 0:
            raise DunningError("row_count_mismatch")
        if total_rows is None:
            total_rows = preview.total_rows
            if total_rows > min(int(normalized.get("max_rows") or MAX_ROWS), MAX_ROWS):
                raise DunningError("row_limit_reached")
        if preview.total_rows != total_rows - len(rows):
            raise DunningError("row_count_mismatch")
        keep = page[:PAGE_SIZE]
        keys = [_row_key(row, stable_key) for row in keep]
        if keys != sorted(keys) or any(key in seen for key in keys):
            raise DunningError("paging_incomplete")
        seen.update(keys)
        rows.extend(keep)
        if len(page) <= PAGE_SIZE:
            break
        if not keys:
            raise DunningError("paging_incomplete")
        last_key = keys[-1]
    if total_rows != len(rows):
        raise DunningError("row_count_mismatch")
    return {"rows": rows, "total_rows": total_rows, "metadata_sha256": metadata_sha256}


def _load_common_runtime() -> tuple[Any, Any]:
    script = REPO_ROOT / "skills" / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
    spec = importlib.util.spec_from_file_location("sapskillhub_dunning_adt", script)
    if spec is None or spec.loader is None:
        raise DunningError("source_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    profiles, internal = module.load_internal_configuration(script.parents[1] / ".env")
    client = module.AdtClient(module._resolve_profile(profiles, internal).connection)
    return module, client


def _live_source_reader(normalized: JsonObject, profile: Mapping[str, Any]) -> JsonObject:
    common, client = _load_common_runtime()
    normalized = {**normalized, "max_rows": profile.get("max_rows")}
    items = _read_table(client, common, object_name=str(profile["item_object"]), fields=ITEM_FIELDS, stable_key=profile["item_stable_paging_key"], metadata_sha256=str(profile["item_metadata_sha256"]), normalized=normalized)
    headers = _read_table(client, common, object_name=str(profile["header_object"]), fields=HEADER_FIELDS, stable_key=profile["header_stable_paging_key"], metadata_sha256=str(profile["header_metadata_sha256"]), normalized=normalized)
    return {"items": items, "headers": headers}


def _join_key(row: Mapping[str, Any], *, item: bool) -> tuple[str, ...]:
    fields = ["MANDT", "LAUFD", "LAUFI", "KOART", "BUKRS", "KUNNR", "LIFNR", "CPDKY", "SKNRZE", "SMABER", "SMAHSK", "GSBER" if item else "BUSAB"]
    return _row_key(row, fields)


def _sequence_status(items: list[JsonObject]) -> dict[tuple[str, str, str], str]:
    groups: dict[tuple[str, str, str], list[JsonObject]] = {}
    for item in items:
        key = (str(item.get("KUNNR") or ""), str(item.get("MABER") or item.get("SMABER") or ""), str(item.get("LAUFD") or ""))
        groups.setdefault(key, []).append(item)
    return {key: ("ambiguous" if len({str(item.get("LAUFI") or "") for item in group}) > 1 else "ordered") for key, group in groups.items()}


def execute(task: Any, *, profile: Mapping[str, Any] | None = None, source_reader: SourceReader | None = None, current_date: date | None = None, run_id: str | None = None, started_at: str | None = None) -> JsonObject:
    started = started_at or _now()
    identifier = run_id or uuid.uuid4().hex
    active_profile = dict(profile or _load_profile())
    result = _base(active_profile, identifier, started)
    try:
        normalized = _validate_task(task, current_date=current_date)
        result["requested_scope"] = {key: normalized.get(key) for key in ("company_code", "customers", "as_of", "dunning_area")}
        if active_profile.get("profile_status") != "validated" or active_profile.get("enabled") is not True:
            raise DunningError("profile_unvalidated")
        source = (source_reader or _live_source_reader)(normalized, active_profile)
        item_block = source.get("items") if isinstance(source.get("items"), dict) else {}
        header_block = source.get("headers") if isinstance(source.get("headers"), dict) else {}
        item_rows = [dict(row) for row in item_block.get("rows") or [] if isinstance(row, dict)]
        header_rows = [dict(row) for row in header_block.get("rows") or [] if isinstance(row, dict)]
        headers: dict[tuple[str, ...], JsonObject] = {}
        for header in header_rows:
            key = _join_key(header, item=False)
            if key in headers and headers[key] != header:
                raise DunningError("relationship_conflict")
            headers[key] = header
        sequences = _sequence_status(item_rows)
        events: list[JsonObject] = []
        restricted: list[JsonObject] = []
        for row in item_rows:
            if str(row.get("BUKRS") or "") != normalized["company_code"] or str(row.get("KUNNR") or "") not in normalized["customers"]:
                raise DunningError("relationship_conflict")
            header = headers.get(_join_key(row, item=True))
            if header is None:
                raise DunningError("relationship_conflict")
            run_date = _date(row.get("LAUFD"), required=True)
            sequence_key = (str(row.get("KUNNR") or ""), str(row.get("MABER") or row.get("SMABER") or ""), str(row.get("LAUFD") or ""))
            event = {
                "customer": str(row.get("KUNNR") or ""),
                "company_code": str(row.get("BUKRS") or ""),
                "dunning_area": str(row.get("MABER") or row.get("SMABER") or ""),
                "dunning_run_id": str(row.get("LAUFI") or ""),
                "dunning_run_date": run_date,
                "effective_dunning_date": _date(header.get("AUSDT"), required=False) or run_date,
                "fiscal_year": str(row.get("GJAHR") or ""),
                "accounting_document": str(row.get("BELNR") or ""),
                "accounting_document_item": str(row.get("BUZEI") or ""),
                "dunning_level": str(row.get("MAHNN") or ""),
                "old_dunning_level": str(row.get("MAHNS") or ""),
                "dunning_blocking_reason": str(row.get("MANSP") or ""),
                "dunning_reversal_status": "not_assessed",
                "special_gl_code": str(row.get("UMSKZ") or ""),
                "amount": _decimal(row.get("DMSHB")),
                "currency": str(row.get("WAERS") or header.get("WAERS") or ""),
                "sequence_status": sequences[sequence_key],
            }
            events.append(event)
            restricted.append({
                "dunning_run_date": event["dunning_run_date"],
                "dunning_run_id": event["dunning_run_id"],
                "company_code": event["company_code"],
                "customer": event["customer"],
                "accounting_document": event["accounting_document"],
                "accounting_document_item": event["accounting_document_item"],
                "document_reference_id": str(row.get("XBLNR") or ""),
                "one_time_account": str(row.get("CPDKY") or ""),
            })
        ambiguous = any(event["sequence_status"] == "ambiguous" for event in events)
        result.update(
            status="complete",
            evidence_status="available" if events else "not_found",
            events=events,
            restricted_rows=restricted,
            completeness={"source_complete": True, "evidence_complete": not ambiguous, "paging_complete": True, "total_rows": int(item_block.get("total_rows") or 0), "returned_rows": len(events), "truncated": False},
            validation_issues=([_issue("sequence_ambiguous")] if ambiguous else []),
            artifacts=[
                {"type": "source_profile", "sha256": str(active_profile.get("profile_sha256") or "")},
                {"type": "item_metadata", "sha256": str(item_block.get("metadata_sha256") or "")},
                {"type": "header_metadata", "sha256": str(header_block.get("metadata_sha256") or "")},
            ],
        )
    except DunningError as exc:
        result["status"] = "partial" if exc.code not in {"invalid_input", "future_date_not_allowed"} else "failed"
        result["evidence_status"] = "partial" if result["status"] == "partial" else "invalid_input"
        result["completeness"]["truncated"] = exc.code in {"row_limit_reached", "paging_incomplete", "row_count_mismatch"}
        result["validation_issues"] = [_issue(exc.code)]
    except Exception:
        result.update(status="partial", evidence_status="source_unavailable", validation_issues=[_issue("runtime_failure")])
    result["completed_at"] = _now()
    return result


def _allowed_path(path: Path, *, must_exist: bool) -> bool:
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError:
        return False
    return any(resolved == root.resolve() or resolved.is_relative_to(root.resolve()) for root in ALLOWED_ARTIFACT_ROOTS)


def write_result(path: Path, result: JsonObject) -> None:
    if not _allowed_path(path, must_exist=False):
        raise DunningError("artifact_path_not_allowed")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strictly read-only historical AR dunning evidence")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not _allowed_path(args.input, must_exist=True) or not _allowed_path(args.output, must_exist=False):
        print("artifact_path_not_allowed", file=sys.stderr)
        return 2
    started = _now()
    run_id = uuid.uuid4().hex
    profile: JsonObject | None = None
    try:
        task = json.loads(args.input.read_text(encoding="utf-8"))
        profile = _load_profile()
        result = execute(task, profile=profile, run_id=run_id, started_at=started)
    except (OSError, json.JSONDecodeError, DunningError):
        result = _base(profile, run_id, started)
        result["validation_issues"] = [_issue("invalid_input")]
        result["completed_at"] = _now()
    write_result(args.output, result)
    return 0 if result["status"] in {"complete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
