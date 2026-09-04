# SAP AR Dunning History Evidence

This Skill reads executed dunning events for one company code, 1–50 customers, and an as-of date. The released `I_DunningEntryItem` view exists in the target, but ADT Data Preview cannot reliably project its complete item key, so the implementation uses a live-DDIC-validated read-only `MHNK/MHND` fallback.

It never changes SAP, reconstructs an arbitrary historical customer-master snapshot, or interprets an empty result as “never dunned.”
