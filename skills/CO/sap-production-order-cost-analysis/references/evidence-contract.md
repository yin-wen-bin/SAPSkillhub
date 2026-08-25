# Evidence contract

The runtime uses an exact manufacturing-order scope and the internally owned default SAP connection.

- AUFK proves `AUFNR -> OBJNR/KOKRS/BUKRS` attribution.
- The released CDS is the authority for comparable plan, target, and actual costs by cost element, ledger, currency role, and selected fiscal periods.
- ACDOCA is an actual-cost fallback and period-discovery source. It cannot prove target cost.
- `TargetCostVariant=1` is normalized to SAP value `001`.
- When no year or period is supplied, the exact-order ACDOCA postings determine the minimum and maximum posted fiscal periods; absence or incomplete paging blocks automatic scope derivation.
- Different ledgers, currencies, currency roles, and cost elements are never silently combined.
- Credit and reversal values retain the signs returned by SAP.

`source_complete=true` means the exact bounded query sources are complete. `evidence_complete=true` additionally requires a proven order relationship and complete plan, target, and actual evidence.
