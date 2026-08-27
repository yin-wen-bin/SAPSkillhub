---
name: sap-control-object-commitment-evidence
description: Read remaining commitment evidence for one already-resolved SAP WBS or internal order within one fiscal year and strict accounting periods 1 through 16. Use when authoritative, period-bearing commitment evidence is required. The Skill is fail-closed while the target source profile is unvalidated; do not use it to estimate commitments, convert currency, rediscover sources, or repair object relationships.
---

# SAP Control Object Commitment Evidence

Accept only a `resolved_object` whose object type, internal ID, object-number prefix, company code, and controlling area are already proven. Do not re-resolve or guess the relationship.

Run `python run.py --input input.json --output output.json`. Use only enabled sources and explicit value-type mappings in `references/source-profiles.json`. Periods are accounting periods, never posting-date approximations or current snapshots.

Emit details and totals only when object scope, requested types, fiscal year, every requested period, stable keys, pagination, amounts, currencies, and currency roles are complete. Otherwise set `evidence_complete=false`, `commitment_details=[]`, and `commitment_totals=null`. A complete empty source may produce explicit zero evidence only when its authoritative scope and zero currency context are proven.

SOAP POST is permitted only for a profile-enabled relative endpoint and exact read-only action. Disable redirects, cap time and response bytes, and reject XML external entities. Read `references/evidence-contract.md` before interpreting zero or partial evidence.
