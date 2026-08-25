---
title: SAP Production Order Cost Analysis
summary: Strictly read-only production-order plan, target, and actual cost evidence by cost element.
tags: [sap, co, production-order, target-cost, read-only]
systems: [SAP S/4HANA]
---

## Overview

This Skill reads auditable production-order cost evidence for one bounded order and fiscal-period scope. It first proves the AUFK cost-object relationship, validates the released parameterized production-order cost CDS at runtime, and returns plan, target, and actual values by cost element.

## Use Cases

Use it when a deterministic Agent must compare production-order plan, target, and actual costs. It is not a material-price comparison tool and never runs costing, variance calculation, settlement, or revaluation.

## Prerequisites

- The internally owned default ADT profile is configured and protected.
- AUFK and the released production-order cost CDS are readable on the target.
- ADT Data Preview is available with TLS validation enabled.
- Python 3.10+ and `requests` from `scripts/requirements.txt` are installed.

## Usage

From this Skill directory:

```powershell
python run.py --input input.json --output .artifacts\production-order-cost\output.json
```

## Inputs

The input schema is `references/input.schema.json`. The caller supplies only a manufacturing order, one fixed target-cost variant, and either an optional fiscal year/period or an internally resolved fiscal-period range. Connection, source-object, raw SQL, and arbitrary CDS parameter selection are rejected.

## Outputs

The output schema is `references/output.schema.json`. It includes order context, analysis scope, AUFK relationship evidence, cost-element details, totals, completeness, validation issues, timestamps, and hashes. Exact decimal values are serialized as strings.

## Limitations

`partial` means the evidence contract is incomplete. Missing plan or target cost is never interpreted as zero. Standard material price is never substituted for production-order target cost. Different ledgers, currencies, currency roles, and periods are never silently combined.

## Examples

```json
{
  "schema_version": 1,
  "manufacturing_order": "1001233",
  "fiscal_year": "2020",
  "period": 11,
  "target_cost_variant": 1
}
```
