# Environment and Compatibility

## Runtime

- Windows 10 or 11
- SAP GUI for Windows with GUI Scripting enabled on both client and server
- One authenticated SAP connection and idle session
- Authorization to run SE16N for the requested table and export ALV results
- Permission to write the target output directory

This skill does not support SAP GUI for HTML, browser-based Fiori apps, or SAP sessions that block SE16N by authorization.

## Source Script Boundary

`scripts/se16n_export.vbs` is based on the recorded script from `<LOCAL_SKILL_PATH>\sap-se16n-export\se16n_export.vbs`. It controls:

- `/nse16n` navigation
- table input through `wnd[0]/usr/ctxtGD-TAB`
- Max. no. of hits through `wnd[0]/usr/txtGD-MAX_LINES`
- execution through toolbar button `wnd[0]/tbar[1]/btn[8]`
- ALV XXL export through `&MB_EXPORT` and `&XXL`
- SAP internal export/save controls `DY_PATH` and `DY_FILENAME`
- startup SAP GUI Scripting security prompts through `scripts/sap_security_prompt_helper.ps1`

Anything outside those SAP GUI Scripting controls and the known security-prompt helper is out of scope for the VBScript.

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
3. Run a low-hit validation export:

   ```powershell
   cscript //nologo scripts\se16n_export.vbs /table:MARA /maxhits:100 /outdir:"<LOCAL_WORKSPACE>\se16n-test" /file:"mara.xlsx" /securitytimeout:60
   ```

4. Open the workbook and confirm the table content is expected.
5. Increase `/maxhits` only after the validation export works.
6. Use a fresh filename unless the user explicitly approves overwriting existing files.

`2147483647` is the technical maximum commonly accepted by the SE16N max-hits field because it maps to an ABAP INT4-style value. It can still be impractical for large tables because runtime, memory, SAP authorization, dialog timeouts, export limits, and frontend spreadsheet limits may stop the export.
