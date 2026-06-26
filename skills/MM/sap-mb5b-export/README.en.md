---
title: SAP MB5B Export and Merge
summary: Automate MB5B exports for plant and storage-location targets, enrich each workbook, and merge successful exports by plant.
tags:
  - MB5B
  - inventory
  - Excel
  - SAP GUI automation
transactions:
  - MB5B
systems:
  - SAP ERP
  - SAP S/4HANA
  - SAP GUI for Windows
---

## Overview

This skill automates transaction MB5B in SAP GUI for Windows. It reads plant and storage-location pairs from an Excel workbook, runs one export for each target, adds the storage location to the exported data, and merges successful exports into one workbook per plant.

The implementation uses SAP technical control IDs and Windows control structure so that execution does not depend on translated labels or fixed screen coordinates. It also enforces the MB5B list scope for non-hierarchical totals before execution.

## Use Cases

- Export stock-on-posting-date data for many plant and storage-location combinations.
- Produce consistently named workbooks for downstream reconciliation or reporting.
- Add the storage location to MB5B data before combining multiple exports.
- Diagnose SAP GUI compatibility after a language, theme, version, or display-scale change.
- Perform a dry run to validate targets and output paths without opening SAP.
- Handle SAP users whose date entry format is `YYYY.MM.DD`, `YYYY/MM/DD`, `YYYY-MM-DD`, or `YYYYMMDD`.

## Prerequisites

- Windows with SAP GUI for Windows installed.
- SAP GUI scripting enabled on both the client and server.
- An authenticated SAP session with authorization to run MB5B and export results.
- Python with the packages listed in `scripts/requirements.txt`.
- An input Excel workbook whose first two columns contain plant and storage-location values.
- Review `references/environment.md` before the first live run on a machine or after an SAP GUI or Windows upgrade.

## Usage

Run the environment check first:

```powershell
python scripts/check_environment.py `
  --input "C:\work\storage-locations.xlsx" `
  --require-sap
```

Preview all targets and output paths without operating SAP:

```powershell
python scripts/mb5b_export.py `
  --input "C:\work\storage-locations.xlsx" `
  --date 2026-02-28 `
  --dry-run
```

On a new SAP GUI environment, run one live target before the complete batch:

```powershell
python scripts/mb5b_export.py `
  --input "C:\work\storage-locations.xlsx" `
  --date 2026-02-28 `
  --sap-date-format dot `
  --limit 1
```

After checking the resulting filename and the `Data!D1` header, rerun without `--limit` for the complete export.

## Inputs

| Input | Required | Description |
| --- | --- | --- |
| `--input` | Yes | Excel workbook containing plant and storage-location pairs. |
| `--date` | Yes | Posting date in `YYYY-MM-DD` format. |
| `--sap-date-format` | No | Date format entered into SAP: `slash` (default), `dot`, `hyphen`, or `compact`. Output filenames always use `YYYYMMDD`. |
| `--output-dir` | No | Directory for individual exports, merged files, logs, and diagnostics. |
| `--sheet` | No | Worksheet name. Defaults to `Sheet1`; if absent, the first worksheet is used by the reader. |
| `--plant-column` | No | Plant column header. Defaults to `プラント`; use this for files with headers such as `Plant`. |
| `--storage-column` | No | Storage-location column header. Defaults to `保管場所`; use this for files with headers such as `S.Loc`. |
| `--storage-header` | No | Header inserted into output column D. Defaults to `保管場所`. |
| `--limit` | No | Process only the first N targets; use `1` for initial live validation. |
| `--dry-run` | No | Validate targets and paths without controlling SAP. |
| `--overwrite` | No | Replace existing output files; use only with explicit permission. |
| `--inspect-ui` | No | Capture passive UI diagnostics for an unsupported dialog without clicking it. |

## Outputs

| Output | Naming contract | Description |
| --- | --- | --- |
| Individual workbook | `MB5B_<plant>_<storage>_<YYYYMMDD>.xlsx` | One enriched export for a successful plant/storage target. |
| Plant workbook | `MB5B_<plant>_<YYYYMMDD>.xlsx` | Successful individual exports merged in input order with one header row. |
| Storage column | `Data!D:D` | Column D is inserted when needed, `D1` receives the configured header, and data rows receive the target storage code. |
| Runtime log | Local output directory | Records processed targets and failures without being committed to the repository. |
| UI diagnostics | Diagnostics directory | Optional screenshot and control-tree JSON created by `--inspect-ui`. |

The process returns exit code `0` for full success, `1` for preflight or startup failure, and `2` for partial export or merge failure.

## SAP Selection Defaults

Before each MB5B execution the automation sets these technical controls:

- `wnd[0]/usr/radLGBST` for storage-location/batch stock.
- `wnd[0]/usr/chkPA_SUMFL` for Totals Only - Non-Hierarchical Representation.
- `wnd[0]/usr/chkXSUM` is cleared when present to avoid hierarchical totals.

If SAP's frontend Excel export flow does not produce a file, the script can write the visible SAP classical list to an `.xlsx` workbook from SAP `GuiLabel` technical IDs and then applies the same storage-column enrichment and plant merge contract.

## Limitations

- The skill supports SAP GUI for Windows; it does not automate SAP GUI for HTML or SAP Fiori apps.
- Execution relies on technical control IDs. It intentionally does not use window titles, translated button text, OCR, or fixed coordinates.
- Ambiguous multi-button dialogs stop the run. The automation never guesses which action means allow, save, or overwrite.
- Existing output files are preserved unless `--overwrite` is explicitly supplied.
- A live batch should not be started until the dry run and one-target validation have both succeeded.

## Examples

Export all targets to a separate test directory:

```powershell
python scripts/mb5b_export.py `
  --input "C:\work\storage-locations.xlsx" `
  --date 2026-02-28 `
  --sap-date-format slash `
  --output-dir "C:\work\mb5b-test"
```

Export a workbook whose headers are `Plant` and `S.Loc` for a user whose SAP date format is `YYYY.MM.DD`:

```powershell
python scripts/mb5b_export.py `
  --input "C:\work\StorageLocation.xlsx" `
  --date 2020-12-31 `
  --sap-date-format dot `
  --plant-column "Plant" `
  --storage-column "S.Loc"
```

If the run returns exit code `2`, keep the successful workbooks and use the log to identify only the failed plant/storage pairs. Do not rerun successful targets with `--overwrite` unless replacement is intended.
