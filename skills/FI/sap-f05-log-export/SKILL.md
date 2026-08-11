---
name: sap-f05-log-export
description: Export an existing SAP F.05 run log or execute F.05 strictly as a non-posting test run through SAP GUI for Windows, capturing messages, valuation totals, document references, timestamps, and hashes. Use for foreign-currency valuation audit evidence when update/posting mode is forbidden.
---

# SAP F.05 Log Export

Read `references/environment.md`, then use `scripts/f05_log_export.py`.

1. Prefer `--mode existing-log` with an explicit run ID.
2. Use `--mode test-run` only with a target-system-validated control profile.
3. Confirm system/client and exact selections before execution.
4. Require the test-run checkbox for a test run and clear every profiled posting/update control.
5. Stop on missing safety controls, active forbidden controls, unknown dialogs, SAP errors, count mismatch, missing log fields, unstable files, or locked outputs.
6. Review the XLSX, CSV, log, and manifest; a complete test run is evidence only and must not be promoted to posting.

Never activate update, posting, batch-input creation, or accounting-document creation. Do not infer that generated document references mean this run created them; existing logs may reference documents created by an earlier authorized run.
