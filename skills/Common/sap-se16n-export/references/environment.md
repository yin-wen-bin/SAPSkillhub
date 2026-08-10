# Environment and Compatibility

The primary entry is `scripts/se16n_export.py`. Install Python 3.12, `openpyxl==3.1.5`, and `pywin32` for live Windows execution. `control-profile.json` is a versioned technical-ID profile and must be revalidated after SAP release, screen-variant, theme, or customer-enhancement changes.

Install the tested package baseline with `python -m pip install -r scripts/requirements.txt`.

## Runtime

- Windows 10 or 11
- SAP GUI for Windows with GUI Scripting enabled on both client and server
- One authenticated SAP connection and idle session
- Authorization to run SE16N for the requested table and export ALV results
- Permission to write the target output directory
- A usable `.xlsx` file association. SAP GUI's XXL export may ask Windows which
  application should open the workbook; the Python process remains blocked until
  that OS dialog is resolved. Configure the association before unattended runs.

This skill does not support SAP GUI for HTML, browser-based Fiori apps, or SAP sessions that block SE16N by authorization.

## Entry-Point Boundary

`scripts/se16n_export.py` is the primary implementation. It controls `/nSE16N`,
selection fields, `GD-MAX_LINES`, ALV technical columns, XXL export, SAP internal
save fields, chunk probes, merging, and evidence generation. The technical IDs
are versioned in `references/control-profile.json` and must be validated against
the target system.

`scripts/se16n_export.vbs` only translates legacy named arguments and starts the
Python entry. An explicit legacy `/maxhits` selects full mode; values above
50,000 are capped to 50,000-row chunks. Omitting `/maxhits` selects the 100-row
validation mode.

## Windows Dialog Handling

If Windows or SAP GUI displays an overwrite prompt, file dialog, Excel prompt, file-lock dialog, or unknown security prompt, do not add screen coordinates, OCR, translated captions, or title-only matching.

Use the `sap-mb5b-export` approach as the pattern:

- Capture visible top-level windows and controls passively before clicking.
- Prefer stable control structure: window class, process ID, owner handle, control type, `control_id`, and `AutomationId`.
- Treat labels and titles as diagnostics, not selectors.
- Auto-confirm only known SAP GUI Scripting security prompts when the prompt text and standard OK control ID are both identified:
  - `A script is attempting to access SAP GUI.`
  - `A script is opening a connection to system:`
- Stop on ambiguous multi-button dialogs unless the user explicitly approved the specific action, such as overwrite.
- Save screenshots and control-tree JSON locally for diagnostics; do not commit them.

## Live-Run Checklist

1. Close existing workbooks with the same output filename.
2. Confirm the SAP session is idle and points to the expected system/client.
3. Run a low-hit validation export without `/maxhits`:

   ```powershell
   cscript //nologo scripts\se16n_export.vbs /table:MARA /outdir:"<LOCAL_WORKSPACE>\se16n-test" /file:"mara.xlsx"
   ```

4. Open the workbook and confirm the table content is expected.
5. Use the Python `--mode full` entry with bounded filters only after validation works.
6. Use a fresh filename unless the user explicitly approves overwriting existing files.

Full mode probes at 50,001 rows and recursively divides bounded ranges until
each final chunk contains at most 50,000 rows. It never requests the old INT4
maximum as a default.
