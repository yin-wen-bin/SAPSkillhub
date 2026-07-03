---
name: sap-se38-export
description: Automate SAP GUI for Windows transaction SE38 to download an ABAP program source file using the bundled VBScript. Use when Codex needs to run, adapt, or diagnose SE38 program source exports, parameterize the program name and output path, validate SAP GUI Scripting behavior, or handle SE38 download issues that may involve SAP or Windows save dialogs.
---

# SAP SE38 Export

Use the bundled VBScript as the starting point for SE38 program source downloads. Keep SAP GUI operations inside SAP GUI Scripting technical IDs, and handle any out-of-scope Windows dialogs with the language-independent principles in `references/environment.md`.

## Required Workflow

1. Read [references/environment.md](references/environment.md) before the first run on a machine or after an SAP GUI, Windows, theme, language, or display-scale change.
2. Confirm SAP GUI for Windows is open, SAP GUI Scripting is enabled, and the user is already authenticated in the intended SAP session.
3. Run a validation download for a small, known program before downloading larger or business-critical objects.
4. Confirm the file is created at the expected path and contains the expected ABAP source.
5. Run the target export only after the validation export succeeds.

## Command

```powershell
cscript //nologo scripts\se38_export.vbs `
  /program:SAPLSE16N `
  /out:"<LOCAL_WORKSPACE>\abap\SAPLSE16N.abap"
```

The source recording came from `<LOCAL_SKILL_PATH>\sap-se38-export\se38_export.vbs`, where the program was hard-coded as `SAPLSE16N` and the output directory as `<LOCAL_SKILL_PATH>\sap-se38-export`. The bundled script requires these values as parameters instead.

## Parameters

- `/program` is the ABAP program name written into `RS38M-PROGRAMM`. The script uppercases it.
- `/out` is the target output path. Pass a full file path for exact naming. If `/out` is an existing directory or ends with `\`, the script writes a file named after the program.
- `/securityhelper` controls the startup SAP GUI Scripting security helper. It defaults to `true`; pass `/securityhelper:false` only when the user wants to handle the prompt manually.
- `/securitytimeout` is the helper's background polling window in seconds. It defaults to `60`.

## Language Independence

- Use SAP technical control IDs from the VBScript for SE38 navigation, program input, display/open action, source download menu selection, and SAP internal save fields.
- Do not add fixed coordinates, OCR, translated button labels, or window-title matching to execution logic.
- Treat displayed titles and labels as diagnostics only.
- The bundled `scripts/sap_security_prompt_helper.ps1` may auto-confirm only known SAP GUI Scripting security prompts after matching the prompt text and standard OK control ID.
- If an external Windows save, overwrite, Excel, file-lock, or unknown security dialog appears outside the VBScript control range, follow `references/environment.md` and the `sap-mb5b-export` model: inspect controls passively, identify controls by structure and stable IDs, and stop on ambiguous multi-button dialogs.
- Do not answer overwrite prompts unless the user explicitly permits replacement.

## Output Contract

The output is the local text file resolved from `/out`. Runtime diagnostics, screenshots, temporary downloads, and generated source files are local artifacts and should not be committed unless the user explicitly asks for sample fixtures.

Do not bulk-delete files or directories. Keep logs and captured UI diagnostics local and out of source control.
