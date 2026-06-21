from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import mb5b_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check sap-mb5b-export prerequisites")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sheet", default=mb5b_export.DEFAULT_INPUT_SHEET)
    parser.add_argument("--plant-column", default=mb5b_export.DEFAULT_PLANT_HEADER)
    parser.add_argument("--storage-column", default=mb5b_export.DEFAULT_STORAGE_HEADER)
    parser.add_argument("--require-sap", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    checks: dict[str, object] = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "windows": os.name == "nt",
        "dependencies": {
            "openpyxl": getattr(mb5b_export.openpyxl, "__version__", "available"),
            "windows_automation": (
                "available"
                if mb5b_export.WINDOWS_IMPORT_ERROR is None
                else str(mb5b_export.WINDOWS_IMPORT_ERROR)
            ),
        },
        "issues": [],
    }
    issues = checks["issues"]
    assert isinstance(issues, list)

    if sys.version_info < (3, 11):
        issues.append("Python 3.11 or later is required")
    if os.name != "nt":
        issues.append("SAP GUI automation requires Windows")
    if mb5b_export.WINDOWS_IMPORT_ERROR is not None:
        issues.append(f"Windows automation dependency error: {mb5b_export.WINDOWS_IMPORT_ERROR}")

    if args.input is not None:
        input_path = args.input.expanduser().resolve()
        checks["input"] = str(input_path)
        try:
            targets = mb5b_export.read_targets(
                input_path,
                args.sheet,
                args.plant_column,
                args.storage_column,
            )
            checks["target_count"] = len(targets)
            if not targets:
                issues.append("Input workbook has no valid plant/storage rows")
        except Exception as exc:
            issues.append(f"Input workbook error: {type(exc).__name__}: {exc}")

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else (args.input.expanduser().resolve().parent if args.input is not None else Path.cwd())
    )
    checks["output_dir"] = str(output_dir)
    existing_parent = output_dir
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent
    if not existing_parent.exists() or not os.access(existing_parent, os.W_OK):
        issues.append(f"Output directory parent is not writable: {existing_parent}")

    if args.require_sap and not issues:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            session = mb5b_export.connect_sap_with_access_helper(output_dir)
            checks["sap"] = mb5b_export.sap_info(session)
        except Exception as exc:
            issues.append(f"SAP session error: {type(exc).__name__}: {exc}")

    checks["ok"] = not issues
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
