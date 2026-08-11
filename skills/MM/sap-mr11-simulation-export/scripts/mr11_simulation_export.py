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
    parser = argparse.ArgumentParser(description="Read-only MR11 simulation evidence export")
    parser.add_argument("--company-code", required=True)
    parser.add_argument("--key-date", type=iso_date, required=True)
    parser.add_argument("--purchase-order-low", default="")
    parser.add_argument("--purchase-order-high", default="")
    parser.add_argument("--age-days", type=int, default=0)
    parser.add_argument("--tolerance-policy", default="")
    parser.add_argument("--variant", default="")
    parser.add_argument("--run-mode", choices=("validate", "full"), default="validate")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--file", default="mr11-simulation")
    parser.add_argument("--system", default="")
    parser.add_argument("--client", default="")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--allow-unvalidated-profile", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def validate_contract(args: argparse.Namespace, profile: dict[str, Any]) -> None:
    if str(profile.get("transaction", "")).upper() != "MR11":
        raise ValueError("control profile transaction must be MR11")
    if args.age_days < 0:
        raise ValueError("age-days cannot be negative")
    if not args.tolerance_policy and not args.variant:
        raise ValueError("provide --tolerance-policy or --variant")
    if args.purchase_order_high and not args.purchase_order_low:
        raise ValueError("purchase-order-high requires purchase-order-low")
    for value in (args.purchase_order_low, args.purchase_order_high):
        if value and (not value.isdigit() or len(value) > 10):
            raise ValueError("purchase order bounds must contain at most 10 digits")
    if args.purchase_order_high and int(args.purchase_order_low) > int(args.purchase_order_high):
        raise ValueError("purchase-order-low cannot exceed purchase-order-high")
    mode = profile.get("modes", {}).get("simulation", {})
    if not mode.get("required_true") or not mode.get("required_false"):
        raise ValueError("profile must prove simulation true and posting/update false")
    if not profile.get("forbidden_controls"):
        raise ValueError("profile must list forbidden posting/update controls")
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
    raw = output_dir / f"{name}.xlsx"
    csv_path = output_dir / f"{name}.csv"
    log = output_dir / f"{name}.log"
    manifest_path = output_dir / f"{name}.manifest.json"
    profile = load_control_profile(args.profile)
    sap: dict[str, str] = {}
    accepted: dict[str, str] = {}
    outputs_claimed = False
    try:
        validate_contract(args, profile)
        inputs = {
            "company_code": args.company_code, "key_date": args.key_date,
            "purchase_order_low": args.purchase_order_low, "purchase_order_high": args.purchase_order_high,
            "age_days": str(args.age_days), "tolerance_policy": args.tolerance_policy,
            "variant": args.variant, "run_mode": args.run_mode, "sap_mode": "simulation",
            "max_hits": "100" if args.run_mode == "validate" else "50000",
        }
        if args.dry_run:
            print(json.dumps(inputs, ensure_ascii=False, indent=2))
            return 0
        output_dir.mkdir(parents=True, exist_ok=True)
        for target in (raw, csv_path, log, manifest_path):
            if target.exists() and not args.overwrite:
                raise FileExistsError(f"output exists; pass --overwrite: {target}")
            if target.exists():
                target.unlink()
        outputs_claimed = True
        session = connect_sap_session(args.system, args.client)
        sap = session_identity(session)
        runner = SafeGuiReportRunner(session, profile, "MR11")
        runner.open_transaction()
        field_inputs = {
            key: inputs[key]
            for key in (
                "company_code", "key_date", "purchase_order_low",
                "purchase_order_high", "age_days", "tolerance_policy",
                "variant", "max_hits",
            )
        }
        accepted = runner.apply_fields(field_inputs)
        runner.enforce_mode("simulation")
        runner.execute("simulation")
        exported = runner.export(raw, overwrite=args.overwrite)
        write_csv(raw, csv_path)
        finished = utc_now()
        log.write_text(f"{started} start MR11 simulation\n{finished} complete rows={exported.row_count}\n", encoding="utf-8")
        manifest = {
            "schema_version": 1, "skill": "sap-mr11-simulation-export", "transaction": "MR11",
            "mode": "simulation", "run_mode": args.run_mode, "sap": sap,
            "input": inputs, "sap_selection": accepted, "layout_fields": list(exported.columns),
            "row_count": exported.row_count, "totals_by_currency": exported.totals_by_currency,
            "started_at": started, "finished_at": finished, "status": "complete",
            "outputs_sha256": {path.name: sha256(path) for path in (raw, csv_path, log)},
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
                existing = [path for path in (raw, csv_path, log) if path.exists()]
                write_manifest(manifest_path, {
                    "schema_version": 1, "skill": "sap-mr11-simulation-export", "transaction": "MR11",
                    "mode": "simulation", "run_mode": args.run_mode, "sap": sap,
                    "sap_selection": accepted, "started_at": started, "finished_at": utc_now(),
                    "status": "partial" if raw.exists() else "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "outputs_sha256": {path.name: sha256(path) for path in existing},
                }, args.overwrite)
            except Exception as manifest_exc:
                print(f"WARN: could not write failure manifest: {manifest_exc}", file=sys.stderr)
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
