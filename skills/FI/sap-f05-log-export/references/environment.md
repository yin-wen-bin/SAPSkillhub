# Environment and safety boundary

Use Windows, an authenticated SAP GUI for Windows session, SAP GUI Scripting, Python 3.12, `pywin32`, and `openpyxl==3.1.5`. F.05 screens, log selection, spool navigation, and ALV controls vary substantially between ECC and S/4HANA and between customer variants.

Copy the profile and validate technical IDs passively in the target system. Record the existing-log display action, test-run checkbox, every update/posting control, result counter, list or spool grid, and technical columns. Set `profile_status=validated` only after that review.

The script defaults to existing-log display. Test-run mode proves the test checkbox is on and posting/update controls are off. It never presses posting or update. Unknown dialogs fail closed. A zero-row result is accepted only from a numeric technical result counter.
