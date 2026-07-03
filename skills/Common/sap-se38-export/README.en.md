---
title: SAP SE38 Program Source Export
summary: Run SE38 through SAP GUI Scripting and download an ABAP source file by program name and output path.
tags:
  - SE38
  - ABAP
  - source export
  - SAP GUI automation
transactions:
  - SE38
systems:
  - SAP ERP
  - SAP S/4HANA
  - SAP GUI for Windows
---

## Overview

This skill automates transaction SE38 in SAP GUI for Windows. It uses `scripts/se38_export.vbs` to open a specified ABAP program and save the source to a local file through the recorded SE38 menu path.

The script is based on `<LOCAL_SKILL_PATH>\sap-se38-export\se38_export.vbs`, where the program was hard-coded as `SAPLSE16N` and the output directory as `<LOCAL_SKILL_PATH>\sap-se38-export`. The repository version requires two runtime parameters instead: the program name and the output path.

## Use Cases

- Download a specified ABAP program source file from SE38.
- Reuse the recorded script without hard-coded program names or output directories.
- Validate SAP GUI Scripting, security prompts, and save-path behavior with a known program.
- Diagnose SE38 download compatibility after SAP GUI language, theme, version, or Windows display-scale changes.
- Design helper handling for Windows dialogs that are outside the VBScript control range.

## Prerequisites

- Windows with SAP GUI for Windows installed.
- SAP GUI Scripting enabled on both the client and server.
- An authenticated SAP session with authorization to run SE38, display the target program, and download source.
- Write access to the output directory, with the target file closed in editors or other tools.
- Review `references/environment.md` before the first live run on a machine or after SAP GUI, Windows, theme, language, or display-scale changes.

## Usage

Run the download with a program name and a full output file path:

```powershell
cscript //nologo scripts\se38_export.vbs `
  /program:SAPLSE16N `
  /out:"<LOCAL_WORKSPACE>\abap\SAPLSE16N.abap"
```

If `/out` points to an existing directory, or ends with a backslash, the script uses the program name as the filename:

```powershell
cscript //nologo scripts\se38_export.vbs /program:ZDEMO_REPORT /out:"<LOCAL_WORKSPACE>\abap\"
```

## Inputs

| Input | Required | Description |
| --- | --- | --- |
| `/program` | Yes | ABAP program name to download. The script writes it into `RS38M-PROGRAMM` and uppercases it. |
| `/out` | Yes | Output path. Prefer a full file path; when a directory is supplied, the filename comes from the program name. |
| `/securityhelper` | No | Enables the SAP GUI Scripting security prompt helper. Defaults to `true`; set to `false` for manual confirmation. |
| `/securitytimeout` | No | Background polling window for the helper, in seconds. Defaults to `60`. |

## Outputs

| Output | Naming contract | Description |
| --- | --- | --- |
| Source file | Resolved local path from `/out` | ABAP source text saved through the SE38 menu download flow. |
| Console output | Standard output | Prints the target path after the download is submitted. |
| Local diagnostics | Manual or helper-defined directory | Used only when investigating windows outside the script control range; do not commit these files. |

## Limitations

- The skill supports SAP GUI for Windows only; it does not automate SAP GUI for HTML or Fiori pages.
- The VBScript relies on SAP GUI Scripting technical control IDs and does not use fixed coordinates, OCR, or translated button text.
- The current script uses the recorded SE38 menu path. If a target system has a different menu structure, inspect the technical control IDs before changing it.
- Only known SAP GUI Scripting security prompts are auto-confirmed, and only after both the prompt text and standard OK control ID match.
- If overwrite confirmations, file locks, authorization messages, or unknown security prompts appear, do not guess button meanings. Follow `references/environment.md` and the language-independent window-handling model from `sap-mb5b-export`.
- Use a fresh output filename unless the user explicitly approves replacement.

## Examples

Download `SAPLSE16N` source to a test directory:

```powershell
cscript //nologo scripts\se38_export.vbs /program:SAPLSE16N /out:"<LOCAL_WORKSPACE>\se38-test\SAPLSE16N.abap"
```

After confirming that the file opens and contains the expected source, rerun with the target program and production output path.
