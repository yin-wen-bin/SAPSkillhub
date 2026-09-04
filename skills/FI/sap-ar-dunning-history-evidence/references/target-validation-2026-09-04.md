# Target validation — 2026-09-04

Verdict: **PASS**

The independent SAPSkillhub validation CLI used only semantic read-only ADT Data Preview POSTs and live DDIC GETs.

- `I_DunningEntryItem` exists, but the target ADT service rejects the complete item-key projection with HTTP 400.
- The fallback uses live-DDIC-pinned `MHND` and `MHNK` metadata.
- `MHND` metadata SHA-256: `37ae8cc2aaab3b3b260f42538f9af113f50baa5d6669d5a1366304da40e81c93`.
- `MHNK` metadata SHA-256: `ab7c6e7ab7972c83e9a992191077b44c2507472d4471e255d3f8f6046171801a`.
- Combined metadata SHA-256: `3bfba2b91ee6bccb334f15f4257515a36931f1cb7949ddf2bf48492085ef6969`.
- Non-zero sample: 3 hashed customers, 230 item rows, 230 normalized events.
- Complete-zero sample: 1 hashed absent customer, 0 events.
- Forced four-year date chunks proved multi-request paging without weakening the full identity-key check.
- Public events exclude document references and one-time-account values; those fields are emitted only in `restricted_rows`.
- Historical customer-master snapshot status remains `not_assessed`.

The ignored detailed validation artifact contains only hashed customer identifiers and counts; it contains no customer names, amounts, complete document numbers, credentials, or raw SAP rows.
