---
name: sap-mb5b-export
description: Automate SAP GUI for Windows transaction MB5B from an Excel list of plants and storage locations, export one workbook per target, add the storage-location column, and merge successful exports per plant. Use when Codex needs to run or diagnose MB5B Excel exports, perform a dry run, validate a new SAP GUI locale, or inspect language-independent SAP and Windows dialog controls.
---

# SAP MB5B Export

Use the bundled Python workflow. Do not recreate the SAP automation with VBS or PowerShell.

## Required Workflow

1. Read [references/environment.md](references/environment.md) before the first run on a machine or after an SAP GUI or Windows upgrade.
2. Run `scripts/check_environment.py` with the input workbook. Add `--require-sap` before a live run.
3. Run `scripts/mb5b_export.py` with `--dry-run` and review all individual and merged output paths.
4. On a new SAP GUI language, version, theme, or Windows scale, run a live `--limit 1` test before processing all rows.
5. Run the complete export only after the one-row file has the expected filename and `Data!D1` header.
6. Report exit code `2` as partial success and use the log to identify failed plant/storage pairs.

## Commands

```powershell
python scripts/check_environment.py --input "C:\work\保管場所.xlsx" --require-sap

python scripts/mb5b_export.py `
  --input "C:\work\保管場所.xlsx" `
  --date 2026-02-28 `
  --dry-run

python scripts/mb5b_export.py `
  --input "C:\work\保管場所.xlsx" `
  --date 2026-02-28 `
  --limit 1
```

Pass `--overwrite` only when the user explicitly permits replacing existing individual and merged files. Use `--output-dir` to keep test exports separate from production files.

## Language Independence

- Use SAP technical control IDs and Windows control structure only.
- Never add window-title, button-label, translated-message, OCR, or fixed-coordinate matching to execution logic.
- Treat labels as diagnostic data only.
- Stop on an ambiguous multi-button dialog. Do not guess which action means allow, save, or overwrite.
- Use `--inspect-ui --output-dir <directory>` passively while the user has the unsupported dialog open. This writes screenshots and a control-tree JSON without clicking anything.
- Preserve the one-submit-per-state rule. Do not retry clicks in a loop.

## Output Contract

- Individual: `MB5B_<plant>_<storage>_<YYYYMMDD>.xlsx`
- Merged: `MB5B_<plant>_<YYYYMMDD>.xlsx`
- Insert column D when needed, set `D1` to the configured storage header, and fill data rows with the target storage code.
- Keep one header row in each plant merge and append only successful individual files in input order.
- Return `0` for full success, `1` for preflight/startup failure, and `2` for partial export or merge failure.

Do not bulk-delete files or directories. Keep runtime logs and diagnostics local and out of source control.
