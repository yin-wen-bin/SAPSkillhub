---
title: SAP SE16N Safe Table Export
summary: Filter, validate, chunk, merge, and evidence SAP SE16N exports through SAP GUI for Windows.
tags: [SE16N, table data, chunking, Excel, SAP GUI automation]
transactions: [SE16N]
systems: [SAP ERP, SAP S/4HANA, SAP GUI for Windows]
---

## Overview

The Python entry accepts JSON selections or repeatable CLI filters, defaults to a 100-row validation run, and uses 50,001 rows as the full-mode overflow probe. Successful leaf chunks are merged into canonical XLSX and CSV outputs with a manifest and SHA-256 evidence. The VBS file remains a compatibility wrapper.

## Use Cases

- Validate a table and filter set with low impact.
- Export a bounded large table through audited recursive chunks.
- Produce reproducible selection, row-count, merge, and hash evidence.

## Prerequisites

Use Windows, an authenticated SAP GUI session, SAP GUI Scripting, Python 3.12, `openpyxl==3.1.5`, and `pywin32`. Review `references/environment.md` and adapt `references/control-profile.json` after passive control inspection when the system screen differs.

## Usage

```powershell
python scripts\se16n_export.py --table BSIK --selection-file .\bsik.json --mode full --output-dir C:\Exports --file bsik
```

Validation is the default:

```powershell
python scripts\se16n_export.py --table MARA --where "MATNR=10000001,10000002" --exclude "MTART=DIEN" --output-dir C:\Exports
```

## Inputs

JSON schema version 1 supports `filters`, `columns`, `sort`, optional `chunk`, and `key_fields`. Filters support `EQ/NE/BT/NB/GE/GT/LE/LT/CP/NP`. Same-field includes are OR alternatives, excludes subtract matches, and different fields combine with AND. CLI shortcuts accept `FIELD=value`, `FIELD=low..high`, and comma-separated values.

Full mode requires bounded policies. BSEG, BSIK, and BSIS require company code and fiscal year; EKBE requires posting-date bounds. Unknown tables require explicit chunk field, type, low/high, and complete key fields.

## Outputs

The run writes `<name>.part-NNNN.xlsx`, `<name>.xlsx`, `<name>.csv`, `<name>.manifest.json`, and probe workbooks used for overflow decisions. The manifest records SAP identity, requested and accepted selection data, chunk ranges and counts, layout, timestamps, status, and hashes.

For several tables, put CLI-equivalent fields in a JSON `jobs` array and run `python scripts\se16n_batch.py --batch-file batch.json`. Every job starts with `/nSE16N`. Completion waits for stable file size/mtime, readable content, and an idle SAP session; timeout never closes SAP GUI.

## Limitations

Only SAP GUI for Windows is supported. Control IDs vary by SAP release and customer screen variant. Full exports are refused without a provable chunk range and key. Failure preserves evidence but never declares completeness. Excel outputs use multiple worksheets beyond 1,048,575 data rows.

## Examples

```json
{"schema_version": 1, "filters": [{"field": "BUKRS", "sign": "I", "option": "EQ", "low": "1710"}, {"field": "GJAHR", "sign": "I", "option": "EQ", "low": "2026"}, {"field": "BELNR", "sign": "I", "option": "BT", "low": "0000000001", "high": "9999999999"}], "sort": ["BUKRS", "GJAHR", "BELNR", "BUZEI"]}
```
