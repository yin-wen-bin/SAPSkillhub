---
title: SAP SE16N Table Export
summary: Run SE16N through SAP GUI Scripting, set the maximum hit count, and export the ALV result to Excel.
tags:
  - SE16N
  - table data
  - Excel
  - SAP GUI automation
transactions:
  - SE16N
systems:
  - SAP ERP
  - SAP S/4HANA
  - SAP GUI for Windows
---

## Overview

This skill automates transaction SE16N in SAP GUI for Windows. It uses `scripts/se16n_export.vbs` to open a table, set `Max. no. of hits`, execute the query, and save the ALV result as an Excel workbook through the XXL export flow. When a standard SAP GUI Scripting security prompt appears at startup, `scripts/sap_security_prompt_helper.ps1` clicks the standard `OK` control automatically.

The script defaults mirror the source script at `<LOCAL_SKILL_PATH>\sap-se16n-export\se16n_export.vbs`: export `MARA` to `<LOCAL_SKILL_PATH>\sap-se16n-export\mara.xlsx` with max hits set to `2147483647`.

## Use Cases

- Export an SE16N table result to an XLSX workbook.
- Validate SAP GUI Scripting, ALV export, and save-path behavior with a low hit count.
- Repeat the export after changing the table, max-hit value, output directory, or filename.
- Diagnose SE16N export compatibility after SAP GUI language, theme, version, or Windows display-scale changes.
- Design helper handling for Windows dialogs that are outside the VBScript control range.

## Prerequisites

- Windows with SAP GUI for Windows installed.
- SAP GUI Scripting enabled on both the client and server.
- An authenticated SAP session with authorization to run SE16N, read the target table, and export ALV results.
- Write access to the output directory, with the target workbook closed in Excel or other spreadsheet tools.
- Review `references/environment.md` before the first live run on a machine or after SAP GUI, Windows, theme, language, or display-scale changes.

## Usage

Start with a low-hit validation export:

```powershell
cscript //nologo scripts\se16n_export.vbs `
  /table:MARA `
  /maxhits:100 `
  /outdir:"<LOCAL_WORKSPACE>\se16n-test" `
  /file:"mara.xlsx" `
  /securitytimeout:60
```

After confirming the workbook, increase `/maxhits` or switch to the target business table:

```powershell
cscript //nologo scripts\se16n_export.vbs `
  /table:MARC `
  /maxhits:50000 `
  /outdir:"<LOCAL_WORKSPACE>\se16n" `
  /file:"marc.xlsx"
```

When no arguments are supplied, the script uses the source VBS defaults: `MARA`, `2147483647`, `<LOCAL_SKILL_PATH>\sap-se16n-export`, and `mara.xlsx`.

## Inputs

| Input | Required | Description |
| --- | --- | --- |
| `/table` | No | SE16N table name. Defaults to `MARA`; the script uppercases it. |
| `/maxhits` | No | Value written to `GD-MAX_LINES`. Defaults to `2147483647`. |
| `/outdir` | No | Output directory. Defaults to `<LOCAL_SKILL_PATH>\sap-se16n-export`; the script creates it when missing. |
| `/file` | No | Output XLSX filename. Defaults from the table name; `.xlsx` is appended when no extension is supplied. |
| `/securityhelper` | No | Enables the SAP GUI Scripting security prompt helper. Defaults to `true`; set to `false` for manual confirmation. |
| `/securitytimeout` | No | Background polling window for the helper, in seconds. Defaults to `60`. |

## Outputs

| Output | Naming contract | Description |
| --- | --- | --- |
| Excel workbook | `<outdir>\<file>` | SE16N ALV result saved through XXL export. |
| Console output | Standard output | Prints the target path after the export is submitted. |
| Local diagnostics | Manual or helper-defined directory | Used only when investigating windows outside the script control range; do not commit these files. |

## Limitations

- The skill supports SAP GUI for Windows only; it does not automate SAP GUI for HTML or Fiori pages.
- The VBScript relies on SAP GUI Scripting technical control IDs and does not use fixed coordinates, OCR, or translated button text.
- The current script does not fill SE16N selection criteria. Add field-specific control logic only after inspecting the target system controls.
- `2147483647` is the technical maximum, but large exports may still fail because of runtime, memory, authorization, ALV, SAP frontend, or Excel limits.
- Only known SAP GUI Scripting security prompts are auto-confirmed, and only after both the prompt text and standard OK control ID match.
- If overwrite confirmations, file locks, Excel dialogs, or unknown security prompts appear, do not guess button meanings. Follow `references/environment.md` and the language-independent window-handling model from `sap-mb5b-export`.
- Use a fresh output filename unless the user explicitly approves replacement.

## Examples

Export the first 100 `MARA` rows to a test directory:

```powershell
cscript //nologo scripts\se16n_export.vbs /table:MARA /maxhits:100 /outdir:"<LOCAL_WORKSPACE>\se16n-test" /file:"mara.xlsx"
```

After confirming that the test workbook opens and contains the expected data, run the production export with the target table and hit count.
