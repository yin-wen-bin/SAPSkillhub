---
name: sap-wbs-object-resolver
description: Resolve one external WBS identifier and company code to a unique SAP WBS control object through fixed, versioned, read-only source profiles. Use before CO/PS evidence retrieval when the caller has a WBS external ID but not the authoritative internal ID, object number, company code, controlling area, and project relationship. Do not use for fuzzy search, mask guessing, writes, caller-selected connections, or dynamic source discovery.
---

# SAP WBS Object Resolver

Resolve exactly one WBS object. Preserve the trimmed external identifier; do not remove separators, guess a coding mask, or change case unless the active source profile explicitly proves case-insensitive semantics.

Run `python run.py --input input.json --output output.json`. The input must satisfy `references/input.schema.json` and contain no connection, URL, SQL, source, or field-selection controls.

Use only the fixed source sequence in `references/source-profiles.json`: Project API exact lookup followed by Financial WBS exact enrichment and relationship cross-check. Treat metadata SHA mismatch, incomplete paging, multiple rows, company mismatch, or inconsistent project/WBS keys as fail-closed evidence gaps. Never return `resolved_object` unless external ID, internal ID, object number, company code, controlling area, and project relationship are all uniquely proven.

Read `references/evidence-contract.md` when interpreting output status. `complete/resolved` proves one control-object relationship for this execution; it does not prove commitments, budget, plan, actual cost, or business-process completion.
