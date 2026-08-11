# Environment and safety boundary

Use Windows, an already authenticated SAP GUI for Windows session, SAP GUI Scripting, Python 3.12, `pywin32`, and `openpyxl==3.1.5`. The supplied technical IDs are a fail-closed template, not a claim that every ECC/S/4HANA release uses the same dynpro.

Before the first live run, inspect controls passively and copy the profile. Validate the transaction, simulation checkbox, every posting/update checkbox, execute button, result counter, ALV grid, and technical column IDs. Keep `profile_status=requires-target-system-validation` until that review is recorded locally; the script refuses this template unless `--allow-unvalidated-profile` is explicitly supplied for a controlled validation run.

MR11 simulation must not post. The script never presses a posting control and aborts if a profiled forbidden checkbox is active or an unknown dialog appears. A zero-result run is accepted only when a numeric result-count control explicitly reads zero.
