---
title: SAP ADT Table Export
summary: Strictly read-only, bounded table and CDS evidence through SAP ADT Data Preview.
tags: [sap, adt, read-only, evidence, export]
systems: [SAP S/4HANA, SAP NetWeaver AS ABAP]
---

## Overview

This skill fills narrow evidence gaps with SAP ADT Data Preview. It accepts structured query intent, resolves only a protected trusted profile, generates SELECT internally, and emits canonical JSON plus a SHA-256 manifest.

## Use Cases

Use it after a released API or OData service cannot supply a required field, and before GUI SE16N. Suitable requests are small, bounded reads of explicitly reviewed table or CDS fields. It is not a general SQL, extraction, development, or transport tool.

## Prerequisites

- An SAP user authorized only for the intended ADT Data Preview reads.
- Active `/sap/bc/adt/datapreview/freestyle` over HTTPS.
- Valid certificate trust; TLS verification cannot be disabled.
- A protected profiles file based on `references/profiles.example.json` with reviewed objects, fields, types, bounded filters, and true stable keys.
- Python 3.10+ and the tested `requests==2.34.2` baseline from `scripts/requirements.txt` (minimum accepted: 2.31.0).

## Usage

From this skill directory:

```powershell
python scripts/check_environment.py
$env:SAP_ADT_PROFILES_FILE = "C:\protected\adt-profiles.json"
python run.py --input input.json --output .artifacts\adt-table-export\output.json
```

Follow `references/live-validation.md` for the first target-system run. Keep all task and result files in ignored runtime storage.

## Inputs

The input schema is `references/input.schema.json`. Task input contains only a trusted profile name, `table` or `cds`, an allowlisted object, allowlisted fields, typed filters, the exact ascending trusted key order, and a bounded `max_rows`. At least one reviewed EQ, BT, or IN bounded filter is mandatory. Raw SQL, URLs, credentials, SAP client values, endpoints, and TLS switches are rejected.

## Outputs

The output follows `references/output.schema.json`: run and source identifiers, exact bounded scope, rows, row count, completeness, truncation, closed-set validation issues, timestamps, and hashes. `complete` applies only to that exact bounded selection. `partial` always has `source_complete=false`; `failed` contains no rows.

## Limitations

Only GET and read-only POST fallback to the exact Data Preview endpoint are implemented. Paging requires a reviewed stable key and ascending keyset order. The runtime cannot prove completeness beyond `max_rows`, infer keys, discover or broaden allowlists, bypass authorization, accept redirects, or weaken TLS. CDS access control may legitimately filter returned rows.

## Examples

```json
{
  "schema_version": 1,
  "connection_profile": "quality-readonly",
  "source_type": "table",
  "object": "TSTC",
  "fields": ["TCODE", "PGMNA"],
  "filters": [{"field": "TCODE", "operator": "eq", "value": "SE16N"}],
  "order_by": [{"field": "TCODE", "direction": "asc"}],
  "max_rows": 2
}
```

A result with one row, no issues, and `source_complete=true` proves only that the exact `TCODE = SE16N` selection completed.
