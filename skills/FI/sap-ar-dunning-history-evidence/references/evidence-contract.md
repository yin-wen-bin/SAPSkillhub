# Evidence contract

- `MHND` is the item authority; `MHNK` supplies the effective dunning date.
- The relationship uses the complete shared run/customer/grouping key. `MHNK-BUSAB` is part of the header identity but is not an item relationship field; multiple conflicting headers for the shared key fail closed.
- `DunningRunDate` and `DunningRun` provide stable paging. The run identifier is not used to infer business chronology.
- The Skill returns all events in scope. Same-day multi-run events without a validated time or business sequence remain `ambiguous`.
- Historical customer dunning master data is `not_assessed`.
