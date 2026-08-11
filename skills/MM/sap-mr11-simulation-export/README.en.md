---
title: SAP MR11 Simulation Export
summary: Run MR11 only in simulation mode and export adjustment candidates with auditable evidence.
tags: [MR11, GR IR, simulation, SAP GUI automation]
transactions: [MR11]
systems: [SAP ERP, SAP S/4HANA, SAP GUI for Windows]
---

## Overview

This Skill runs MR11 only after proving the simulation control is selected and posting/update controls are cleared. It exports candidate rows, exclusion reasons, messages, currency totals, logs, and hashes.

## Use Cases

- Obtain exact SAP-standard MR11 proposal logic without posting.
- Review ageing or tolerance-based GR/IR adjustment candidates.
- Preserve a reproducible audit package.

## Prerequisites

Use Windows, an authenticated SAP GUI session, scripting enabled, Python 3.12, `pywin32`, and `openpyxl`. Validate a copied technical-control profile against the target system.

## Usage

```powershell
python scripts\mr11_simulation_export.py --company-code 1000 --key-date 2026-08-01 --variant Z_MR11_AUDIT --output-dir C:\Exports --profile .\validated-profile.json
```

## Inputs

Company code, key date, optional PO range, age days, tolerance policy or SAP variant, validation/full run mode, system/client, profile, output name, and overwrite permission.

## Outputs

Technical-header XLSX, CSV, log, and manifest containing SAP identity, accepted selections, row count, totals by currency, timestamps, and SHA-256 hashes.

## Limitations

The bundled profile is deliberately unvalidated. Control IDs and ALV fields vary by release and customer enhancement. The Skill has no posting mode and accepts zero results only from a numeric SAP result counter.

## Examples

Start with a 100-row validation run and a narrow PO range:

```powershell
python scripts\mr11_simulation_export.py --company-code 1000 --key-date 2026-08-01 --purchase-order-low 4500001000 --purchase-order-high 4500001099 --tolerance-policy Z01 --run-mode validate --output-dir C:\Exports --profile .\validated-profile.json
```
