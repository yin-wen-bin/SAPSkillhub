---
title: SAP WBS Object Resolver
summary: Resolve one external WBS ID to authoritative SAP control-object keys through fixed read-only sources.
tags: [sap, co, ps, wbs, read-only]
systems: [SAP S/4HANA]
---

## Overview

This Skill resolves one trimmed external WBS ID plus company code to an authoritative internal WBS ID, object number, controlling area, and project relationship. Runtime source selection is fixed by a versioned profile.

## Use Cases

Use it before CO/PS amount retrieval when the caller has a user-visible WBS external ID but downstream evidence requires SAP internal keys. It is not a fuzzy search, coding-mask converter, or source-discovery tool.

## Prerequisites

- The SAPSkillhub-owned read-only connection is configured with TLS validation enabled.
- Project V2 and Financial WBS are readable on the target.
- Their live metadata SHA-256 values match `references/source-profiles.json`.
- Python 3.10+ and `requests` from `scripts/requirements.txt` are installed.

## Usage

From this Skill directory:

```powershell
python run.py --input input.json --output .artifacts\wbs-resolver\output.json
```

## Inputs

The strict input schema accepts only `schema_version`, `wbs_external_id`, and `company_code`. The WBS value is trimmed but its case and separators are preserved. Connections, URLs, SQL, sources, fields, and unknown properties are rejected.

## Outputs

The output includes the requested scope, nullable `resolved_object`, cross-source relationship checks, safe source-profile identity, source/paging/evidence completeness, issue codes, timestamps, and SHA-256 artifacts. A resolved object is returned only for `complete/resolved`.

## Limitations

The validated profile uses exact Project V2 lookup followed by Financial WBS enrichment. Missing, ambiguous, incomplete, metadata-incompatible, or inconsistent evidence returns `partial` without a resolved object. Resolution does not prove commitment, budget, plan, actual cost, or process completion.

## Examples

```json
{
  "schema_version": 1,
  "wbs_external_id": "S/5818-ETO1",
  "company_code": "KT70"
}
```
