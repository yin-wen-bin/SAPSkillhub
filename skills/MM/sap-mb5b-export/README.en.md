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

The implementation uses SAP technical control IDs and Windows control structure so that execution does not depend on translated labels or fixed screen coordinates.

When SAP GUI shows a standard SAP GUI Scripting security prompt, this skill confirms it only after matching known security prompt text and the standard `OK` control. Business dialogs, overwrite confirmations, and other multi-button dialogs still stop safely or follow the existing export state machine.

## Use Cases

- Export stock-on-posting-date data for many plant and storage-location combinations.
- Produce consistently named workbooks for downstream reconciliation or reporting.
- Add the storage location to MB5B data before combining multiple exports.
- Diagnose SAP GUI compatibility after a language, theme, version, or display-scale change.
- Perform a dry run to validate targets and output paths without opening SAP.

## Prerequisites

- Windows with SAP GUI for Windows installed.
- SAP GUI scripting enabled on both the client and server.
- An authenticated SAP session with authorization to run MB5B and export results.
- Python with the packages listed in `scripts/requirements.txt`.
- An input Excel workbook whose first two columns contain plant and storage-location values.
- Review `references/environment.md` before the first live run on a machine or after an SAP GUI or Windows upgrade.

## Dependency Version Policy

`scripts/requirements.txt` keeps the tested baseline pinned:

```text
openpyxl==3.1.5
pywin32==311
pywinauto==0.6.9
```

`scripts/check_environment.py` accepts installed dependency versions that meet or exceed the minimum requirements and runs the normal environment, input, and optional SAP session checks first. If those checks pass, no package update or downgrade is required. If the checks fail while the installed versions differ from the tested baseline, the script reports both the current versions and the tested baseline and recommends reproducing with `scripts/requirements.txt`.

## Usage

Run the environment check first:

```powershell
python scripts/check_environment.py `
  --input "<LOCAL_WORKSPACE>\storage-locations.xlsx" `
  --require-sap
```

Preview all targets and output paths without operating SAP:

```powershell
python scripts/mb5b_export.py `
  --input "<LOCAL_WORKSPACE>\storage-locations.xlsx" `
  --date 2026-02-28 `
  --dry-run
```

On a new SAP GUI environment, run one live target before the complete batch:

```powershell
python scripts/mb5b_export.py `
  --input "<LOCAL_WORKSPACE>\storage-locations.xlsx" `
  --date 2026-02-28 `
  --limit 1
```

After checking the resulting filename and the `Data!D1` header, rerun without `--limit` for the complete export.

## Inputs

| Input | Required | Description |
| --- | --- | --- |
| `--input` | Yes | Excel workbook containing plant and storage-location pairs. |
| `--date` | Yes | Posting date in `YYYY-MM-DD` format. |
| `--output-dir` | No | Directory for individual exports, merged files, logs, and diagnostics. |
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

## Limitations

- The skill supports SAP GUI for Windows; it does not automate SAP GUI for HTML or SAP Fiori apps.
- Execution relies on technical control IDs. It intentionally does not use window titles, translated button text, OCR, or fixed coordinates.
- It only auto-confirms two SAP GUI Scripting security prompts: `A script is attempting to access SAP GUI.` and `A script is opening a connection to system:`.
- Ambiguous multi-button dialogs stop the run. The automation never guesses which action means allow, save, or overwrite.
- Existing output files are preserved unless `--overwrite` is explicitly supplied.
- A live batch should not be started until the dry run and one-target validation have both succeeded.

## Examples

Export all targets to a separate test directory:

```powershell
python scripts/mb5b_export.py `
  --input "<LOCAL_WORKSPACE>\storage-locations.xlsx" `
  --date 2026-02-28 `
  --output-dir "<LOCAL_WORKSPACE>\mb5b-test"
```

If the run returns exit code `2`, keep the successful workbooks and use the log to identify only the failed plant/storage pairs. Do not rerun successful targets with `--overwrite` unless replacement is intended.
