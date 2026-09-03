---
title: SAP Bank Receipt Evidence
summary: Read bounded, auditable credit receipts, reversals, and processing evidence from one fixed bank-statement source.
tags: [sap, fi, bank-statement, bank-receipt, read-only]
systems: [SAP S/4HANA]
---

## Overview

This Skill reads SAP bank-statement credit items by company code and value-date range. It returns stable keys, dates, signed Decimal amounts, currencies, reversal state, processing state, and privacy-safe payer account evidence.

It does not use Payment Advice, match customers or invoices, or interpret a bank line as proof that a receivable is settled.

## Use Cases

Use it to obtain bank-statement credit evidence for one company code and bounded value-date range, especially when active, reversal, and processing states must remain separately auditable.

## Prerequisites

- The fixed source profile has passed target-system validation and is enabled.
- The SAPSkillhub-owned ADT connection enforces TLS validation.
- The Skill-owned ignored `.env` contains the account HMAC key and matching key ID.

## Usage

Input and output must stay in a repository-ignored artifact directory:

```powershell
python run.py --input ..\..\..\.artifacts\bank-receipt\input.json --output ..\..\..\.artifacts\bank-receipt\output.json
```

## Inputs

The strict schema accepts only the version, company code, date bounds, and an optional bank reference. Dates are inclusive value dates and may span at most 31 days. Connections, URLs, objects, fields, SQL, credentials, TLS, and paging controls are rejected.

## Outputs

The output contains receipt details, per-currency active and reversal-affected summaries, the fixed source profile, three completeness signals, safe issue codes, timestamps, and artifact hashes. Accounts are represented only by a last-four mask and HMAC.

## Completeness

Details and currency summaries are returned only when metadata, stable-key paging, counts, amounts, currencies, and status mappings are complete. An authoritative empty result is `complete/not_found`. Any source or row-level problem is `partial/source_unavailable` without partial details.

## Privacy

Raw payer accounts never leave the process. Only a last-four mask and keyed HMAC-SHA-256 are emitted. Payer names and bank references may appear only in the ignored output JSON, never in logs, errors, or Git.

## Limitations

A related accounting document is only a bank-statement processing relationship. It does not prove customer identity, invoice allocation, receivable clearing, or business settlement. Partial sources or invalid required evidence never produce partial details.

## Examples

```json
{
  "schema_version": 1,
  "company_code": "1710",
  "date_from": "2023-11-01",
  "date_to": "2023-11-30"
}
```
