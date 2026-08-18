# Live target-system validation

1. Confirm a released API/OData route cannot provide the required evidence.
2. Copy `.env.example` to the Skill directory as `.env`, keep it ignored, and point `SAP_ADT_PROFILES_FILE` to a protected profiles file outside the repository. Do not rely on or export caller process environment variables.
3. Set one internal `default_profile` in the protected profiles file and enable `dynamic_objects` there. Choose one harmless table or CDS object and let the runtime confirm its returned fields, literal types, and ordered stable key from live ADT/DDIC metadata. Do not put the profile name in task input and do not guess a key.
4. Verify the endpoint is HTTPS and certificate verification remains enabled. If the internal CA is not in the operating-system trust store, reference a protected CA bundle. Never set verification to false.
5. Start with `max_rows: 2` and an equality filter expected to return zero or one row. Prefer technical metadata such as a single transaction-code row; avoid business, user, credential, HR, bank, or personal data.
6. Run `python run.py --input <input.json> --output <ignored-output.json>`. The CLI intentionally has no profile-selection option.
7. Accept target validation only when status is `complete`, `read_only=true`, `validated=true`, `source_complete=true`, there are no validation issues, and the adjacent manifest SHA-256 matches the output.
8. Retain the ignored output locally. Confirm output, manifest, stdout and stderr contain no profile name, SAP URL, client, username, credential, or connection path. Commit only a redacted validation note containing the object, bounded scope, row count, status, timestamp, and hashes; never commit raw rows, URLs, usernames, or credentials.

If validation fails, report its closed-set failure code. Do not fall back by allowing HTTP, disabling TLS, removing the bounded filter, accepting an inferred key, or raising `max_rows` above 30,000.
