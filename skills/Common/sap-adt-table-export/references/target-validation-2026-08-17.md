# Target-system validation — 2026-08-17

- Run ID: `bb739ea4-768f-4fd1-964f-6b8bd49aa265`
- Time (UTC): `2026-08-17T07:46:08.453221Z` to `2026-08-17T07:46:15.710744Z`
- Standard entrypoint: `python run.py --input input.json --output output.json`
- Tested dependency baseline: `requests==2.34.2`
- Transport: HTTPS with certificate validation enabled; exact ADT Data Preview endpoint; read-only POST compatibility fallback after GET returned 405
- Source: allowlisted table `TSTC`
- Bounded scope: fields `TCODE`, `PGMNA`; filter `TCODE EQ SE16N`; stable key `TCODE ASC`; `max_rows=2`
- Result: `complete`, `read_only=true`, `validated=true`, `source_complete=true`, `total_count_known=true`, `paging_complete=true`, `truncated=false`, one row, no validation issues
- Input SHA-256: `068f6f91bd8a8001d4772dd4f091d725a006c7ef65f33a28f7c8d8d515ca0f46`
- Live DDIC metadata SHA-256: `e2ff3ece1a5664a40637b60b1ab1866ad56825d000dc5c3deceec8c6454be6c7`
- Generated query SHA-256: `46f803d5ec5a398b7470172209ba19887bb1c1e658fd8f0e411c7c76f5e2a5ad`
- Returned row-set SHA-256: `3d59be23af73592a2d0efc89dedf3303ca51237b60fafb12ce56c9f051bc4627`
- Canonical output SHA-256: `c313f615f0745796c6dfa29d834888b33686c09fa22f3b72cb3b18554afb6727`

The raw input, protected profile, output rows, SAP URL, username, and credentials remain only in ignored local runtime storage and are not committed. This validates one exact bounded technical-data query; it does not claim broader source or business-process completeness.
