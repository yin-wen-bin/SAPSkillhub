# Target validation — 2026-09-03

Status: `PASS`

## Sanitized preflight

- The released `I_BankStatementItem` candidate was rejected because it does not expose the required debit/credit indicator and excludes reversed statements.
- The registered Bank Reconciliation API was rejected because it is limited to unmatched reconciliation items.
- Fixed ADT candidate: `bank_statement_item_adt_v1`.
- Candidate and dependency metadata fingerprints are pinned in `source-profiles.json`.
- Read-only aggregate probes confirmed credit, reversed, and completed samples without storing payer, account, reference, amount, URL, or credential data.
- Stable-key ordering and a multi-page keyset probe completed without duplicate keys.

## Sanitized live validation

- Non-zero scope: company `1710`, value dates `2023-11-01..2023-11-30`.
- Direct SAP and standalone Skill returned 17 credit records with identical stable keys, statuses, dates, signed Decimal amounts, currencies, document relationships, masks, and paging completeness.
- The scope contained both reversed and completed samples.
- Forced five-row keyset pages reproduced the direct 17-row baseline without duplicates, gaps, or ordering drift.
- Exact-reference narrowing used a separate `2018-10-01..2018-10-31` value-date scope because the November 2023 credit records had empty bank references. One exact record matched; the reference itself is not stored.
- Authoritative-zero scope: company `1710`, value dates `2026-09-01..2026-09-03`; direct SAP and the Skill both returned complete zero results.
- Account masking, HMAC stability, adjacent-manifest integrity, and tracked-content privacy scans passed.

## Evidence hashes

- Direct non-zero rows SHA-256: `6f7eb2b831ca2af5a6fe0a51344aae1be1b1e9d5eb74bfeea03667ee5cf827bb`
- Skill non-zero receipts SHA-256: `a048f36595bcf32b7f9a4b6be1e97f646ab37bff96ea8d150fec368969ab3fdb`
- Exact-reference direct rows SHA-256: `da4b41930b1f0d02ed7e974fbc21c33a22ff47632f63851e0bed87fb17aad073`
- Exact-reference case SHA-256: `21ec6bd235f3ea2880129fc1b3ab5a46cf05c6471ee61379c9d83019fac71c2e`
- Authoritative-zero result SHA-256: `cc0fb8eb76a208cde5d1d0dcda6f110a5ff89f3a32b843b32f621d404241cad2`
- Source metadata SHA-256: `03232d2f8a5ba02f3647a36002d85ad20d4045a38c03307ba4aabbe8c51c6e46`
- Query template SHA-256: `8a7432163289969c1d59c35737451f91828719ae5af9da1dc5c7834b71aab513`

The active profile is enabled at version `2026-09-03.2`. Raw SAP responses, payer data, account values, bank references, business amounts, URLs, connection settings, and the HMAC key remain only in ignored local paths.
