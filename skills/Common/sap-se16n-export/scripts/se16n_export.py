from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "lib"))

from sapskillhub_export.core import (  # noqa: E402
    IDENTIFIER,
    ChunkRange,
    Filter,
    Selection,
    connect_sap_session,
    export_alv,
    find_required,
    grid_column_ids,
    grouped_filter_semantics,
    load_control_profile,
    load_selection,
    merge_workbooks,
    policy_for,
    recursive_chunks,
    rewrite_workbook_with_technical_headers,
    session_identity,
    set_key_verified,
    set_text_verified,
    sha256,
    status_error,
    utc_now,
    validate_chunk_coverage,
    wait_ready,
    write_manifest,
)

DEFAULT_PROFILE = Path(__file__).resolve().parents[1] / "references" / "control-profile.json"


def control_text(control: Any) -> str:
    for attribute in ("Text", "Name", "Key"):
        try:
            value = str(getattr(control, attribute)).strip()
            if value:
                return value
        except Exception:
            continue
    return ""


def locate_selection_row(
    session: Any, field: str, profile: dict[str, Any]
) -> int:
    table = find_required(session, profile["selection_table"])
    rows = profile["selection_rows"]
    try:
        total = int(table.RowCount)
        visible_count = int(table.VisibleRowCount)
    except Exception as exc:
        raise RuntimeError("cannot read SE16N selection table dimensions") from exc
    if total < 1 or visible_count < 1:
        raise RuntimeError("SE16N selection table has no rows")
    for start in range(0, total, visible_count):
        try:
            table.VerticalScrollbar.Position = start
        except Exception as exc:
            if start:
                raise RuntimeError("cannot scroll SE16N selection table") from exc
        wait_ready(session)
        visible_rows = min(visible_count, total - start)
        for visible_row in range(visible_rows):
            try:
                candidate = control_text(
                    find_required(
                        session, rows["field"].format(row=visible_row)
                    )
                ).upper()
            except RuntimeError:
                continue
            if candidate == field.upper():
                return visible_row
    raise RuntimeError(f"SE16N technical selection field not found: {field}")


def apply_multiple_selection(
    session: Any, filters: Sequence[Filter], profile: dict[str, Any]
) -> None:
    multiple = profile.get("multiple_selection")
    if not multiple:
        raise RuntimeError("control profile has no SE16N multiple-selection dialog")
    rows = multiple["rows"]
    for index, item in enumerate(filters):
        for name, value in (
            ("sign", item.sign),
            ("option", item.option),
            ("low", item.low),
            ("high", item.high),
        ):
            if not value and name == "high":
                continue
            template = rows.get(name)
            if not template:
                raise RuntimeError(
                    f"control profile cannot enter multiple-selection {name}"
                )
            setter = (
                set_key_verified if name in {"sign", "option"} else set_text_verified
            )
            setter(session, template.format(row=index), value)
    find_required(session, multiple["accept"]).Press()
    wait_ready(session)


def apply_filters(session: Any, filters: Sequence[Filter], profile: dict[str, Any]) -> None:
    """Locate SE16N fields by technical name, enter values, and verify controls."""
    grouped: dict[str, list[Filter]] = {}
    for item in filters:
        grouped.setdefault(item.field, []).append(item)
    rows = profile["selection_rows"]
    for field, conditions in grouped.items():
        visible_row = locate_selection_row(session, field, profile)
        direct = (
            len(conditions) == 1
            and conditions[0].sign == "I"
            and conditions[0].option in {"EQ", "BT"}
        )
        if direct:
            item = conditions[0]
            set_text_verified(session, rows["low"].format(row=visible_row), item.low)
            if item.option == "BT":
                set_text_verified(
                    session, rows["high"].format(row=visible_row), item.high
                )
            continue
        find_required(
            session, rows["multiple"].format(row=visible_row)
        ).Press()
        wait_ready(session)
        apply_multiple_selection(session, conditions, profile)


def run_one(session: Any, table: str, selection: Selection, maxhits: int, output: Path, profile: dict[str, Any], overwrite: bool) -> int:
    command = find_required(session, profile["command"])
    command.Text = "/nSE16N"
    find_required(session, profile["main_window"]).SendVKey(0)
    wait_ready(session)
    set_text_verified(session, profile["table"], table)
    find_required(session, profile["main_window"]).SendVKey(0)
    wait_ready(session)
    apply_filters(session, selection.filters, profile)
    set_text_verified(session, profile["maxhits"], str(maxhits))
    find_required(session, profile["execute"]).Press()
    wait_ready(session)
    error = status_error(session)
    if error:
        raise RuntimeError(f"SAP status error: {error}")
    grid = find_required(session, profile["grid"])
    technical_columns = grid_column_ids(grid)
    export_alv(session, profile["grid"], output, overwrite)
    return rewrite_workbook_with_technical_headers(output, technical_columns)


def with_chunk(selection: Selection, field: str, low: str, high: str) -> Selection:
    filters = tuple(
        item
        for item in selection.filters
        if not (item.field == field and item.sign == "I")
    ) + (Filter(field, "I", "BT", low, high),)
    return replace(selection, filters=filters)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe SE16N SAP GUI export with validation and chunking")
    parser.add_argument("--table", default="MARA")
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--where", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--mode", choices=("validate", "full"), default="validate")
    parser.add_argument("--maxhits", type=int, help="Legacy compatibility: implies full mode")
    parser.add_argument("--chunk-size", type=int, default=50_000)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--file")
    parser.add_argument("--system", default="")
    parser.add_argument("--client", default="")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = utc_now()
    table = args.table.strip().upper()
    output_dir = args.output_dir.expanduser().resolve()
    name = Path(args.file or table.lower()).stem
    parts: list[Path] = []
    manifest_path = output_dir / f"{name}.manifest.json"
    log_path = output_dir / f"{name}.log"
    mode = args.mode
    chunks: list[dict[str, Any]] = []
    sap_identity: dict[str, str] = {}
    try:
        if not IDENTIFIER.fullmatch(table):
            raise ValueError(f"invalid SAP table name: {table!r}")
        selection = load_selection(args.selection_file, args.where, args.exclude)
        mode = "full" if args.maxhits is not None else args.mode
        if args.maxhits is not None and args.maxhits < 1:
            raise ValueError("legacy maxhits must be positive")
        if args.maxhits is not None and args.maxhits > 50_000:
            print("WARN: legacy --maxhits above 50000 is converted to 50000-row chunking", file=sys.stderr)
        chunk_size = min(args.chunk_size, 50_000)
        maxhits = 100 if mode == "validate" else chunk_size
        if maxhits < 1:
            raise ValueError("maxhits must be positive")
        chunk, keys = policy_for(table, selection) if mode == "full" else (None, selection.key_fields)
        final_xlsx = output_dir / f"{name}.xlsx"
        final_csv = output_dir / f"{name}.csv"
        artifact_patterns = (f"{name}.part-*.xlsx", f"{name}.probe-*.xlsx")
        prior_artifacts = [path for pattern in artifact_patterns for path in output_dir.glob(pattern)] if output_dir.exists() else []
        for target in (final_xlsx, final_csv, manifest_path, log_path, *prior_artifacts):
            if target.exists() and not args.overwrite:
                raise FileExistsError(f"output exists; pass --overwrite: {target}")
        planned = {
            "table": table, "mode": mode, "maxhits": maxhits,
            "filters": [asdict(item) for item in selection.filters],
            "semantics": grouped_filter_semantics(selection.filters),
            "chunk": asdict(chunk) if chunk else None, "key_fields": list(keys),
        }
        if args.dry_run:
            print(json.dumps(planned, ensure_ascii=False, indent=2))
            return 0
        output_dir.mkdir(parents=True, exist_ok=True)
        if args.overwrite:
            for target in (final_xlsx, final_csv, manifest_path, log_path):
                if target.exists():
                    target.unlink()
            for target in prior_artifacts:
                target.unlink()
        log_path.write_text(f"{started} start sap-se16n-export table={table} mode={mode}\n", encoding="utf-8")
        if mode == "full" and chunk and not keys:
            raise ValueError("full export requires key_fields")
        profile = load_control_profile(args.profile)
        session = connect_sap_session(args.system, args.client)
        sap_identity = session_identity(session)
        if mode == "validate":
            part = output_dir / f"{name}.part-0001.xlsx"
            count = run_one(session, table, selection, 100, part, profile, args.overwrite)
            chunks.append({"part": part.name, "rows": count})
            parts.append(part)
        elif chunk:
            probe_number = 0
            def probe(current: ChunkRange, limit: int) -> int:
                nonlocal probe_number
                probe_number += 1
                path = output_dir / f"{name}.probe-{probe_number:04d}.xlsx"
                count = run_one(session, table, with_chunk(selection, chunk.field, current.low, current.high), limit, path, profile, args.overwrite)
                chunks.append({"probe": path.name, "low": current.low, "high": current.high, "rows": count})
                return count
            leaves = recursive_chunks(chunk, probe, chunk_size)
            validate_chunk_coverage([item[0] for item in leaves], chunk)
            for index, (current, expected_count) in enumerate(leaves, 1):
                path = output_dir / f"{name}.part-{index:04d}.xlsx"
                count = run_one(session, table, with_chunk(selection, chunk.field, current.low, current.high), chunk_size, path, profile, args.overwrite)
                if count != expected_count:
                    raise RuntimeError(f"row count changed between probe and final export for {current.low}..{current.high}")
                parts.append(path)
                chunks.append({"part": path.name, "low": current.low, "high": current.high, "rows": count})
        else:
            probe = output_dir / f"{name}.probe-0001.xlsx"
            count = run_one(session, table, selection, 50_001, probe, profile, args.overwrite)
            chunks.append({"probe": probe.name, "rows": count})
            if count > 50_000:
                raise ValueError("unknown table exceeded 50000 rows; provide chunk.field/type/low/high and key_fields in JSON")
            part = output_dir / f"{name}.part-0001.xlsx"
            final_count = run_one(session, table, selection, 50_000, part, profile, args.overwrite)
            if final_count != count:
                raise RuntimeError("row count changed between overflow probe and final export")
            parts.append(part)
            chunks.append({"part": part.name, "rows": final_count})
        merged = merge_workbooks(parts, final_xlsx, final_csv, keys or selection.sort, selection.sort, args.overwrite, selection.columns)
        finished = utc_now()
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(f"{finished} complete rows={merged['rows']}\n")
        evidence_files = parts + sorted(output_dir.glob(f"{name}.probe-*.xlsx")) + [final_xlsx, final_csv, log_path]
        outputs = {path.name: sha256(path) for path in evidence_files}
        manifest = {
            "schema_version": 1, "skill": "sap-se16n-export", "transaction": "SE16N",
            "mode": mode, "sap": sap_identity, "input": planned,
            "sap_selection": [asdict(item) for item in selection.filters], "local_filters": [],
            "layout_fields": merged["columns"], "chunks": chunks, "final_rows": merged["rows"],
            "currency_totals": {}, "started_at": started, "finished_at": finished,
            "outputs_sha256": outputs, "status": "complete",
        }
        write_manifest(manifest_path, manifest, args.overwrite)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        if args.dry_run:
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(f"{utc_now()} ERROR {type(exc).__name__}: {exc}\n")
            if not manifest_path.exists() or args.overwrite:
                data_existing = [path for path in parts if path.exists()] + sorted(output_dir.glob(f"{name}.probe-*.xlsx"))
                existing = list(data_existing)
                if log_path.exists():
                    existing.append(log_path)
                write_manifest(manifest_path, {
                    "schema_version": 1, "skill": "sap-se16n-export", "transaction": "SE16N",
                    "mode": mode, "sap": sap_identity,
                    "input": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                    "sap_selection": [], "local_filters": [], "layout_fields": [], "chunks": chunks,
                    "final_rows": 0, "currency_totals": {}, "started_at": started, "finished_at": utc_now(),
                    "outputs_sha256": {path.name: sha256(path) for path in existing},
                    "status": "partial" if data_existing else "failed", "error": f"{type(exc).__name__}: {exc}",
                }, args.overwrite)
        except Exception as manifest_exc:
            print(f"WARN: could not write failure manifest: {manifest_exc}", file=sys.stderr)
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
