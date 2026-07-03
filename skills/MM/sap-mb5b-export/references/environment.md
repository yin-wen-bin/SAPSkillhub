# Environment and Compatibility

## Runtime

- Windows 10 or 11
- SAP GUI for Windows with GUI Scripting enabled
- One authenticated SAP connection and session
- Permission to run MB5B and export XLSX files
- Python 3.13 validation baseline
- Packages from `scripts/requirements.txt`

## Dependency Version Policy

`scripts/requirements.txt` records the tested baseline for SAP GUI and Windows
dialog automation. Keep these versions pinned for reproducible installs.

`scripts/check_environment.py` allows installed dependency versions that meet or
exceed the minimum tested versions and runs the normal environment checks first.
If those checks pass, no package change is required. If the checks fail while the
installed versions differ from the tested baseline, the checker reports both the
tested baseline and the current versions so the user can reproduce with
`scripts/requirements.txt` before further diagnosis.

Install dependencies with:

```powershell
python -m pip install -r scripts/requirements.txt
```

## Input Workbook

The default worksheet is `Sheet1`. If it does not exist, the first worksheet is used. Defaults:

- Plant column: `プラント`
- Storage-location column: `保管場所`
- Added output header: `保管場所`

Override all three labels with `--plant-column`, `--storage-column`, and `--storage-header`. Store codes as Excel text when leading zeros matter.

## Language-Independent Boundary

The automation supports arbitrary display languages when the SAP GUI and Windows dialog control structures remain compatible. It does not claim compatibility with every SAP GUI or Windows release.

Execution decisions use:

- SAP GUI Scripting technical IDs
- top-level window handles and creation sequence
- window class and parent/process metadata
- control type, `control_id`, and `AutomationId`
- a strict export, save, overwrite, and output-detection state machine

Displayed titles, button captions, messages, and OCR are excluded from selectors. An unknown security prompt with multiple buttons is deliberately left untouched.

## Diagnostic Mode

Open the problematic dialog manually, then run:

```powershell
python scripts/mb5b_export.py --inspect-ui --output-dir "<LOCAL_WORKSPACE>\diagnostics"
```

The command does not click the UI. It writes `ui-tree.json` and screenshots for visible windows. Treat these files as potentially sensitive because titles may include local paths or SAP context.

## Live-Run Checklist

1. Close existing target workbooks in Excel or WPS.
2. Confirm the SAP session is idle and MB5B is authorized.
3. Run the environment checker.
4. Run `--dry-run`.
5. Run `--limit 1` after locale, SAP GUI, Windows, theme, or display-scale changes.
6. Check the individual filename, `Data!D1`, storage values, and log.
7. Run all rows only after the compatibility test succeeds.

The skill never supports SAP Web GUI or browser-based Fiori pages.
