# Upstream review

- Repository: `shrek-abaper/sap-engineering-skill`
- Reviewed revision: `10c0fd4a0576e8fdc295fc03e84c5e5ea8bd5024`
- License at review time: MIT
- Reviewed files: `skills/sap-adt-cli/scripts/lib/client.py`, `handlers.py`, and `references/adt_api.md`
- Reused concepts: the allowlisted ADT Data Preview and DDIC/CDS source paths, `rowNumber`, the typed Data Preview Accept header, and the column-oriented XML response shape.
- Code reuse: none. This runtime is an independent implementation because the upstream CLI accepts arbitrary SQL, can disable TLS verification, and shares code with write, activation, and transport operations.
- Security delta: task input has no raw SQL or connection data; only one exact endpoint is available; redirects and disabled TLS are rejected; query text is generated and hashed but not logged.
