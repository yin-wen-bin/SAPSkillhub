---
name: sap-bank-receipt-evidence
description: Read bounded, authoritative SAP bank-statement credit receipt evidence, including reversal and processing state. Use for bank receipt evidence by company code and value-date range. Do not use Payment Advice, infer customer or invoice allocation, or claim that a business receivable is settled.
---

# SAP Bank Receipt Evidence

Run `python run.py --input <ignored-input.json> --output <ignored-output.json>`. Both files must be under the repository `.artifacts` or `.codex-tmp` directory.

Use only the enabled, versioned source in `references/source-profiles.json`. Runtime source discovery, caller-selected connections, arbitrary fields or SQL, redirects, disabled TLS, and write operations are forbidden. The Skill fails closed while the target profile is unvalidated or its metadata fingerprint changes.

The date range always means inclusive bank value dates and cannot exceed 31 days or end in the future. An optional receipt reference is an exact `BankReference` filter; it never broadens the scope.

Return only SAP credit rows. Preserve reversal and posting status separately, keep Decimal signs, and group active and reversal-affected amounts without calculating net receipt, customer matching, invoice allocation, or business settlement. Read `references/evidence-contract.md` before interpreting zero or partial evidence.

Payer names and bank references may exist only in the requested output artifact. Never place them, raw accounts, SQL, SAP responses, URLs, connection names, or credentials in stdout, stderr, logs, tracked files, or error messages.
