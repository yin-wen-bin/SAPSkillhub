---
name: sap-adt-table-export
description: Export small, bounded table or CDS evidence through SAP ABAP Development Tools Data Preview using a trusted connection profile and an internally generated SELECT. Use only after a released API/OData route is unavailable and before falling back to SAP GUI SE16N; never use for arbitrary SQL, writes, activation, transports, or unbounded extraction.
---

# SAP ADT Table Export

Use this skill only in the evidence fallback chain: released API/OData, then this ADT skill, then `sap-se16n-export`, then an explicit `DATA_GAP`. Read `references/live-validation.md` before any target-system run.

Run `python run.py --input input.json --output output.json`. Put only `connection_profile`, object, fields, typed filters, stable ordering, and `max_rows` in task input. Keep URLs, SAP client, credentials, CA paths, allowlists, field types, and stable keys in the protected trusted profiles file named by `SAP_ADT_PROFILES_FILE` or `--profiles`.

The runtime exposes only the allowlisted DDIC/CDS source metadata paths and `/sap/bc/adt/datapreview/freestyle`, generates one SELECT internally, enforces HTTPS certificate validation, validates live source and returned column metadata, and uses ascending trusted-key pagination. It rejects raw SQL, task-supplied endpoints or credentials, unknown objects or fields, sensitive fields, unbounded filters, non-stable ordering, redirects, and any response that cannot prove paging integrity.

Treat `complete` as complete only for the exact bounded selection. `partial` with `row_limit_reached` is useful evidence but has `source_complete=false`. A timeout, unavailable metadata, duplicate/non-monotonic key, authorization error, authentication error, or TLS failure is `failed`; do not retry by weakening TLS or widening the selection.

Never print raw rows, credentials, base URLs, or generated SQL to logs. Store runtime inputs and outputs only in ignored evidence directories such as `.artifacts/adt-table-export/`. Preserve the result JSON and its adjacent SHA-256 manifest.

interface:
  display_name: "SAP ADT Table Export"
  short_description: "Read-only bounded ADT evidence export"
  default_prompt: "Use $sap-adt-table-export to run a strictly read-only bounded ADT table or CDS evidence query."
policy:
  allow_implicit_invocation: true
