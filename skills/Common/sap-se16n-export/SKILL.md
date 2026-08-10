---
name: sap-se16n-export
description: Automate SAP GUI for Windows transaction SE16N with JSON or CLI filters, safe validation defaults, audited 50000-row recursive chunking, workbook merging, and evidence manifests. Use for controlled table exports, selection-input validation, or diagnosing technical-control and ALV export behavior.
---

# SAP SE16N Export

Use `scripts/se16n_export.py`; keep `scripts/se16n_export.vbs` only as a legacy forwarding entry. Read `references/environment.md` before a live run.

Default to `--mode validate` and 100 rows. Use `--mode full` only with bounded, verified selection criteria. For BSEG, BSIK, BSIS, and EKBE enforce the audited policy. For any other large table require explicit `chunk.field/type/low/high` and `key_fields`; never guess a composite key.

Use technical SAP GUI control IDs and verify each value by reading it back. Stop on missing controls, unknown dialogs, locked files, layout mismatches, duplicate keys, chunk gaps, or partial exports. Preserve successful part files and report partial/failed status without claiming a complete result.
