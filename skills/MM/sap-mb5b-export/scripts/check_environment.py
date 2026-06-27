from __future__ import annotations

import argparse
from importlib import metadata
import json
import os
import re
import sys
from pathlib import Path

try:
    import mb5b_export
except Exception as exc:  # pragma: no cover - reports broken local environments
    mb5b_export = None
    MB5B_IMPORT_ERROR: Exception | None = exc
else:
    MB5B_IMPORT_ERROR = None


DEFAULT_INPUT_SHEET = "Sheet1"
DEFAULT_PLANT_HEADER = "プラント"
DEFAULT_STORAGE_HEADER = "保管場所"
MINIMUM_DEPENDENCIES = {
    "openpyxl": "3.1.5",
    "pywin32": "311",
    "pywinauto": "0.6.9",
}
TESTED_DEPENDENCIES = {
    "openpyxl": "3.1.5",
    "pywin32": "311",
    "pywinauto": "0.6.9",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check sap-mb5b-export prerequisites")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--sheet",
        default=getattr(mb5b_export, "DEFAULT_INPUT_SHEET", DEFAULT_INPUT_SHEET),
    )
    parser.add_argument(
        "--plant-column",
        default=getattr(mb5b_export, "DEFAULT_PLANT_HEADER", DEFAULT_PLANT_HEADER),
    )
    parser.add_argument(
        "--storage-column",
        default=getattr(mb5b_export, "DEFAULT_STORAGE_HEADER", DEFAULT_STORAGE_HEADER),
    )
    parser.add_argument("--require-sap", action="store_true")
    return parser


def version_parts(value: str) -> tuple[int, ...]:
    parts = tuple(int(part) for part in re.findall(r"\d+", value))
    return parts or (0,)


def version_at_least(installed: str, required: str) -> bool:
    installed_parts = version_parts(installed)
    required_parts = version_parts(required)
    width = max(len(installed_parts), len(required_parts))
    return installed_parts + (0,) * (width - len(installed_parts)) >= required_parts + (
        0,
    ) * (width - len(required_parts))


def installed_distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def dependency_policy() -> dict[str, dict[str, object]]:
    policy: dict[str, dict[str, object]] = {}
    for name, minimum in MINIMUM_DEPENDENCIES.items():
        installed = installed_distribution_version(name)
        tested = TESTED_DEPENDENCIES[name]
        policy[name] = {
            "installed": installed,
            "minimum": minimum,
            "tested": tested,
            "meets_minimum": (
                installed is not None and version_at_least(installed, minimum)
            ),
            "matches_tested": installed == tested,
        }
    return policy


def dependency_versions(policy: dict[str, dict[str, object]]) -> dict[str, str]:
    return {
        name: str(values["installed"] or "not installed")
        for name, values in policy.items()
    }


def tested_dependency_summary() -> str:
    return ", ".join(
        f"{name}=={version}" for name, version in TESTED_DEPENDENCIES.items()
    )


def current_dependency_summary(
    policy: dict[str, dict[str, object]],
) -> str:
    return ", ".join(
        f"{name}=={values['installed'] or 'not installed'}"
        for name, values in policy.items()
    )


def main() -> int:
    args = build_parser().parse_args()
    policy = dependency_policy()
    checks: dict[str, object] = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "windows": os.name == "nt",
        "dependencies": dependency_versions(policy),
        "dependency_policy": policy,
        "issues": [],
    }
    issues = checks["issues"]
    assert isinstance(issues, list)

    if sys.version_info < (3, 11):
        issues.append("Python 3.11 or later is required")
    if os.name != "nt":
        issues.append("SAP GUI automation requires Windows")
    for name, values in policy.items():
        installed = values["installed"]
        minimum = values["minimum"]
        tested = values["tested"]
        if installed is None:
            issues.append(
                f"Dependency missing: {name}>={minimum} is required; "
                f"the tested baseline uses {name}=={tested}"
            )
        elif not values["meets_minimum"]:
            issues.append(
                f"Dependency version too old: {name}=={installed} is installed; "
                f"{name}>={minimum} is required. The tested baseline uses {name}=={tested}"
            )

    if MB5B_IMPORT_ERROR is not None:
        issues.append(f"MB5B module import error: {type(MB5B_IMPORT_ERROR).__name__}: {MB5B_IMPORT_ERROR}")
    elif mb5b_export.WINDOWS_IMPORT_ERROR is not None:
        issues.append(f"Windows automation dependency error: {mb5b_export.WINDOWS_IMPORT_ERROR}")

    if args.input is not None and MB5B_IMPORT_ERROR is None:
        input_path = args.input.expanduser().resolve()
        checks["input"] = str(input_path)
        try:
            assert mb5b_export is not None
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
            assert mb5b_export is not None
            output_dir.mkdir(parents=True, exist_ok=True)
            session = mb5b_export.connect_sap_with_access_helper(output_dir)
            checks["sap"] = mb5b_export.sap_info(session)
        except Exception as exc:
            issues.append(f"SAP session error: {type(exc).__name__}: {exc}")

    version_drift = [
        name for name, values in policy.items() if not values["matches_tested"]
    ]
    checks["version_drift"] = version_drift
    if issues and version_drift:
        issues.append(
            "Environment checks failed while dependency versions differ from the "
            f"tested baseline. Tested baseline: {tested_dependency_summary()}. "
            f"Current environment: {current_dependency_summary(policy)}. "
            "Reproduce with scripts/requirements.txt before diagnosing further."
        )

    checks["ok"] = not issues
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
