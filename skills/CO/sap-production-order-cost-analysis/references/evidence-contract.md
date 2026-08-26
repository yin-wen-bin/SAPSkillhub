# Evidence contract

The runtime uses an exact manufacturing-order scope and the internally owned default SAP connection.

- AUFK proves `AUFNR -> OBJNR/KOKRS/BUKRS` attribution.
- `I_MfgOrderActlPlanTgtLdgrCost` is the sole executable authority for comparable plan, target, and actual costs by cost element, ledger, currency role, and selected fiscal periods. The analytical consumption view is semantic documentation only.
- ACDOCA is an actual-cost fallback and period-discovery source. It cannot prove target cost.
- `TargetCostVariant=1` is normalized to SAP value `001`.
- When no year or period is supplied, the exact-order ACDOCA postings determine the minimum and maximum posted fiscal periods; absence or incomplete paging blocks automatic scope derivation.
- Different ledgers, currencies, currency roles, and cost elements are never silently combined.
- Credit and reversal values retain the signs returned by SAP.

`source_complete=true` means every required bounded query has proven transport completeness, including an exact Data Preview `totalRows` match. `evidence_complete=true` additionally requires a proven order relationship, non-empty plan/target/actual rows, valid decimal amounts, and one comparable ledger/currency scope. Partial cost rows never produce details or totals.
