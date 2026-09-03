# Bank receipt evidence contract

## Evidence boundary

The Skill reports source bank-statement lines. A bank line, related accounting document, posting status, or completed indicator does not prove customer identity, invoice allocation, receivable clearing, or business settlement.

Payment Advice and the unmatched-only Bank Reconciliation API are not eligible sources. Runtime uses only the enabled target profile and never discovers or switches sources.

## Scope and completeness

- `date_from` and `date_to` are inclusive `ValueDate` bounds.
- `receipt_reference`, when present, is an exact `BankReference` equality filter.
- Only raw SAP debit/credit code `H` is eligible; a returned `S` row is a contract failure.
- `BankStatementShortID + BankStatementItem` is the stable key.
- A complete empty source means `complete/not_found` and `evidence_complete=true`.
- Missing totals, partial paging, metadata drift, unknown status, duplicate keys, invalid Decimal values, or missing required evidence make the result partial and clear all details and summaries.

`source_complete` means the fixed metadata and all keyset pages were complete. `paging_complete` means the key order, overlap boundary, declared totals, and cumulative rows agreed. `evidence_complete` additionally requires every returned row to satisfy the evidence contract.

## Reversal and posting

Bank-statement status `R` is reversed, `Q` is reversal in process, and `E` is reversal failed. Other pinned domain values are not reversed. Any unknown value fails closed.

Posting status is derived only from pinned SAP status fields. Reversal-affected credit rows remain inspectable but are excluded from active receipt totals. No net receipt or business conclusion is calculated.

## Account privacy

Partner IBAN is preferred over partner bank account. IBAN spaces are removed and letters uppercased; a generic account is only trimmed. The output mask exposes at most the last four characters. The hash is HMAC-SHA-256 over a domain-separated canonical value using the Skill-owned ignored key whose public identifier is `bank-receipt-hmac-v1`.

The local ignored `.env` must contain:

```text
SAP_BANK_RECEIPT_HMAC_KEY_ID=bank-receipt-hmac-v1
SAP_BANK_RECEIPT_HMAC_KEY_B64=<base64 of at least 32 random bytes>
```

Raw accounts, raw SAP responses, SQL, URLs, credentials, connection names, payer names, and bank references are forbidden in logs, tracked validation reports, and errors.
