---
name: sap-production-order-cost-analysis
description: Read strictly bounded, read-only SAP production-order cost evidence for one manufacturing order, including AUFK object attribution, actual postings, and released plan/target/actual CDS values. Use for auditable production-order cost variance analysis; never use for cost calculation, variance calculation, settlement, revaluation, arbitrary CDS parameters, writes, or connection selection.
---

# SAP Production Order Cost Analysis

Run `python run.py --input input.json --output output.json`.

The caller supplies only `manufacturing_order`, optional `fiscal_year` and `period`, and `target_cost_variant`. The runtime owns the SAP connection and fixed ledger/currency-role policy. It validates AUFK attribution before accepting cost rows and reads only the released `I_MfgOrderActlPlanTgtLdgrCost` interface through a bounded, multiline ADT Data Preview POST. Read `references/evidence-contract.md` before interpreting a result.

Treat `complete` as complete only when order attribution, period scope, ledger, currency role, exact SAP total row count, and plan/target/actual interface evidence are all complete. Empty, truncated, count-mismatched, relationship-conflicting, or invalid amount evidence is `partial` and produces no cost details or totals. A complete ACDOCA actual-cost fallback without plan and target evidence is `partial`, never a zero target cost. Never derive target cost from standard price multiplied by order quantity.

Never expose connection data, credentials, generated SQL, or raw SAP response bodies. Preserve the output JSON and its adjacent SHA-256 manifest only in ignored evidence directories.
