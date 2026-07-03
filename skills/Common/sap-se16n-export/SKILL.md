---
name: sap-se16n-export
description: Automate SAP GUI for Windows transaction SE16N to open a table, set Max. no. of hits, execute, and export the ALV result to an Excel workbook using the bundled VBScript. Use when Codex needs to run, adapt, or diagnose SE16N table exports, validate SAP GUI Scripting behavior, or handle SE16N export issues that may involve SAP or Windows save dialogs.
---

# SAP SE16N Export

Use the bundled VBScript as the starting point for SE16N exports. Keep SAP GUI operations inside SAP GUI Scripting technical IDs, and handle any out-of-scope Windows dialogs with the language-independent principles in `references/environment.md`.

## Required Workflow

1. Read [references/environment.md](references/environment.md) before the first run on a machine or after an SAP GUI, Windows, theme, language, or display-scale change.
2. Confirm SAP GUI for Windows is open, SAP GUI Scripting is enabled, and the user is already authenticated in the intended SAP session.
3. Run a small validation export first, either with a small table or a low `/maxhits` value.
4. Confirm the workbook is created at the expected path and contains the expected SE16N result.
5. Run the full export only after the validation export succeeds.

## Command

```powershell
cscript //nologo scripts\se16n_export.vbs `
  /table:MARA `
  /maxhits:100 `
  /outdir:"<LOCAL_WORKSPACE>\se16n" `
  /file:"mara.xlsx" `
  /securitytimeout:60
```

Defaults match the source script in `<LOCAL_SKILL_PATH>\sap-se16n-export`: `/table:MARA`, `/maxhits:2147483647`, `/outdir:"<LOCAL_SKILL_PATH>\sap-se16n-export"`, and `/file:"mara.xlsx"`.

## Parameters

- `/table` is the SE16N table name. The script uppercases it.
- `/maxhits` is written into `GD-MAX_LINES`. Use a low value for validation; `2147483647` requests the technical maximum and can be slow or disruptive on large tables.
- `/outdir` is the target directory. The script creates it when missing.
- `/file` is the XLSX filename. The script appends `.xlsx` when no extension is supplied.
- `/securityhelper` controls the startup SAP GUI Scripting security helper. It defaults to `true`; pass `/securityhelper:false` only when the user wants to handle the prompt manually.
- `/securitytimeout` is the helper's background polling window in seconds. It defaults to `60`.

## Language Independence

- Use SAP technical control IDs from the VBScript for SE16N navigation, table input, `GD-MAX_LINES`, ALV export, and SAP internal save fields.
- Do not add fixed coordinates, OCR, translated button labels, or window-title matching to execution logic.
- Treat displayed titles and labels as diagnostics only.
- The bundled `scripts/sap_security_prompt_helper.ps1` may auto-confirm only known SAP GUI Scripting security prompts after matching the prompt text and standard OK control ID.
- If an external Windows save, overwrite, Excel, file-lock, or unknown security dialog appears outside the VBScript control range, follow `references/environment.md` and the `sap-mb5b-export` model: inspect controls passively, identify controls by structure and stable IDs, and stop on ambiguous multi-button dialogs.
- Do not answer overwrite prompts unless the user explicitly permits replacement.

## Output Contract

The output workbook is `<outdir>\<file>`. Runtime diagnostics, screenshots, temporary exports, and generated workbooks are local artifacts and should not be committed unless the user explicitly asks for sample fixtures.

Do not bulk-delete files or directories. Keep logs and captured UI diagnostics local and out of source control.
