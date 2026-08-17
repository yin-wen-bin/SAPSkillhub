# Live target-system validation

1. Confirm a released API/OData route cannot provide the required evidence.
2. Create a protected profiles file outside the repository. Reference credential and HTTPS URL environment variables; never place their values in the task JSON or repository.
3. Approve one harmless table or CDS object, its returned fields, their types, at least one bounded-filter field, and its true stable key. Do not guess a key.
4. Verify the endpoint is HTTPS and certificate verification remains enabled. If the internal CA is not in the operating-system trust store, reference a protected CA bundle. Never set verification to false.
5. Start with `max_rows: 2` and an equality filter expected to return zero or one row. Prefer technical metadata such as a single transaction-code row; avoid business, user, credential, HR, bank, or personal data.
6. Run `python run.py --profiles <protected-profile.json> --input <input.json> --output <ignored-output.json>`.
7. Accept target validation only when status is `complete`, `read_only=true`, `validated=true`, `source_complete=true`, there are no validation issues, and the adjacent manifest SHA-256 matches the output.
8. Retain the ignored output locally. Commit only a redacted validation note containing the object, bounded scope, row count, status, timestamp, and hashes; never commit raw rows, URLs, usernames, or credentials.

If validation fails, keep Issue #20 open and report its closed-set failure code. Do not fall back by allowing HTTP, disabling TLS, widening the object allowlist, removing the bounded filter, or accepting an inferred key.
