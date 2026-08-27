---
title: SAP Control Object Commitment Evidence
summary: Read strict fiscal-year and accounting-period commitment evidence for one resolved WBS or internal order.
tags: [sap, co, ps, commitment, read-only]
systems: [SAP S/4HANA]
---

## Overview

This strictly read-only Skill accepts one authoritative resolved WBS or internal-order object and a fiscal-year/accounting-period range. It aggregates signed finite Decimal evidence only when the full object, type, period, currency, stable-key, and paging contract is proven.

## Use Cases

Use it when a deterministic CO/PS workflow needs remaining purchase-requisition, purchase-order, and related commitment types 21, 22, 24, or 26. It never estimates commitments or substitutes a current snapshot for period evidence.

## Prerequisites

- A source for the requested object type is enabled and validated in `references/source-profiles.json`.
- The target source exposes fiscal year, accounting period, remaining amount, currency, currency role, purchasing references, and stable paging.
- Any SOAP source has a fixed approved read-only action and endpoint.
- Python 3.10+ and `requests` from `scripts/requirements.txt` are installed.

## Usage

From this Skill directory:

```powershell
python run.py --input input.json --output .artifacts\commitment-evidence\output.json
```

## Inputs

The input contains one strict `resolved_object`, fiscal year, `period_from`, `period_to`, and an explicit list of commitment types. Periods are accounting periods 1 through 16. Caller-selected connections, sources, SQL, fields, URLs, and unknown properties are rejected.

## Outputs

The output includes relationship and analysis scope, source-profile identity, commitment details, nullable totals grouped by type/currency/role, source/paging/scope/evidence completeness, safe issue codes, timestamps, and artifact hashes.

## Limitations

The current target profile is intentionally unvalidated: no callable Project Commitment SOAP binding has been proven. Internal-order COSP/COSS key records are readable, but period amount projection fails intermittently with `Unknown column VERS` and has not been reconciled to an authoritative baseline. Runtime requests therefore return `partial` with empty details and null totals. Incomplete rows are never dropped and missing values are never treated as zero. No currency conversion is performed.

## Examples

```json
{
  "schema_version": 1,
  "resolved_object": {
    "object_type": "WBS",
    "external_id": "P-100.01",
    "internal_id": "557",
    "object_number": "PR00000557",
    "company_code": "KT70",
    "controlling_area": "KT00"
  },
  "fiscal_year": "2026",
  "period_from": 1,
  "period_to": 16,
  "commitment_types": ["21", "22", "24", "26"]
}
```
