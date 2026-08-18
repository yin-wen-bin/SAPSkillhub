---
name: sap-adt-table-export
description: Export small, bounded table or CDS evidence through SAP ABAP Development Tools Data Preview using an internally owned default connection and generated SELECT. Use only after a released API/OData route is unavailable and before falling back to SAP GUI SE16N; never use for arbitrary SQL, writes, activation, transports, connection selection, or unbounded extraction.
---

# SAP ADT Table Export

Use this skill only in the evidence fallback chain: released API/OData, then this ADT skill, then `sap-se16n-export`, then an explicit `DATA_GAP`. Read `references/live-validation.md` before any target-system run.

Run `python run.py --input input.json --output output.json`. Put only object, fields, typed filters, stable ordering, and `max_rows` in task input. The runtime loads this Skill directory's ignored `.env`, resolves its protected profiles file, and uses only the internal `default_profile`; callers cannot select or override a connection through JSON, CLI arguments, or process environment variables. With `dynamic_objects=true`, the runtime accepts any syntactically valid table or CDS name and validates its fields, resolves literal types through live data-element metadata, and obtains the ordered stable key from live ADT/DDIC metadata; no object, selected-field, or filter-field allowlist is required.

The runtime exposes no profile name, SAP URL, client, credentials, connection endpoint, or metadata path in output and validation issues. It generates one SELECT internally, enforces HTTPS certificate validation, validates live source and returned column metadata, and uses ascending live-key pagination. It rejects raw SQL, task-supplied connection selection, endpoints or credentials, fields absent from live metadata, unbounded filters, non-stable ordering, redirects, requests above 30,000 rows, and any response that cannot prove paging integrity.

Treat `complete` as complete only for the exact bounded selection. `partial` with `row_limit_reached` is useful evidence but has `source_complete=false`. A timeout, unavailable metadata, duplicate/non-monotonic key, authorization error, authentication error, or TLS failure is `failed`; do not retry by weakening TLS or widening the selection.

Never print raw rows, credentials, base URLs, or generated SQL to logs. Store runtime inputs and outputs only in ignored evidence directories such as `.artifacts/adt-table-export/`. Preserve the result JSON and its adjacent SHA-256 manifest.

interface:
  display_name: "SAP ADT Table Export"
  short_description: "Read-only bounded ADT evidence export"
  default_prompt: "Use $sap-adt-table-export to run a strictly read-only bounded ADT table or CDS evidence query."
policy:
  allow_implicit_invocation: true
