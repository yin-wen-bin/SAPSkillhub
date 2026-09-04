---
name: sap-ar-dunning-history-evidence
description: Read executed historical FI-AR dunning events for one company code, 1-50 customers, and an as-of date through a fixed target-validated read-only ADT profile.
---

# SAP AR Dunning History Evidence

Run `python run.py --input input.json --output output.json`. The Skill reads only the pinned MHNK/MHND fallback after independent live validation. It never reconstructs arbitrary historical customer-master snapshots and never treats an empty result as proof that a customer was never dunned.

Only `complete` results with `source_complete=true` may support absence claims within the requested scope. `sequence_status=ambiguous` means same-day events cannot be ordered from validated fields. The runtime must not infer business chronology from a lexicographic dunning run ID.
