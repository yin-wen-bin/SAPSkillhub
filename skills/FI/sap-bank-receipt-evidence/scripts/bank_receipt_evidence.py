from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import decimal
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote
import uuid
from zoneinfo import ZoneInfo


SCHEMA_VERSION = 1
SKILL_ID = "sap-bank-receipt-evidence"
SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
PROFILE_PATH = SKILL_ROOT / "references" / "source-profiles.json"
LOCAL_ENV_PATH = SKILL_ROOT / ".env"
SOURCE_OBJECT = "I_ArBankStatementItem"
SOURCE_DEPENDENCY = "P_ARBankStatementItemIDBS"
PAGE_SIZE = 1_000
MAX_ROWS = 30_000
MAX_RESPONSE_BYTES = 25 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 120
TOTAL_TIMEOUT_SECONDS = 600
ALLOWED_ARTIFACT_ROOTS = (REPO_ROOT / ".artifacts", REPO_ROOT / ".codex-tmp")

SOURCE_FIELDS = (
    "BankStatementShortID",
    "BankStatementItem",
    "CompanyCode",
    "ValueDate",
    "PostingDate",
    "AmountInTransactionCurrency",
    "TransactionCurrency",
    "DebitCreditCode",
    "BankStatementStatus",
    "BankStatementItemLifeCycSts",
    "IsCompleted",
    "IsInProcess",
    "PostingErrorStatus",
    "BankLedgerDocument",
    "SubledgerDocument",
    "FiscalYear",
    "BusinessPartnerName",
    "PartnerBankAccount",
    "PartnerBankIBAN",
    "BankReference",
)
SOURCE_COLUMNS = tuple(field.upper() for field in SOURCE_FIELDS)
STABLE_KEY = ("BANKSTATEMENTSHORTID", "BANKSTATEMENTITEM")
ALLOWED_INPUT_KEYS = {
    "schema_version",
    "company_code",
    "date_from",
    "date_to",
    "receipt_reference",
}
FORBIDDEN_REFERENCE_CHARS = re.compile(r"[\x00-\x1f\x7f*?%]")
COMPANY_CODE = re.compile(r"^[A-Z0-9]{4}$")
SAFE_MESSAGES = {
    "invalid_input": "The structured input failed the fixed bank-receipt evidence contract.",
    "date_range_invalid": "The value-date range must be ordered and contain at most 31 calendar days.",
    "future_date_not_allowed": "The value-date range cannot end after the current business date.",
    "artifact_path_not_allowed": "Input and output files must remain inside an approved ignored artifact directory.",
    "profile_unvalidated": "The fixed target-system source profile has not been validated.",
    "metadata_incompatible": "The live SAP metadata does not match the pinned source profile.",
    "hash_key_unavailable": "The Skill-owned payer-account hash key is unavailable or invalid.",
    "source_unavailable": "The fixed bank-statement source is unavailable.",
    "authentication_failed": "SAP authentication failed.",
    "authorization_denied": "SAP denied the read-only request.",
    "tls_validation_failed": "SAP TLS certificate validation failed.",
    "timeout": "The bounded SAP read timed out.",
    "adt_service_unavailable": "The required SAP ADT read-only service is unavailable.",
    "response_too_large": "The SAP response exceeded the fixed safety bound.",
    "query_execution_failed": "SAP rejected the fixed read-only bank-statement query.",
    "source_total_unavailable": "SAP did not provide a usable total row count.",
    "row_limit_reached": "The fixed bank-receipt row limit was reached.",
    "row_count_mismatch": "The SAP row count did not match the bounded result.",
    "paging_incomplete": "Stable keyset pagination could not be proven complete.",
    "duplicate_stable_key": "The bank-statement source returned a duplicate stable business key.",
    "source_column_mismatch": "The SAP response columns do not match the fixed source contract.",
    "relationship_conflict": "A bank-statement row conflicts with the requested company code.",
    "debit_row_returned": "A non-credit row escaped the fixed credit-only source filter.",
    "row_required_field_missing": "A bank-receipt row is missing a required evidence field.",
    "row_text_invalid": "A bank-receipt text field contains invalid control characters.",
    "amount_invalid": "A bank-receipt amount is not a finite Decimal value.",
    "date_invalid": "A bank-receipt date is invalid.",
    "status_mapping_unknown": "A SAP bank-statement status is outside the validated mapping.",
    "runtime_failure": "The bank-receipt runtime failed closed.",
}


JsonObject = dict[str, Any]
SourceReader = Callable[[JsonObject, Mapping[str, Any]], JsonObject]


class ReceiptError(Exception):
    """Closed-set internal failure that never carries SAP payloads or SQL."""

    def __init__(self, code: str, *, http_status_category: str | None = None):
        safe_code = code if code in SAFE_MESSAGES else "source_unavailable"
        super().__init__(SAFE_MESSAGES[safe_code])
        self.code = safe_code
        self.message = SAFE_MESSAGES[safe_code]
        self.http_status_category = http_status_category


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _issue(code: str, *, http_status_category: str | None = None) -> JsonObject:
    safe_code = code if code in SAFE_MESSAGES else "source_unavailable"
    result: JsonObject = {"code": safe_code, "message": SAFE_MESSAGES[safe_code]}
    if http_status_category:
        result["http_status_category"] = http_status_category
    return result


def _exact(value: decimal.Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _decimal_value(value: Any) -> decimal.Decimal:
    if value is None or str(value).strip() == "":
        raise ReceiptError("row_required_field_missing")
    rendered = str(value).strip()
    if rendered.endswith("-") and rendered.count("-") == 1:
        rendered = "-" + rendered[:-1]
    elif rendered.endswith("+") and rendered.count("+") == 1:
        rendered = rendered[:-1]
    try:
        parsed = decimal.Decimal(rendered)
    except (decimal.InvalidOperation, ValueError) as exc:
        raise ReceiptError("amount_invalid") from exc
    if not parsed.is_finite():
        raise ReceiptError("amount_invalid")
    return parsed


def _parse_date_value(value: Any, *, required: bool) -> str | None:
    rendered = str(value or "").strip()
    if not rendered:
        if required:
            raise ReceiptError("row_required_field_missing")
        return None
    for pattern in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(rendered, pattern).date().isoformat()
        except ValueError:
            continue
    raise ReceiptError("date_invalid")


def _validate_task(
    task: Any,
    *,
    business_timezone: str = "Asia/Shanghai",
    current_date: date | None = None,
) -> JsonObject:
    if not isinstance(task, dict) or set(task) - ALLOWED_INPUT_KEYS:
        raise ReceiptError("invalid_input")
    if task.get("schema_version") != SCHEMA_VERSION:
        raise ReceiptError("invalid_input")
    company_code = task.get("company_code")
    if not isinstance(company_code, str) or not COMPANY_CODE.fullmatch(company_code):
        raise ReceiptError("invalid_input")
    try:
        date_from = date.fromisoformat(task.get("date_from"))
        date_to = date.fromisoformat(task.get("date_to"))
    except (TypeError, ValueError):
        raise ReceiptError("invalid_input") from None
    if date_to < date_from or (date_to - date_from).days > 30:
        raise ReceiptError("date_range_invalid")
    if current_date is None:
        try:
            business_zone = timezone(timedelta(hours=8)) if business_timezone == "Asia/Shanghai" else ZoneInfo(business_timezone)
            current_date = datetime.now(business_zone).date()
        except Exception as exc:
            raise ReceiptError("metadata_incompatible") from exc
    if date_to > current_date:
        raise ReceiptError("future_date_not_allowed")
    receipt_reference = task.get("receipt_reference")
    if receipt_reference is not None:
        if not isinstance(receipt_reference, str):
            raise ReceiptError("invalid_input")
        receipt_reference = receipt_reference.strip()
        if not receipt_reference or len(receipt_reference) > 35 or FORBIDDEN_REFERENCE_CHARS.search(receipt_reference):
            raise ReceiptError("invalid_input")
    return {
        "schema_version": SCHEMA_VERSION,
        "company_code": company_code,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "sap_date_from": date_from.strftime("%Y%m%d"),
        "sap_date_to": date_to.strftime("%Y%m%d"),
        "receipt_reference": receipt_reference,
    }


def _load_profile(path: Path = PROFILE_PATH) -> JsonObject:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptError("metadata_incompatible") from exc
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ReceiptError("metadata_incompatible")
    active_id = document.get("active_profile_id")
    profiles = document.get("profiles")
    raw = profiles.get(active_id) if isinstance(profiles, dict) else None
    if not isinstance(active_id, str) or not isinstance(raw, dict):
        raise ReceiptError("metadata_incompatible")
    profile = dict(raw)
    profile["profile_id"] = active_id
    profile["profile_version"] = str(document.get("profile_version") or "")
    profile["profile_status"] = str(document.get("profile_status") or "unvalidated")
    profile["profile_sha256"] = _sha256(_canonical_bytes(document))
    return profile


def _safe_profile(profile: Mapping[str, Any] | None, source: Mapping[str, Any] | None = None) -> JsonObject:
    profile = profile or {}
    source = source or {}
    pinned = profile.get("metadata_sha256")
    return {
        "profile_id": str(profile.get("profile_id") or ""),
        "version": str(profile.get("profile_version") or ""),
        "status": str(profile.get("profile_status") or "unavailable"),
        "source_id": str(profile.get("source_id") or ""),
        "date_basis": str(profile.get("date_basis") or "value_date"),
        "hash_key_id": str(profile.get("hash_key_id") or ""),
        "profile_sha256": str(profile.get("profile_sha256") or ""),
        "metadata_sha256": str(source.get("metadata_sha256") or pinned or ""),
    }


def _base_result(
    *,
    task: Any,
    profile: Mapping[str, Any] | None,
    run_id: str,
    started_at: str,
) -> JsonObject:
    return {
        "schema_version": SCHEMA_VERSION,
        "skill_id": SKILL_ID,
        "run_id": run_id,
        "status": "failed",
        "evidence_status": "invalid_input",
        "read_only": True,
        "validated": bool(profile and profile.get("enabled") is True and profile.get("profile_status") == "validated"),
        "requested_scope": {},
        "receipts": [],
        "currency_summaries": [],
        "source_profile": _safe_profile(profile),
        "completeness": {
            "source_complete": False,
            "evidence_complete": False,
            "paging_complete": False,
            "total_rows": None,
            "returned_rows": 0,
            "truncated": False,
        },
        "validation_issues": [],
        "started_at": started_at,
        "completed_at": started_at,
        "artifacts": ([{"type": "source_profile", "sha256": str(profile.get("profile_sha256"))}] if profile and profile.get("profile_sha256") else []),
    }


def _row_value(row: Mapping[str, Any], field: str) -> Any:
    return row.get(field.upper(), row.get(field))


def _required_text(row: Mapping[str, Any], field: str) -> str:
    rendered = _optional_text(row, field)
    if not rendered:
        raise ReceiptError("row_required_field_missing")
    return rendered


def _optional_text(row: Mapping[str, Any], field: str) -> str:
    rendered = str(_row_value(row, field) or "").strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in rendered):
        raise ReceiptError("row_text_invalid")
    return rendered


def _account_evidence(row: Mapping[str, Any], hash_key: bytes) -> tuple[str | None, str | None]:
    iban = _optional_text(row, "PartnerBankIBAN")
    account = _optional_text(row, "PartnerBankAccount")
    if iban:
        normalized = "".join(iban.split()).upper()
        domain = "IBAN"
    elif account:
        normalized = account
        domain = "ACCOUNT"
    else:
        return None, None
    if not normalized:
        return None, None
    masked = "****" + normalized[-4:] if len(normalized) > 4 else "****"
    digest = hmac.new(hash_key, f"{domain}:{normalized}".encode("utf-8"), hashlib.sha256).hexdigest()
    return masked, digest


def _status_values(row: Mapping[str, Any], profile: Mapping[str, Any]) -> tuple[str, str]:
    raw_status = str(_row_value(row, "BankStatementStatus") or "").strip()
    reversal_map = profile.get("reversal_status_mapping")
    if not isinstance(reversal_map, dict) or raw_status not in reversal_map:
        raise ReceiptError("status_mapping_unknown")
    reversal_status = str(reversal_map[raw_status])
    lifecycle = str(_row_value(row, "BankStatementItemLifeCycSts") or "").strip()
    lifecycle_map = profile.get("lifecycle_status_mapping")
    if not isinstance(lifecycle_map, dict) or lifecycle not in lifecycle_map:
        raise ReceiptError("status_mapping_unknown")
    lifecycle_state = str(lifecycle_map[lifecycle])
    completed = str(_row_value(row, "IsCompleted") or "").strip().upper()
    in_process = str(_row_value(row, "IsInProcess") or "").strip().upper()
    if completed not in {"", "X"} or in_process not in {"", "X"}:
        raise ReceiptError("status_mapping_unknown")
    posting_error = str(_row_value(row, "PostingErrorStatus") or "").strip()
    posting_error_map = profile.get("posting_error_status_mapping")
    if not isinstance(posting_error_map, dict) or posting_error not in posting_error_map:
        raise ReceiptError("status_mapping_unknown")
    posting_error_state = str(posting_error_map[posting_error])
    if posting_error_state == "error" or raw_status in {"A", "E"}:
        posting_status = "posting_failed"
    elif posting_error_state != "none":
        raise ReceiptError("status_mapping_unknown")
    elif in_process == "X" or raw_status in {"P", "Q"} or lifecycle_state == "partially_applied":
        posting_status = "in_process"
    elif completed == "X" or raw_status in {"8", "S", "R"} or lifecycle_state in {
        "completed", "completed_on_account", "completed_set_to_done"
    }:
        posting_status = "completed"
    elif raw_status in {"", "0", "2", "7"} and lifecycle_state == "not_completed":
        posting_status = "not_completed"
    else:
        raise ReceiptError("status_mapping_unknown")
    return reversal_status, posting_status


def _receipt_from_row(
    row: Mapping[str, Any],
    *,
    normalized: Mapping[str, Any],
    profile: Mapping[str, Any],
    hash_key: bytes,
) -> tuple[JsonObject, decimal.Decimal]:
    if _required_text(row, "CompanyCode") != normalized["company_code"]:
        raise ReceiptError("relationship_conflict")
    if _required_text(row, "DebitCreditCode") != "H":
        raise ReceiptError("debit_row_returned")
    statement_id = _required_text(row, "BankStatementShortID")
    statement_item = _required_text(row, "BankStatementItem")
    value_date = _parse_date_value(_row_value(row, "ValueDate"), required=True)
    posting_date = _parse_date_value(_row_value(row, "PostingDate"), required=False)
    amount = _decimal_value(_row_value(row, "AmountInTransactionCurrency"))
    currency = _required_text(row, "TransactionCurrency")
    reversal_status, posting_status = _status_values(row, profile)
    bank_document = _optional_text(row, "BankLedgerDocument") or None
    subledger_document = _optional_text(row, "SubledgerDocument") or None
    fiscal_year = _optional_text(row, "FiscalYear") or None
    if (bank_document or subledger_document) and not fiscal_year:
        raise ReceiptError("row_required_field_missing")
    related_document = (
        {
            "bank_ledger_document": bank_document,
            "subledger_document": subledger_document,
            "fiscal_year": fiscal_year,
        }
        if bank_document or subledger_document
        else None
    )
    payer_account_masked, payer_account_hash = _account_evidence(row, hash_key)
    receipt = {
        "statement_id": statement_id,
        "statement_item": statement_item,
        "value_date": value_date,
        "posting_date": posting_date,
        "amount": _exact(amount),
        "currency": currency,
        "credit_debit_indicator": "credit",
        "reversal_status": reversal_status,
        "posting_status": posting_status,
        "related_accounting_document": related_document,
        "payer_name": _optional_text(row, "BusinessPartnerName") or None,
        "payer_account_masked": payer_account_masked,
        "payer_account_hash": payer_account_hash,
        "bank_reference": _optional_text(row, "BankReference") or None,
    }
    return receipt, amount


def _summaries(receipts: Sequence[JsonObject]) -> list[JsonObject]:
    groups: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        currency = str(receipt["currency"])
        values = groups.setdefault(
            currency,
            {
                "active_receipt_count": 0,
                "active_receipt_amount": decimal.Decimal(0),
                "reversed_receipt_count": 0,
                "reversed_receipt_amount": decimal.Decimal(0),
            },
        )
        amount = decimal.Decimal(str(receipt["amount"]))
        if receipt["reversal_status"] == "not_reversed":
            values["active_receipt_count"] += 1
            values["active_receipt_amount"] += amount
        else:
            values["reversed_receipt_count"] += 1
            values["reversed_receipt_amount"] += amount
    return [
        {
            "currency": currency,
            "active_receipt_count": values["active_receipt_count"],
            "active_receipt_amount": _exact(values["active_receipt_amount"]),
            "reversed_receipt_count": values["reversed_receipt_count"],
            "reversed_receipt_amount": _exact(values["reversed_receipt_amount"]),
        }
        for currency, values in sorted(groups.items())
    ]


def execute(
    task: Any,
    *,
    profile: Mapping[str, Any] | None,
    source_reader: SourceReader | None = None,
    hash_key: bytes | None = None,
    run_id: str | None = None,
    started_at: str | None = None,
    current_date: date | None = None,
) -> JsonObject:
    started_at = started_at or _now()
    run_id = run_id or uuid.uuid4().hex
    base = _base_result(task=task, profile=profile, run_id=run_id, started_at=started_at)
    timezone_name = str((profile or {}).get("business_timezone") or "Asia/Shanghai")
    try:
        normalized = _validate_task(task, business_timezone=timezone_name, current_date=current_date)
    except ReceiptError as exc:
        base["validation_issues"] = [_issue(exc.code)]
        base["completed_at"] = _now()
        return base
    base["requested_scope"] = {
        "company_code": normalized["company_code"],
        "date_basis": "value_date",
        "date_from": normalized["date_from"],
        "date_to": normalized["date_to"],
        "receipt_reference_supplied": normalized["receipt_reference"] is not None,
    }
    if not profile or profile.get("enabled") is not True or profile.get("profile_status") != "validated":
        base.update(
            {
                "status": "partial",
                "evidence_status": "source_unavailable",
                "validation_issues": [_issue("profile_unvalidated")],
                "completed_at": _now(),
            }
        )
        return base
    if not isinstance(hash_key, bytes) or len(hash_key) < 32:
        base.update(
            {
                "status": "partial",
                "evidence_status": "source_unavailable",
                "validation_issues": [_issue("hash_key_unavailable")],
                "completed_at": _now(),
            }
        )
        return base
    if source_reader is None:
        base.update(
            {
                "status": "partial",
                "evidence_status": "source_unavailable",
                "validation_issues": [_issue("source_unavailable")],
                "completed_at": _now(),
            }
        )
        return base
    try:
        source = source_reader(normalized, profile)
    except ReceiptError as exc:
        source = {
            "status": "partial",
            "rows": [],
            "completeness": {
                "source_complete": False,
                "paging_complete": False,
                "total_rows": None,
                "returned_rows": 0,
                "truncated": False,
            },
            "validation_issues": [_issue(exc.code, http_status_category=exc.http_status_category)],
        }
    source_completeness = source.get("completeness") if isinstance(source.get("completeness"), dict) else {}
    base["source_profile"] = _safe_profile(profile, source)
    base["completeness"] = {
        "source_complete": bool(source_completeness.get("source_complete")),
        "evidence_complete": False,
        "paging_complete": bool(source_completeness.get("paging_complete")),
        "total_rows": source_completeness.get("total_rows"),
        "returned_rows": int(source_completeness.get("returned_rows") or 0),
        "truncated": bool(source_completeness.get("truncated")),
    }
    for artifact_type, key in (("source_metadata", "metadata_sha256"), ("query_template", "query_template_sha256")):
        if source.get(key):
            base["artifacts"].append({"type": artifact_type, "sha256": str(source[key])})
    if source.get("status") != "complete" or not base["completeness"]["source_complete"]:
        issues = [dict(item) for item in source.get("validation_issues") or [] if isinstance(item, dict)]
        base.update(
            {
                "status": "partial",
                "evidence_status": "source_unavailable",
                "validation_issues": issues or [_issue("source_unavailable")],
                "completed_at": _now(),
            }
        )
        return base
    rows = [dict(row) for row in source.get("rows") or [] if isinstance(row, dict)]
    try:
        receipts_with_amounts = [
            _receipt_from_row(row, normalized=normalized, profile=profile, hash_key=hash_key)
            for row in rows
        ]
        receipts = [item[0] for item in receipts_with_amounts]
        keys = [(item["statement_id"], item["statement_item"]) for item in receipts]
        if len(set(keys)) != len(keys):
            raise ReceiptError("duplicate_stable_key")
        receipts.sort(key=lambda item: (item["statement_id"], item["statement_item"]))
    except ReceiptError as exc:
        base.update(
            {
                "status": "partial",
                "evidence_status": "source_unavailable",
                "receipts": [],
                "currency_summaries": [],
                "validation_issues": [_issue(exc.code)],
                "completed_at": _now(),
            }
        )
        return base
    base.update(
        {
            "status": "complete",
            "evidence_status": "available" if receipts else "not_found",
            "receipts": receipts,
            "currency_summaries": _summaries(receipts),
            "validation_issues": [],
            "completed_at": _now(),
        }
    )
    base["completeness"]["evidence_complete"] = True
    return base


def _sql_literal(value: str) -> str:
    if len(value) > 128 or any(ord(char) < 32 for char in value):
        raise ReceiptError("invalid_input")
    return "'" + value.replace("'", "''") + "'"


def _base_predicates(normalized: Mapping[str, Any]) -> list[str]:
    predicates = [
        f"CompanyCode = {_sql_literal(str(normalized['company_code']))}",
        f"AND ValueDate >= {_sql_literal(str(normalized['sap_date_from']))}",
        f"AND ValueDate <= {_sql_literal(str(normalized['sap_date_to']))}",
        "AND DebitCreditCode = 'H'",
    ]
    if normalized.get("receipt_reference") is not None:
        predicates.append(f"AND BankReference = {_sql_literal(str(normalized['receipt_reference']))}")
    return predicates


def build_query(normalized: Mapping[str, Any], last_key: tuple[str, str] | None = None) -> str:
    lines = ["SELECT"]
    for index, field in enumerate(SOURCE_FIELDS):
        lines.append(f"  {field}{',' if index < len(SOURCE_FIELDS) - 1 else ''}")
    lines.append(f"FROM {SOURCE_OBJECT}")
    base = _base_predicates(normalized)
    if last_key is None:
        lines.append("WHERE " + base[0])
        lines.extend(base[1:])
    else:
        first_key = _sql_literal(last_key[0])
        second_key = _sql_literal(last_key[1])
        lines.append("WHERE " + base[0])
        lines.extend(base[1:])
        lines.append(f"AND BankStatementShortID > {first_key}")
        lines.append("OR " + base[0])
        lines.extend(base[1:])
        lines.append(f"AND BankStatementShortID = {first_key}")
        lines.append(f"AND BankStatementItem > {second_key}")
    lines.append("ORDER BY BankStatementShortID, BankStatementItem")
    if any(len(line) > 120 for line in lines):
        raise ReceiptError("query_execution_failed")
    return "\n".join(lines)


def _query_template_sha256() -> str:
    template = {
        "source": SOURCE_OBJECT,
        "fields": list(SOURCE_FIELDS),
        "filters": ["CompanyCode=", "ValueDate=BT", "DebitCreditCode=H", "BankReference=optional-EQ"],
        "stable_key": list(STABLE_KEY),
        "page_size": PAGE_SIZE,
        "max_rows": MAX_ROWS,
        "method": "POST",
    }
    return _sha256(_canonical_bytes(template))


def _metadata_contract(source: str, dependency: str, profile: Mapping[str, Any]) -> None:
    expected_source_hash = str(profile.get("metadata_sha256") or "")
    dependencies = profile.get("dependency_metadata_sha256")
    expected_dependency_hash = dependencies.get(SOURCE_DEPENDENCY) if isinstance(dependencies, dict) else None
    if _sha256(source.encode("utf-8")) != expected_source_hash:
        raise ReceiptError("metadata_incompatible")
    if _sha256(dependency.encode("utf-8")) != expected_dependency_hash:
        raise ReceiptError("metadata_incompatible")
    for field in SOURCE_FIELDS:
        if not re.search(rf"\b{re.escape(field)}\b", source, flags=re.IGNORECASE):
            raise ReceiptError("metadata_incompatible")
    for key in ("BankStatementShortID", "BankStatementItem"):
        if not re.search(rf"\bkey\b[^\n]*\b{re.escape(key)}\b", dependency, flags=re.IGNORECASE):
            raise ReceiptError("metadata_incompatible")


def _source_key(row: Mapping[str, Any]) -> tuple[str, str]:
    values = tuple(str(_row_value(row, field) or "").strip() for field in STABLE_KEY)
    if not all(values):
        raise ReceiptError("row_required_field_missing")
    return values[0], values[1]


def read_source_with_client(
    normalized: Mapping[str, Any],
    profile: Mapping[str, Any],
    *,
    client: Any,
    common_module: Any,
) -> JsonObject:
    returned_rows = 0
    total_rows: int | None = None
    metadata_sha256: str | None = None
    try:
        source, _source_path = client.metadata("cds", SOURCE_OBJECT)
        dependency, _dependency_path = client.metadata("cds", SOURCE_DEPENDENCY)
        _metadata_contract(source, dependency, profile)
        metadata_sha256 = _sha256(source.encode("utf-8"))
        rows: list[JsonObject] = []
        seen: set[tuple[str, str]] = set()
        last_key: tuple[str, str] | None = None
        previous_key: tuple[str, str] | None = None
        while True:
            query = build_query(normalized, last_key)
            common_module._validate_compiled_select(query)
            preview = client.preview(query, PAGE_SIZE + 1, prefer_post=True)
            if tuple(str(column).upper() for column in preview.columns) != SOURCE_COLUMNS:
                raise ReceiptError("source_column_mismatch")
            page_rows = [dict(row) for row in preview.rows]
            if preview.total_rows is None or not isinstance(preview.total_rows, int) or preview.total_rows < 0:
                raise ReceiptError("source_total_unavailable")
            if total_rows is None:
                total_rows = preview.total_rows
                if total_rows > MAX_ROWS:
                    returned_rows = len(page_rows)
                    raise ReceiptError("row_limit_reached")
            expected_remaining = total_rows - len(rows)
            if preview.total_rows != expected_remaining:
                raise ReceiptError("row_count_mismatch")
            if len(page_rows) != min(expected_remaining, PAGE_SIZE + 1):
                raise ReceiptError("row_count_mismatch")
            keep = page_rows[:PAGE_SIZE]
            page_keys = [_source_key(row) for row in keep]
            if page_keys != sorted(page_keys) or any(
                page_keys[index] <= page_keys[index - 1] for index in range(1, len(page_keys))
            ):
                raise ReceiptError("paging_incomplete")
            if previous_key is not None and page_keys and page_keys[0] <= previous_key:
                raise ReceiptError("paging_incomplete")
            for key in page_keys:
                if key in seen:
                    raise ReceiptError("duplicate_stable_key")
                seen.add(key)
            rows.extend(keep)
            returned_rows += len(keep)
            if len(page_rows) <= PAGE_SIZE:
                break
            if not page_keys:
                raise ReceiptError("paging_incomplete")
            previous_key = page_keys[-1]
            last_key = page_keys[-1]
        if total_rows != len(rows):
            raise ReceiptError("row_count_mismatch")
        return {
            "status": "complete",
            "rows": rows,
            "metadata_sha256": metadata_sha256,
            "query_template_sha256": _query_template_sha256(),
            "completeness": {
                "source_complete": True,
                "paging_complete": True,
                "total_rows": total_rows,
                "returned_rows": len(rows),
                "truncated": False,
            },
            "validation_issues": [],
        }
    except ReceiptError as exc:
        code = exc.code
    except common_module.ExportError as exc:
        raw_code = str(getattr(exc, "code", "source_unavailable"))
        mapping = {
            "metadata_unavailable": "metadata_incompatible",
            "query_line_truncated": "query_execution_failed",
            "query_syntax_invalid": "query_execution_failed",
            "query_column_invalid": "query_execution_failed",
            "query_execution_failed": "query_execution_failed",
            "timeout": "timeout",
            "authorization_denied": "authorization_denied",
            "authentication_failed": "authentication_failed",
            "tls_validation_failed": "tls_validation_failed",
            "adt_service_unavailable": "adt_service_unavailable",
            "response_too_large": "response_too_large",
        }
        code = mapping.get(raw_code, "source_unavailable")
    return {
        "status": "partial",
        "rows": [],
        "metadata_sha256": metadata_sha256,
        "query_template_sha256": _query_template_sha256(),
        "completeness": {
            "source_complete": False,
            "paging_complete": False,
            "total_rows": total_rows,
            "returned_rows": returned_rows,
            "truncated": code in {"row_limit_reached", "row_count_mismatch", "paging_incomplete"},
        },
        "validation_issues": [_issue(code)],
    }


def _bounded_client_class(common_module: Any):
    class BoundedBankAdtClient(common_module.AdtClient):
        def _bounded_request(self, method: str, url: str, **kwargs: Any):
            kwargs["stream"] = True
            response = self._session.request(method, url, **kwargs)
            content_length = response.headers.get("Content-Length")
            if content_length and content_length.isdigit() and int(content_length) > MAX_RESPONSE_BYTES:
                response.close()
                raise common_module.ExportError("response_too_large", SAFE_MESSAGES["response_too_large"])
            payload = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                payload.extend(chunk)
                if len(payload) > MAX_RESPONSE_BYTES:
                    response.close()
                    raise common_module.ExportError("response_too_large", SAFE_MESSAGES["response_too_large"])
            response._content = bytes(payload)
            response._content_consumed = True
            return response

        def _metadata_get(self, path: str, accept: str):
            try:
                response = self._bounded_request(
                    "GET",
                    self._connection.base_url + path,
                    headers={
                        "Accept": accept,
                        "X-SAP-Client": self._connection.client,
                        "Accept-Language": self._connection.language,
                    },
                    verify=self._connection.verify,
                    timeout=self._connection.timeout_seconds,
                    allow_redirects=False,
                )
                if 300 <= response.status_code < 400:
                    raise common_module.ExportError("metadata_unavailable", "Redirects are not allowed for ADT metadata.")
                if response.status_code == 401:
                    raise common_module.ExportError("authentication_failed", SAFE_MESSAGES["authentication_failed"])
                if response.status_code == 403:
                    raise common_module.ExportError("authorization_denied", SAFE_MESSAGES["authorization_denied"])
                if response.status_code >= 400 or not response.text.strip():
                    raise common_module.ExportError("metadata_unavailable", "SAP ADT metadata is unavailable.")
                return response.text, path
            except common_module.ExportError:
                raise
            except self._requests.exceptions.SSLError as exc:
                raise common_module.ExportError("tls_validation_failed", SAFE_MESSAGES["tls_validation_failed"]) from exc
            except self._requests.exceptions.Timeout as exc:
                raise common_module.ExportError("timeout", SAFE_MESSAGES["timeout"]) from exc
            except self._requests.exceptions.RequestException as exc:
                raise common_module.ExportError("adt_service_unavailable", SAFE_MESSAGES["adt_service_unavailable"]) from exc

        def _request(self, method: str, *, row_number: int, sql: str, token: str | None = None):
            if method not in {"GET", "POST"}:
                raise common_module.ExportError("query_execution_failed", SAFE_MESSAGES["query_execution_failed"])
            headers = {
                "Accept": common_module.ACCEPT,
                "X-SAP-Client": self._connection.client,
                "Accept-Language": self._connection.language,
            }
            if token:
                headers["x-csrf-token"] = token
            kwargs: JsonObject = {
                "headers": headers,
                "verify": self._connection.verify,
                "timeout": self._connection.timeout_seconds,
                "allow_redirects": False,
            }
            if method == "GET":
                kwargs["params"] = {"rowNumber": row_number, "sqlCommand": sql}
            else:
                headers["Content-Type"] = "text/plain; charset=utf-8"
                kwargs["params"] = {"rowNumber": row_number}
                kwargs["data"] = sql.encode("utf-8")
            return self._bounded_request(method, self._url, **kwargs)

        def _csrf_token(self) -> str:
            response = self._bounded_request(
                "GET",
                self._url,
                headers={
                    "Accept": common_module.ACCEPT,
                    "X-SAP-Client": self._connection.client,
                    "x-csrf-token": "fetch",
                },
                verify=self._connection.verify,
                timeout=self._connection.timeout_seconds,
                allow_redirects=False,
            )
            if 300 <= response.status_code < 400:
                raise common_module.ExportError("adt_service_unavailable", "Redirects are not allowed for ADT CSRF.")
            if response.status_code == 401:
                raise common_module.ExportError("authentication_failed", SAFE_MESSAGES["authentication_failed"])
            if response.status_code == 403:
                raise common_module.ExportError("authorization_denied", SAFE_MESSAGES["authorization_denied"])
            token = response.headers.get("x-csrf-token")
            if token and (200 <= response.status_code < 300 or response.status_code == 405):
                return token
            raise common_module.ExportError("adt_service_unavailable", "SAP ADT did not return a CSRF token.")

    return BoundedBankAdtClient


def _load_common_runtime() -> tuple[Any, Any]:
    common_script = REPO_ROOT / "skills" / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
    spec = importlib.util.spec_from_file_location("sapskillhub_bank_adt_table_export", common_script)
    if spec is None or spec.loader is None:
        raise ReceiptError("source_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    profiles, internal_values = module.load_internal_configuration(common_script.parents[1] / ".env")
    trusted_profile = module._resolve_profile(profiles, internal_values)
    connection = replace(
        trusted_profile.connection,
        timeout_seconds=max(REQUEST_TIMEOUT_SECONDS, trusted_profile.connection.timeout_seconds),
    )
    client = _bounded_client_class(module)(connection)
    return module, client


def _live_source_reader(normalized: JsonObject, profile: Mapping[str, Any]) -> JsonObject:
    module, client = _load_common_runtime()
    return read_source_with_client(normalized, profile, client=client, common_module=module)


def _load_local_env(path: Path = LOCAL_ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _load_hash_key(profile: Mapping[str, Any]) -> bytes:
    values = _load_local_env()
    if values.get("SAP_BANK_RECEIPT_HMAC_KEY_ID") != profile.get("hash_key_id"):
        raise ReceiptError("hash_key_unavailable")
    try:
        key = base64.b64decode(values.get("SAP_BANK_RECEIPT_HMAC_KEY_B64", ""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ReceiptError("hash_key_unavailable") from exc
    if len(key) < 32:
        raise ReceiptError("hash_key_unavailable")
    return key


def _is_allowed_artifact_path(path: Path, *, must_exist: bool) -> bool:
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError:
        return False
    return any(resolved == root.resolve() or resolved.is_relative_to(root.resolve()) for root in ALLOWED_ARTIFACT_ROOTS)


def write_result(path: Path, result: JsonObject) -> None:
    if not _is_allowed_artifact_path(path, must_exist=False):
        raise ReceiptError("artifact_path_not_allowed")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    manifest_path = path.with_name(path.name + ".manifest.json")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "skill_id": SKILL_ID,
        "run_id": result.get("run_id"),
        "read_only": True,
        "status": result.get("status"),
        "output_sha256": _sha256(payload.encode("utf-8")),
        "profile_sha256": result.get("source_profile", {}).get("profile_sha256"),
        "metadata_sha256": result.get("source_profile", {}).get("metadata_sha256"),
        "query_template_sha256": next(
            (item.get("sha256") for item in result.get("artifacts", []) if item.get("type") == "query_template"),
            None,
        ),
        "created_at": _now(),
    }
    manifest_temporary = manifest_path.with_name(manifest_path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(payload.encode("utf-8"))
        manifest_temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        os.replace(manifest_temporary, manifest_path)
    finally:
        for candidate in (temporary, manifest_temporary):
            if candidate.exists():
                candidate.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strictly read-only SAP bank-receipt evidence")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if not _is_allowed_artifact_path(args.input, must_exist=True) or not _is_allowed_artifact_path(args.output, must_exist=False):
        print("artifact_path_not_allowed", file=sys.stderr)
        return 2
    started_at = _now()
    run_id = uuid.uuid4().hex
    profile: JsonObject | None = None
    try:
        task = json.loads(args.input.read_text(encoding="utf-8"))
        profile = _load_profile()
        hash_key: bytes | None = None
        source_reader: SourceReader | None = None
        if profile.get("enabled") is True and profile.get("profile_status") == "validated":
            hash_key = _load_hash_key(profile)
            source_reader = _live_source_reader
        result = execute(
            task,
            profile=profile,
            source_reader=source_reader,
            hash_key=hash_key,
            run_id=run_id,
            started_at=started_at,
        )
    except ReceiptError as exc:
        result = _base_result(task={}, profile=profile, run_id=run_id, started_at=started_at)
        result["status"] = "partial"
        result["evidence_status"] = "source_unavailable"
        result["validation_issues"] = [_issue(exc.code)]
        result["completed_at"] = _now()
    except (OSError, json.JSONDecodeError):
        result = _base_result(task={}, profile=profile, run_id=run_id, started_at=started_at)
        result["validation_issues"] = [_issue("invalid_input")]
        result["completed_at"] = _now()
    except Exception:
        result = _base_result(task={}, profile=profile, run_id=run_id, started_at=started_at)
        result["status"] = "partial"
        result["evidence_status"] = "source_unavailable"
        result["validation_issues"] = [_issue("runtime_failure")]
        result["completed_at"] = _now()
    write_result(args.output, result)
    return 0 if result["status"] in {"complete", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
