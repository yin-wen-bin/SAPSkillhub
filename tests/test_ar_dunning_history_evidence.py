from __future__ import annotations

from datetime import date
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "FI" / "sap-ar-dunning-history-evidence" / "scripts" / "dunning_history_evidence.py"
SPEC = importlib.util.spec_from_file_location("test_dunning_history_runtime", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _profile() -> dict[str, object]:
    return {
        "enabled": True,
        "profile_status": "validated",
        "profile_id": "test",
        "profile_version": "test",
        "source_id": "mhnk-mhnd-test",
        "profile_sha256": "a" * 64,
        "item_metadata_sha256": "b" * 64,
        "header_metadata_sha256": "c" * 64,
    }


def _item(run_id: str = "A") -> dict[str, str]:
    return {
        "MANDT": "001", "LAUFD": "20240131", "LAUFI": run_id, "KOART": "D",
        "BUKRS": "1710", "KUNNR": "0000010001", "LIFNR": "", "CPDKY": "",
        "SKNRZE": "", "SMABER": "", "SMAHSK": "1", "BBUKRS": "1710",
        "BELNR": "1900000001", "GJAHR": "2024", "BUZEI": "001", "GSBER": "",
        "XBLNR": "PRIVATE-REFERENCE", "MABER": "01", "MADAT": "20240131",
        "MAHNS": "1", "MAHNN": "2", "MANSP": "", "UMSKZ": "", "SHKZG": "S",
        "WAERS": "USD", "DMSHB": "125.50", "WRSHB": "125.50",
    }


def _header(run_id: str = "A") -> dict[str, str]:
    return {
        "MANDT": "001", "LAUFD": "20240131", "LAUFI": run_id, "KOART": "D",
        "BUKRS": "1710", "KUNNR": "0000010001", "LIFNR": "", "CPDKY": "",
        "SKNRZE": "", "SMABER": "", "SMAHSK": "1", "BUSAB": "",
        "AUSDT": "20240201", "PRNDT": "20240202", "MAHNS": "2", "MANSP": "", "WAERS": "USD",
    }


def _source(items=None, headers=None):
    items = [_item()] if items is None else items
    headers = [_header()] if headers is None else headers
    return {
        "items": {"rows": items, "total_rows": len(items), "metadata_sha256": "b" * 64},
        "headers": {"rows": headers, "total_rows": len(headers), "metadata_sha256": "c" * 64},
    }


def _task() -> dict[str, object]:
    return {"schema_version": 1, "company_code": "1710", "customers": ["0000010001"], "as_of": "2024-12-31"}


def test_complete_event_keeps_private_fields_out_of_public_event() -> None:
    result = MODULE.execute(
        _task(), profile=_profile(), source_reader=lambda *_: _source(), current_date=date(2026, 9, 4)
    )
    assert result["status"] == "complete"
    assert result["evidence_status"] == "available"
    assert result["events"][0]["effective_dunning_date"] == "2024-02-01"
    assert result["events"][0]["amount"] == "125.5"
    assert "document_reference_id" not in result["events"][0]
    assert result["restricted_rows"][0]["document_reference_id"] == "PRIVATE-REFERENCE"
    assert result["historical_dunning_master_status"] == "not_assessed"


def test_empty_complete_scope_is_not_found_not_never_dunned() -> None:
    result = MODULE.execute(
        _task(), profile=_profile(), source_reader=lambda *_: _source([], []), current_date=date(2026, 9, 4)
    )
    assert result["status"] == "complete"
    assert result["evidence_status"] == "not_found"
    assert result["completeness"]["source_complete"] is True
    assert "historical_dunning_master_snapshot_not_available" in result["limitations"]


def test_same_day_multiple_runs_are_explicitly_ambiguous() -> None:
    second_item = _item("B")
    second_item["BELNR"] = "1900000002"
    second_header = _header("B")
    result = MODULE.execute(
        _task(),
        profile=_profile(),
        source_reader=lambda *_: _source([_item(), second_item], [_header(), second_header]),
        current_date=date(2026, 9, 4),
    )
    assert result["status"] == "complete"
    assert result["completeness"]["evidence_complete"] is False
    assert {event["sequence_status"] for event in result["events"]} == {"ambiguous"}
    assert result["validation_issues"][0]["code"] == "sequence_ambiguous"


def test_unvalidated_profile_fails_closed_without_calling_source() -> None:
    profile = _profile()
    profile["enabled"] = False
    profile["profile_status"] = "unvalidated"
    called = False

    def source(*_):
        nonlocal called
        called = True
        return _source()

    result = MODULE.execute(_task(), profile=profile, source_reader=source, current_date=date(2026, 9, 4))
    assert result["status"] == "partial"
    assert result["validation_issues"][0]["code"] == "profile_unvalidated"
    assert called is False


def test_manifest_and_schemas_are_closed() -> None:
    root = SCRIPT.parents[1]
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    output = json.loads((root / "references" / "output.schema.json").read_text(encoding="utf-8"))
    assert manifest["read_only"] is True
    assert manifest["validated"] is True
    assert manifest["allowed_http_methods"] == ["GET", "POST"]
    assert output["additionalProperties"] is False
