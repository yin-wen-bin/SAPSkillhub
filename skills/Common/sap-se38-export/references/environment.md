# Environment and Compatibility

## Runtime

- Windows 10 or 11
- SAP GUI for Windows with GUI Scripting enabled on both client and server
- One authenticated SAP connection and idle session
- Authorization to run SE38 and display or download the requested program source
- Permission to write the target output path

This skill does not support SAP GUI for HTML, browser-based Fiori apps, or SAP sessions that block SE38 or source display by authorization.

## Source Script Boundary

`scripts/se38_export.vbs` is based on the recorded script from `<LOCAL_SKILL_PATH>\sap-se38-export\se38_export.vbs`. It controls:

- `/nse38` navigation
- program input through `wnd[0]/usr/ctxtRS38M-PROGRAMM`
- the recorded SE38 display/open action through `wnd[0]/usr/btnSHOP`
- source download menu selection through `wnd[0]/mbar/menu[3]/menu[9]/menu[3]/menu[1]`
- SAP internal save controls `DY_PATH`, `DY_FILENAME`, and `DY_FILE_ENCODING`
- startup SAP GUI Scripting security prompts through `scripts/sap_security_prompt_helper.ps1`

Anything outside those SAP GUI Scripting controls and the known security-prompt helper is out of scope for the VBScript.

## Windows Dialog Handling

If Windows or SAP GUI displays an overwrite prompt, file dialog, Excel prompt, file-lock dialog, authorization message, or unknown security prompt, do not add screen coordinates, OCR, translated captions, or title-only matching.

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

1. Close existing files with the same output path.
2. Confirm the SAP session is idle and points to the expected system/client.
3. Run a validation export for a known small program:

   ```powershell
   cscript //nologo scripts\se38_export.vbs /program:SAPLSE16N /out:"<LOCAL_WORKSPACE>\se38-test\SAPLSE16N.abap"
   ```

4. Open the downloaded file and confirm the source content is expected.
5. Use a fresh output path unless the user explicitly approves overwriting an existing file.
