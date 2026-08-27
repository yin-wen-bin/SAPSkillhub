# Target validation — 2026-08-26

Scope: strictly read-only, bounded ADT Data Preview checks required by SAPBusinessAgents `internal-order-project-control` version 0.2.0. Raw rows, connection details, SQL, credentials, and full business identifiers remain only in ignored local artifacts.

## Results

- AUFK: `complete`, one exact masked sample, live stable key confirmed as `MANDT/AUFNR`.
- BPJA: `complete`, two rows for one masked control object/year, with the full live compound key returned as support fields.
- PRPS: the table and six requested fields were proven through DD02L/DD03L while a source/include endpoint returned HTTP 404. The new transparent-table metadata fallback produced a complete zero-row bounded query with key `MANDT/PSPNR`.
- COOI: key/context fields returned one complete row. Each amount field (`WHGBTR`, `WKGBTR`, `WOGBTR`, `WLGBTR`, `WTGBTR`) was confirmed by DDIC but rejected by Data Preview as `query_column_invalid` for both GET and the identical read-only POST.

## Verdict

The stable-key and transparent-table metadata repairs are validated, and PRPS is no longer blocked by the unpublished source/include endpoint. COOI commitment amounts remain unavailable on this target, so consumers must keep commitment evidence and EAC inconclusive; no amount may be substituted or inferred.
