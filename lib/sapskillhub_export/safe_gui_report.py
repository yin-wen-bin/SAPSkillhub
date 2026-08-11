"""Fail-closed primitives for SAP GUI reports that must never post."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import openpyxl

from .core import (
    export_alv,
    find_required,
    grid_column_ids,
    read_workbook_rows,
    rewrite_workbook_with_technical_headers,
    set_text_verified,
    status_error,
    wait_ready,
)


class SafetyViolation(RuntimeError):
    """A posting/update path or ambiguous SAP state was observed."""


@dataclass(frozen=True)
class ReportExport:
    path: Path
    row_count: int
    columns: tuple[str, ...]
    totals_by_currency: Mapping[str, str]


def _selected(control: Any) -> bool:
    for attribute in ("Selected", "Checked"):
        if hasattr(control, attribute):
            return bool(getattr(control, attribute))
    raise SafetyViolation("cannot read checkbox state from a safety control")


def set_checkbox_verified(session: Any, control_id: str, selected: bool) -> None:
    control = find_required(session, control_id)
    if hasattr(control, "Selected"):
        control.Selected = selected
    elif hasattr(control, "Checked"):
        control.Checked = selected
    else:
        raise SafetyViolation(f"safety control is not a checkbox: {control_id}")
    if _selected(control) is not selected:
        raise SafetyViolation(f"SAP rejected safety state for {control_id}")


def _window_count(session: Any) -> int:
    try:
        return int(session.Children.Count)
    except Exception:
        return 1


class SafeGuiReportRunner:
    """Execute one profiled report after proving non-posting controls."""

    def __init__(self, session: Any, profile: Mapping[str, Any], transaction: str):
        self.session = session
        self.profile = profile
        if profile.get("schema_version") != 1:
            raise ValueError("unsupported control profile schema")
        if str(profile.get("transaction", "")).upper() != transaction.upper():
            raise ValueError("control profile transaction mismatch")
        self.transaction = transaction.upper()

    def open_transaction(self) -> None:
        command = find_required(self.session, str(self.profile["command"]))
        command.Text = f"/n{self.transaction}"
        find_required(self.session, str(self.profile["main_window"])).SendVKey(0)
        wait_ready(self.session)

    def apply_fields(self, values: Mapping[str, str]) -> dict[str, str]:
        controls = self.profile.get("fields", {})
        if not isinstance(controls, dict):
            raise ValueError("profile fields must be an object")
        accepted: dict[str, str] = {}
        for name, value in values.items():
            if value == "":
                continue
            control_id = controls.get(name)
            if not control_id:
                raise RuntimeError(f"control profile cannot enter field: {name}")
            set_text_verified(self.session, str(control_id), value)
            accepted[name] = value
        return accepted

    def enforce_mode(self, mode: str) -> None:
        modes = self.profile.get("modes", {})
        config = modes.get(mode) if isinstance(modes, dict) else None
        if not isinstance(config, dict):
            raise SafetyViolation(f"control profile does not define safe mode: {mode}")
        required_true = config.get("required_true", [])
        required_false = config.get("required_false", [])
        if not required_true and mode not in {"existing-log", "existing_log"}:
            raise SafetyViolation(f"safe mode {mode} has no required test/simulation control")
        for control_id in required_true:
            set_checkbox_verified(self.session, str(control_id), True)
        for control_id in required_false:
            set_checkbox_verified(self.session, str(control_id), False)
        for control_id in self.profile.get("forbidden_controls", []):
            try:
                control = self.session.FindById(str(control_id))
            except Exception:
                continue
            if _selected(control):
                raise SafetyViolation(f"posting/update control is active: {control_id}")
        if _window_count(self.session) != 1:
            raise SafetyViolation("unexpected dialog is open before report execution")

    def execute(self, mode: str) -> None:
        config = self.profile["modes"][mode]
        execute_id = config.get("execute") or self.profile.get("execute")
        if not execute_id:
            raise ValueError(f"profile has no execute control for mode {mode}")
        find_required(self.session, str(execute_id)).Press()
        wait_ready(self.session)
        error = status_error(self.session)
        if error:
            raise RuntimeError(f"SAP status error: {error}")
        if _window_count(self.session) != 1:
            raise SafetyViolation("unexpected dialog appeared after report execution")

    def export(self, output: Path, *, overwrite: bool = False) -> ReportExport:
        count_control = self.profile.get("result_count")
        if count_control:
            raw_count = str(getattr(find_required(self.session, str(count_control)), "Text", "")).strip()
            try:
                expected_count = int(raw_count.replace(",", ""))
            except ValueError as exc:
                raise RuntimeError("cannot verify result count") from exc
            if expected_count == 0:
                if output.exists() and not overwrite:
                    raise FileExistsError(f"output exists; pass --overwrite: {output}")
                output.parent.mkdir(parents=True, exist_ok=True)
                book = openpyxl.Workbook()
                sheet = book.active
                sheet.title = "Data"
                columns = tuple(str(value) for value in self.profile.get("required_columns", []))
                sheet.append(list(columns))
                book.save(output)
                book.close()
                return ReportExport(output, 0, columns, {})
        grid_id = str(self.profile["grid"])
        grid = find_required(self.session, grid_id)
        technical_columns = grid_column_ids(grid)
        export_alv(self.session, grid_id, output, overwrite)
        row_count = rewrite_workbook_with_technical_headers(output, technical_columns)
        columns, rows = read_workbook_rows(output)
        required = tuple(str(value) for value in self.profile.get("required_columns", []))
        missing = [value for value in required if value not in columns]
        if missing:
            raise RuntimeError(f"required report column(s) missing: {', '.join(missing)}")
        if count_control and row_count != expected_count:
            raise RuntimeError(
                f"result count mismatch: SAP={expected_count}, export={row_count}"
            )
        totals = self._totals(rows)
        return ReportExport(output, row_count, tuple(columns), totals)

    def _totals(self, rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
        amount_field = str(self.profile.get("amount_field", ""))
        currency_field = str(self.profile.get("currency_field", ""))
        if not amount_field or not currency_field:
            return {}
        totals: dict[str, Decimal] = {}
        for row in rows:
            currency = str(row.get(currency_field, "") or "").strip()
            if not currency:
                raise RuntimeError("blank currency in exported report")
            try:
                amount = Decimal(str(row.get(amount_field, 0) or 0).replace(",", ""))
            except InvalidOperation as exc:
                raise RuntimeError(f"invalid report amount: {row.get(amount_field)!r}") from exc
            totals[currency] = totals.get(currency, Decimal("0")) + amount
        return {currency: str(amount) for currency, amount in sorted(totals.items())}
