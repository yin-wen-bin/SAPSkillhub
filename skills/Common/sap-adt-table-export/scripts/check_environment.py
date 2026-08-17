"""Report the minimum and tested dependency baseline without exposing secrets."""

from __future__ import annotations

import importlib.metadata
import json
import sys

from adt_table_export import MINIMUM_DEPENDENCIES, TESTED_DEPENDENCIES


def version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split(".")[:3])


def main() -> int:
    results = []
    failed = False
    for package, minimum in MINIMUM_DEPENDENCIES.items():
        tested = TESTED_DEPENDENCIES[package]
        try:
            current = importlib.metadata.version(package)
            meets_minimum = version_tuple(current) >= version_tuple(minimum)
        except importlib.metadata.PackageNotFoundError:
            current = None
            meets_minimum = False
        failed = failed or not meets_minimum
        results.append(
            {
                "package": package,
                "minimum": minimum,
                "tested": tested,
                "current": current,
                "meets_minimum": meets_minimum,
                "matches_tested_baseline": current == tested,
            }
        )
    print(json.dumps({"ok": not failed, "dependencies": results}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
