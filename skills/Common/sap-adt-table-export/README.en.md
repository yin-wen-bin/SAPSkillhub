---
title: SAP ADT Table Export
summary: Strictly read-only, bounded table and CDS evidence through SAP ADT Data Preview.
tags: [sap, adt, read-only, evidence, export]
systems: [SAP S/4HANA, SAP NetWeaver AS ABAP]
---

## Overview

This skill fills narrow evidence gaps with SAP ADT Data Preview. It accepts structured query intent, resolves only its internally configured default profile, generates SELECT internally, and emits canonical JSON plus a SHA-256 manifest.

## Use Cases

Use it after a released API or OData service cannot supply a required field, and before GUI SE16N. Suitable requests are bounded reads of table or CDS fields confirmed by live ADT/DDIC metadata. It is not a general SQL, development, or transport tool.

## Prerequisites

- An SAP user authorized only for the intended ADT Data Preview reads.
- Active `/sap/bc/adt/datapreview/freestyle` over HTTPS.
- Valid certificate trust; TLS verification cannot be disabled.
- An ignored `.env` copied from `.env.example` and a protected profiles file based on `references/profiles.example.json`. The profiles file declares `default_profile`; callers cannot select it. Dynamic mode confirms objects, fields, literal types, and true stable keys from live DDIC metadata.
- Python 3.10+ and the tested `requests==2.34.2` baseline from `scripts/requirements.txt` (minimum accepted: 2.31.0).

## Usage

From this skill directory:

```powershell
python scripts/check_environment.py
Copy-Item .env.example .env
# Edit the ignored .env and the protected profile outside the repository.
python run.py --input input.json --output .artifacts\adt-table-export\output.json
```

Follow `references/live-validation.md` for the first target-system run. Keep all task and result files in ignored runtime storage.

## Inputs

The input schema is `references/input.schema.json`. Task input contains only `table` or `cds`, object and fields, typed filters, the exact ascending live-DDIC key order, and a bounded `max_rows`. Any live field may be selected or filtered, but at least one inclusive EQ, BT, or IN filter is mandatory; `max_rows` is capped at 30,000. Profile names, raw SQL, URLs, credentials, SAP client values, endpoints, and TLS switches are rejected.

## Outputs

The output follows `references/output.schema.json`: run identifier, sanitized source identity, exact bounded scope, rows, row count, completeness, truncation, closed-set validation issues, timestamps, and hashes. Internal profile names, SAP URLs, client, credentials and connection paths are omitted. `complete` applies only to that exact bounded selection. `partial` always has `source_complete=false`; `failed` contains no rows.

## Limitations

Only GET and read-only POST fallback to the exact Data Preview endpoint are implemented. Paging requires a live-DDIC-declared stable key and ascending keyset order. The runtime cannot prove completeness beyond `max_rows`, infer keys, bypass authorization, accept redirects, or weaken TLS. Reaching 30,000 rows or a smaller task limit returns `partial/row_limit_reached`. CDS access control may legitimately filter returned rows.

## Examples

```json
{
  "schema_version": 1,
  "source_type": "table",
  "object": "TSTC",
  "fields": ["TCODE", "PGMNA"],
  "filters": [{"field": "TCODE", "operator": "eq", "value": "SE16N"}],
  "order_by": [{"field": "TCODE", "direction": "asc"}],
  "max_rows": 2
}
```

A result with one row, no issues, and `source_complete=true` proves only that the exact `TCODE = SE16N` selection completed.
