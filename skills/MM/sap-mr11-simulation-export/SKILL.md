---
name: sap-mr11-simulation-export
description: Run SAP GUI for Windows transaction MR11 strictly in simulation or proposal mode and export read-only GR/IR adjustment candidates, exclusions, messages, totals, and hashed evidence. Use when exact MR11 standard logic is required and no posting or adjustment may be created.
---

# SAP MR11 Simulation Export

Read `references/environment.md`, then use `scripts/mr11_simulation_export.py`.

1. Start with `--run-mode validate`, one company code and a narrow PO range.
2. Confirm the system/client and adapt `references/control-profile.json` only from passive SAP GUI Scripting inspection.
3. Require either `--variant` or `--tolerance-policy`; never infer customer tolerance rules.
4. Let the script set and read back the simulation checkbox and clear every profiled posting/update checkbox.
5. Stop on missing safety controls, an active forbidden control, unknown dialogs, SAP errors, missing ALV fields, count mismatch, file instability, or a locked output.
6. Review the XLSX, CSV, log, and manifest. Treat `status=complete` as export completion, not approval to post.

Never press a posting, save-adjustment, update, or background-update control. Do not add an execution mode to this Skill. A future posting workflow must be a separate Skill with explicit human authorization.
