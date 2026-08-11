"""Run bounded SE16N exports sequentially without reusing transaction state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from se16n_export import main as export_main  # noqa: E402


ALLOWED = {
    "table": "--table",
    "selection_file": "--selection-file",
    "mode": "--mode",
    "maxhits": "--maxhits",
    "chunk_size": "--chunk-size",
    "output_dir": "--output-dir",
    "file": "--file",
    "system": "--system",
    "client": "--client",
    "profile": "--profile",
}


def job_argv(job: dict[str, Any], overwrite: bool) -> list[str]:
    unknown = sorted(set(job) - set(ALLOWED) - {"where", "exclude"})
    if unknown:
        raise ValueError(f"unsupported batch job field(s): {', '.join(unknown)}")
    if not str(job.get("table", "")).strip():
        raise ValueError("every batch job requires table")
    result: list[str] = []
    for field, option in ALLOWED.items():
        value = job.get(field)
        if value is not None and value != "":
            result.extend((option, str(value)))
    for field in ("where", "exclude"):
        values = job.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"batch job {field} must be a list of strings")
        for value in values:
            result.extend((f"--{field}", value))
    if overwrite:
        result.append("--overwrite")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SE16N jobs sequentially with /nSE16N reset")
    parser.add_argument("--batch-file", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.batch_file.read_text(encoding="utf-8-sig"))
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs, list) or not jobs or any(not isinstance(job, dict) for job in jobs):
        raise ValueError("batch JSON must contain a non-empty jobs array")
    outcomes: list[dict[str, Any]] = []
    for index, job in enumerate(jobs, 1):
        code = export_main(job_argv(job, args.overwrite))
        outcomes.append({"index": index, "table": job.get("table"), "exit_code": code})
        if code and not args.continue_on_error:
            break
    print(json.dumps({"jobs": outcomes, "complete": len(outcomes) == len(jobs) and all(not item["exit_code"] for item in outcomes)}, ensure_ascii=False, indent=2))
    return 0 if len(outcomes) == len(jobs) and all(not item["exit_code"] for item in outcomes) else 2


if __name__ == "__main__":
    raise SystemExit(main())
