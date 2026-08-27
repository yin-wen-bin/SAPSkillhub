# Evidence contract

- `complete/resolved`: both fixed sources returned exactly one row, live metadata hashes matched the profile, pagination was complete, and all relationship fields agreed.
- `partial/not_found`: all required source reads were complete and no exact object existed.
- `partial/ambiguous`: more than one row or any company/project/WBS relationship conflict occurred; `resolved_object` is null.
- `partial/source_unavailable`: metadata, source, authentication, authorization, transport, or paging evidence was unavailable.
- `failed/invalid_input`: the strict input or safety contract was rejected.

Only hashes and fixed issue messages are emitted for transport failures. Outputs never contain SAP URLs, credentials, connection names, raw responses, or caller-selected source controls.
