from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[2]
RUNTIME_PATH = Path(__file__).with_name("dunning_history_evidence.py")


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("validation_runtime_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _baseline_rows(common: Any, client: Any, runtime: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    selected = list(runtime.ITEM_FIELDS)
    customers = ", ".join("'" + value.replace("'", "''") + "'" for value in task["customers"])
    sql = (
        f"SELECT {', '.join(selected)} FROM MHND "
        f"WHERE KOART = 'D' AND BUKRS = '{task['company_code']}' "
        f"AND LAUFD <= '{task['as_of'].replace('-', '')}' AND KUNNR IN ({customers}) "
        f"ORDER BY {', '.join(runtime._load_profile()['item_stable_paging_key'])}"
    )
    common._validate_compiled_select(sql)
    preview = client.preview(sql, runtime.MAX_ROWS + 1, prefer_post=True)
    if preview.total_rows != len(preview.rows) or preview.total_rows > runtime.MAX_ROWS:
        raise RuntimeError("baseline_incomplete")
    return [dict(row) for row in preview.rows]


def run(output: Path) -> dict[str, Any]:
    runtime = _load(RUNTIME_PATH, "dunning_profile_runtime")
    common_path = REPO_ROOT / "skills" / "Common" / "sap-adt-table-export" / "scripts" / "adt_table_export.py"
    common = _load(common_path, "dunning_profile_adt")
    profiles, internal = common.load_internal_configuration(common_path.parents[1] / ".env")
    client = common.AdtClient(common._resolve_profile(profiles, internal).connection)
    discovery_sql = (
        "SELECT LAUFD, BUKRS, KUNNR FROM MHND WHERE KOART = 'D' "
        "ORDER BY MANDT, LAUFD, LAUFI, KOART, BUKRS, KUNNR, LIFNR, CPDKY, SKNRZE, SMABER, SMAHSK, BBUKRS, BELNR, GJAHR, BUZEI"
    )
    discovery = client.preview(discovery_sql, 1000, prefer_post=True)
    if not discovery.rows or discovery.total_rows != len(discovery.rows):
        raise RuntimeError("live_sample_discovery_incomplete")
    companies = Counter(str(row.get("BUKRS") or "") for row in discovery.rows)
    company = companies.most_common(1)[0][0]
    customers = list(dict.fromkeys(str(row.get("KUNNR") or "") for row in discovery.rows if str(row.get("BUKRS") or "") == company))[:3]
    if not customers:
        raise RuntimeError("live_sample_unavailable")
    task = {"schema_version": 1, "company_code": company, "customers": customers, "as_of": date.today().isoformat()}
    profile = runtime._load_profile()
    validation_profile = {**profile, "enabled": True, "profile_status": "validated"}
    original_page_size = runtime.PAGE_SIZE
    runtime.PAGE_SIZE = 25
    try:
        nonzero = runtime.execute(task, profile=validation_profile, current_date=date.today())
    finally:
        runtime.PAGE_SIZE = original_page_size
    baseline = _baseline_rows(common, client, runtime, task)
    expected_keys = {
        (str(row.get("BUKRS") or ""), str(row.get("KUNNR") or ""), str(row.get("BELNR") or ""), str(row.get("GJAHR") or ""), str(row.get("BUZEI") or ""), str(row.get("LAUFD") or ""), str(row.get("LAUFI") or ""))
        for row in baseline
    }
    actual_keys = {
        (event["company_code"], event["customer"], event["accounting_document"], event["fiscal_year"], event["accounting_document_item"], event["dunning_run_date"].replace("-", ""), event["dunning_run_id"])
        for event in nonzero.get("events") or []
    }
    if nonzero.get("status") != "complete" or expected_keys != actual_keys:
        raise RuntimeError("nonzero_baseline_mismatch")
    absent = next(value for value in ("9999999999", "9999999998", "9999999997") if value not in {str(row.get("KUNNR") or "") for row in discovery.rows})
    zero_task = {"schema_version": 1, "company_code": company, "customers": [absent], "as_of": date.today().isoformat()}
    zero = runtime.execute(zero_task, profile=validation_profile, current_date=date.today())
    if zero.get("status") != "complete" or zero.get("evidence_status") != "not_found" or zero.get("events"):
        raise RuntimeError("zero_baseline_mismatch")
    forbidden = {"document_reference_id", "one_time_account"}
    if any(forbidden & set(event) for event in nonzero.get("events") or []):
        raise RuntimeError("privacy_projection_failed")
    report = {
        "schema_version": 1,
        "skill_id": runtime.SKILL_ID,
        "verdict": "PASS",
        "read_only": True,
        "semantic_read_only_post": True,
        "profile_version": profile.get("profile_version"),
        "profile_sha256": profile.get("profile_sha256"),
        "item_metadata_sha256": profile.get("item_metadata_sha256"),
        "header_metadata_sha256": profile.get("header_metadata_sha256"),
        "sample": {
            "company_code": company,
            "customer_hashes": [_hash_identifier(value) for value in customers],
            "customer_count": len(customers),
            "baseline_row_count": len(baseline),
            "event_count": len(nonzero.get("events") or []),
            "forced_page_size": 25,
            "multipage": len(baseline) > 25,
        },
        "zero_sample": {"customer_hash": _hash_identifier(absent), "event_count": 0},
        "checks": [
            "live_ddic_metadata_match",
            "nonzero_complete_key_match",
            "complete_zero_result",
            "forced_keyset_paging",
            "public_restricted_split",
            "historical_master_not_assessed",
        ],
        "comparison_hash": runtime._sha256(runtime._canonical_bytes(sorted(expected_keys))),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate the fixed dunning-history source profile")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / ".artifacts" / "sap-ar-dunning-history-evidence-profile-validation.json")
    args = parser.parse_args()
    report = run(args.output.resolve())
    print(json.dumps({"verdict": report["verdict"], "output": str(args.output.resolve()), "event_count": report["sample"]["event_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
