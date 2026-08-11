from __future__ import annotations

import argparse
import csv
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "lib"))

from sapskillhub_export.core import (  # noqa: E402
    connect_sap_session, load_control_profile, read_workbook_rows,
    session_identity, sha256, utc_now, write_manifest,
)
from sapskillhub_export.safe_gui_report import SafeGuiReportRunner  # noqa: E402


DEFAULT_PROFILE = Path(__file__).resolve().parents[1] / "references" / "control-profile.json"


def iso_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only F.05 existing-log or test-run export")
    parser.add_argument("--mode", choices=("existing-log", "test-run"), default="existing-log")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--company-code", default="")
    parser.add_argument("--valuation-key-date", type=iso_date)
    parser.add_argument("--valuation-area", default="")
    parser.add_argument("--valuation-method", default="")
    parser.add_argument("--variant", default="")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--file", default="f05-evidence")
    parser.add_argument("--system", default="")
    parser.add_argument("--client", default="")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--allow-unvalidated-profile", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def validate_contract(args: argparse.Namespace, profile: dict[str, Any]) -> None:
    if str(profile.get("transaction", "")).upper() != "F.05":
        raise ValueError("control profile transaction must be F.05")
    if args.mode == "existing-log" and not args.run_id:
        raise ValueError("existing-log mode requires --run-id")
    if args.mode == "test-run" and (not args.company_code or not args.valuation_key_date):
        raise ValueError("test-run mode requires --company-code and --valuation-key-date")
    config = profile.get("modes", {}).get(args.mode, {})
    if not config.get("required_false") or not profile.get("forbidden_controls"):
        raise ValueError("profile must clear and forbid posting/update controls")
    if args.mode == "test-run" and not config.get("required_true"):
        raise ValueError("test-run profile must require a test checkbox")
    if profile.get("profile_status") != "validated" and not args.allow_unvalidated_profile:
        raise ValueError("control profile is not target-system validated")


def write_csv(xlsx: Path, target: Path) -> int:
    columns, rows = read_workbook_rows(xlsx)
    with target.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = utc_now()
    output_dir = args.output_dir.expanduser().resolve()
    name = Path(args.file).stem
    xlsx = output_dir / f"{name}.xlsx"
    csv_path = output_dir / f"{name}.csv"
    log = output_dir / f"{name}.log"
    manifest_path = output_dir / f"{name}.manifest.json"
    profile = load_control_profile(args.profile)
    sap: dict[str, str] = {}
    accepted: dict[str, str] = {}
    outputs_claimed = False
    try:
        validate_contract(args, profile)
        selections = {
            "run_id": args.run_id, "company_code": args.company_code,
            "valuation_key_date": args.valuation_key_date or "",
            "valuation_area": args.valuation_area, "valuation_method": args.valuation_method,
            "variant": args.variant,
        }
        if args.dry_run:
            print(json.dumps({"mode": args.mode, "selections": selections}, ensure_ascii=False, indent=2))
            return 0
        output_dir.mkdir(parents=True, exist_ok=True)
        for target in (xlsx, csv_path, log, manifest_path):
            if target.exists() and not args.overwrite:
                raise FileExistsError(f"output exists; pass --overwrite: {target}")
            if target.exists():
                target.unlink()
        outputs_claimed = True
        session = connect_sap_session(args.system, args.client)
        sap = session_identity(session)
        runner = SafeGuiReportRunner(session, profile, "F.05")
        runner.open_transaction()
        accepted = runner.apply_fields(selections)
        runner.enforce_mode(args.mode)
        runner.execute(args.mode)
        exported = runner.export(xlsx, overwrite=args.overwrite)
        write_csv(xlsx, csv_path)
        finished = utc_now()
        log.write_text(f"{started} start F.05 {args.mode}\n{finished} complete rows={exported.row_count}\n", encoding="utf-8")
        manifest = {
            "schema_version": 1, "skill": "sap-f05-log-export", "transaction": "F.05",
            "mode": args.mode, "run_id": args.run_id, "sap": sap,
            "input": selections, "sap_selection": accepted, "layout_fields": list(exported.columns),
            "row_count": exported.row_count, "totals_by_currency": exported.totals_by_currency,
            "started_at": started, "finished_at": finished, "status": "complete",
            "outputs_sha256": {path.name: sha256(path) for path in (xlsx, csv_path, log)},
        }
        write_manifest(manifest_path, manifest, args.overwrite)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        if outputs_claimed:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(f"{utc_now()} ERROR {type(exc).__name__}: {exc}\n")
                existing = [path for path in (xlsx, csv_path, log) if path.exists()]
                write_manifest(manifest_path, {
                    "schema_version": 1, "skill": "sap-f05-log-export", "transaction": "F.05",
                    "mode": args.mode, "run_id": args.run_id, "sap": sap,
                    "sap_selection": accepted, "started_at": started, "finished_at": utc_now(),
                    "status": "partial" if xlsx.exists() else "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "outputs_sha256": {path.name: sha256(path) for path in existing},
                }, args.overwrite)
            except Exception as manifest_exc:
                print(f"WARN: could not write failure manifest: {manifest_exc}", file=sys.stderr)
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
