# Target validation — 2026-09-03

Status: `UNVALIDATED`

## Sanitized preflight

- The released `I_BankStatementItem` candidate was rejected because it does not expose the required debit/credit indicator and excludes reversed statements.
- The registered Bank Reconciliation API was rejected because it is limited to unmatched reconciliation items.
- Fixed ADT candidate: `bank_statement_item_adt_v1`.
- Candidate and dependency metadata fingerprints are pinned in `source-profiles.json`.
- Read-only aggregate probes confirmed credit, reversed, and completed samples without storing payer, account, reference, amount, URL, or credential data.
- Stable-key ordering and a multi-page keyset probe completed without duplicate keys.

## Validation gate

The profile remains disabled until direct SAP, standalone Skill, exact-reference narrowing, authoritative-zero, amount/currency reconciliation, privacy scans, and adjacent-manifest checks all match. No business identifiers or amounts will be added to this tracked report.
