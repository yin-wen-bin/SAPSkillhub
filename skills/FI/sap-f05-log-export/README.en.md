---
title: SAP F.05 Log and Test-Run Export
summary: Export an existing F.05 run log or non-posting test-run evidence through SAP GUI.
tags: [F.05, foreign currency valuation, test run, SAP GUI automation]
transactions: [F.05]
systems: [SAP ERP, SAP S/4HANA, SAP GUI for Windows]
---

## Overview

The Skill defaults to existing-log display and also supports a strictly non-posting F.05 test run. It captures run metadata, warnings/errors, valuation totals, referenced documents, and file hashes.

## Use Cases

- Export evidence from an existing foreign-currency valuation run.
- Perform a controlled F.05 test run without update or posting.
- Preserve a language-independent ALV/list or spool artifact.

## Prerequisites

Use Windows, an authenticated SAP GUI session, scripting enabled, Python 3.12, `pywin32`, and `openpyxl`. Validate a copied technical-control profile against the target system.

## Usage

```powershell
python scripts\f05_log_export.py --mode existing-log --run-id 20260801-001 --output-dir C:\Exports --profile .\validated-profile.json
```

## Inputs

Mode, run ID for an existing log, or company code and valuation key date for a test run; optional valuation area/method, variant, system/client, output name, profile, and overwrite permission.

## Outputs

Technical-header XLSX, CSV, log, and manifest with SAP identity, exact selections, job/run status fields, warnings/errors, currency totals, timestamps, document references, and SHA-256 hashes.

## Limitations

The bundled profile is unvalidated. F.05 and spool controls vary across releases and customer variants. The Skill never enables update/posting and does not create accounting documents.

## Examples

Run a non-posting test only after profile validation:

```powershell
python scripts\f05_log_export.py --mode test-run --company-code 1000 --valuation-key-date 2026-08-01 --valuation-method Z001 --output-dir C:\Exports --profile .\validated-profile.json
```
