---
title: SAP AR Dunning History Evidence
summary: Read bounded, executed customer dunning events as of a business date from a validated read-only source.
tags: [sap, fi, accounts-receivable, dunning, read-only]
systems: [SAP S/4HANA]
---

## Overview

This Skill reads executed AR dunning events for one company code, 1–50 customers, and an as-of date. The target system exposes `I_DunningEntryItem`, but ADT Data Preview cannot reliably project its complete item key, so the validated source profile uses a live-DDIC-checked, read-only `MHNK/MHND` fallback.

It never changes SAP, reconstructs an arbitrary historical customer-master snapshot, or interprets an empty result as proof that a customer was never dunned.

## Use Cases

Use it to support historical receivables analysis that must distinguish executed dunning evidence from current customer dunning master data.

## Prerequisites

- The fixed source profile has passed target-system validation and is enabled.
- SAPSkillhub has access to the approved ADT Data Preview and DDIC source endpoints.
- TLS verification and the repository-managed connection profile remain enabled.

## Usage

Keep input and output under a repository-ignored artifact directory:

```powershell
python run.py --input ..\..\..\.artifacts\ar-dunning\input.json --output ..\..\..\.artifacts\ar-dunning\output.json
```

## Inputs

The strict schema accepts a company code, 1–50 unique customers, an inclusive as-of date, and an optional dunning area. Connections, tables, fields, SQL, credentials, TLS, and paging controls cannot be supplied by the caller.

## Outputs

The public projection contains executed dunning events with company code, customer, dunning area, run identifiers and dates, FI document keys, dunning levels, Decimal amount text, currency, and sequence status. Restricted source fields are returned separately for platform encryption.

## Completeness

Source, paging, and evidence completeness are reported independently. A complete empty result means only that no executed dunning event was found in the requested scope through the as-of date. Ambiguous same-day event order remains explicit.

## Privacy

Public and restricted fields are split by declared schemas. Restricted rows must be encrypted by the consuming platform and must not be exposed to an Agent Runtime, public artifact, log, or SSE event.

## Limitations

The Skill does not reconstruct historical customer-master settings. `historical_dunning_master_status` therefore remains `not_assessed`. It also does not infer a business sequence from a run ID when date, time, or validated sequence evidence is insufficient.

## Examples

```json
{
  "schema_version": 1,
  "company_code": "1710",
  "customers": ["1000001", "1000002"],
  "as_of": "2023-11-30"
}
```
