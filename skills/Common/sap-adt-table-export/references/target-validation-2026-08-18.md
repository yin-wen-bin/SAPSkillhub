# Target-system validation — 2026-08-18

- Issue: `#22` connection ownership and caller decoupling
- Run ID: `5c4e32c7-6010-4236-9146-2dd726c84fc4`
- Time (UTC): `2026-08-18T14:06:24.208874Z` to `2026-08-18T14:06:26.863292Z`
- Standard entrypoint: `python run.py --input input.json --output output.json`
- Public input: profile-free; no connection selector, URL, client, credential, endpoint, or TLS setting
- Internal configuration: Skill-owned ignored `.env` and one protected internal `default_profile`; caller process environment was not used
- Tested dependency baseline: `requests==2.34.2`
- Transport: HTTPS with certificate validation enabled; read-only ADT Data Preview with live DDIC metadata validation
- Source: technical table `TSTC`
- Bounded scope: fields `TCODE`, `PGMNA`; filter `TCODE EQ SE16N`; stable key `TCODE ASC`; `max_rows=2`
- Result: `complete`, `read_only=true`, `validated=true`, `source_complete=true`, `total_count_known=true`, `paging_complete=true`, `truncated=false`, one row, no validation issues
- Connection leak scan: no internal profile name, SAP URL, client, username, credential, connection endpoint, metadata path, or caller override value in output, manifest, stdout, or stderr
- Input SHA-256: `8947d500284aef0ebb61ffd867bae998f3d5b9a366a69400048fe437d657b741`
- Live DDIC metadata SHA-256: `e2ff3ece1a5664a40637b60b1ab1866ad56825d000dc5c3deceec8c6454be6c7`
- Generated query SHA-256: `46f803d5ec5a398b7470172209ba19887bb1c1e658fd8f0e411c7c76f5e2a5ad`
- Returned row-set SHA-256: `3d59be23af73592a2d0efc89dedf3303ca51237b60fafb12ce56c9f051bc4627`
- Canonical output SHA-256: `621a30c9fed9a454cf24068d7613eb1402906879ba5a4f96354ef68051a796c7`
- Adjacent manifest verification: passed

The raw input, protected configuration, output rows, SAP connection details, and credentials remain only in ignored local runtime storage. This validates one exact bounded technical-data query and the profile-free connection contract; it does not claim broader source or business-process completeness.
