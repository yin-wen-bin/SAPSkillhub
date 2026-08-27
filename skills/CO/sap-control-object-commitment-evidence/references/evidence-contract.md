# Evidence contract

- Periods are fiscal-year accounting periods `1..16`; a current snapshot is never substituted.
- `commitment_details` and `commitment_totals` exist only when source, scope, paging, stable keys, relations, amounts, currencies, roles, and value-type mappings are all complete.
- A technically complete zero-row result is not automatically zero. Explicit zero evidence requires the authoritative source to prove the full requested scope and a currency/currency-role context.
- Missing WBS or internal-order capability returns the mode-specific source-unavailable code. It never triggers source discovery, COOI projection, or an estimate.
- Signed finite Decimal values are preserved. No value is replaced with zero and no currency conversion is performed.
