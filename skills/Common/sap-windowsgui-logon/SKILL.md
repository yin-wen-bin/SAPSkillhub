---
name: sap-windowsgui-logon
description: Log on to a locally installed SAP GUI for Windows system from a JSON configuration, preferring pywin32 with SAP GUI Scripting and automatically falling back to sapshcut.exe when scripting is unavailable before credentials are submitted. Use when Codex needs to validate an SAP GUI logon configuration, start an SAP Logon connection, handle a server with GUI Scripting disabled, or authenticate a user through either supported method.
---

# SAP Windows GUI Logon

Use the bundled PowerShell launcher backed by `scripts/logon.py`. It selects between pywin32 SAP GUI Scripting and SAP Shortcut; do not reimplement the login with keystrokes, OCR, window titles, or fixed screen coordinates.

## Required Workflow

1. Use `%USERPROFILE%\.sap-windowsgui-logon\config.json` unless the user provides another configuration path.
2. If the configuration does not exist, copy `assets/config.example.json` to that location and ask the user to fill it locally. Never ask the user to paste a password into chat.
3. Do not read, print, summarize, or pass configuration values on the command line. Pass only the configuration file path to the script.
4. Validate the configuration before a first live login:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/logon.ps1 -ValidateOnly
   ```

5. Run the live login after validation:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/logon.ps1
   ```

6. Add `-ConfigPath "<LOCAL_CONFIG_PATH>\config.json"` only for a non-default configuration. Add `-SapLogonPath` or `-SapShcutPath` only when the executables cannot be discovered automatically.
7. Use the automatic SAP Shortcut fallback by default. Add `-DisableSapshcutFallback` only when the user rejects command-line password exposure.
8. Report the selected method and whether authentication was verified. Never expose the password or the full configuration content.

## Configuration Contract

The JSON file must contain the following required string fields:

- `Description`: exact, case-sensitive SAP Logon connection description.
- `Client`: three-digit SAP client, including leading zeros.
- `User`: SAP user name.
- `Password`: SAP password. Preserve leading or trailing characters.
- `LogonLanguage`: two-letter SAP logon language such as `EN`, `DE`, or `ZH`.

`System` is optional. Set it to the three-character SAP system ID when `Description` cannot be mapped uniquely through `%APPDATA%\SAP\Common\SAPUILandscape.xml` for the SAP Shortcut fallback.

Store the configuration outside the repository and restrict its NTFS permissions to the intended Windows user. The script never writes the configuration or logs its contents.

## Automation Rules

- Require Windows, SAP GUI for Windows, Python 3.11 or later, and `pywin32>=311`.
- Keep `scripts/requirements.txt` pinned to the tested baseline. The logon script
  accepts installed dependency versions that meet or exceed the minimum and runs
  the normal validation or login first. If that flow fails while the installed
  dependency version differs from the tested baseline, report both versions and
  recommend reproducing with `scripts/requirements.txt`.
- Try pywin32 SAP GUI Scripting first. Select the connection through `OpenConnection(Description)`, fill the login screen through SAP technical control IDs, and verify the authenticated client and user.
- Fall back only when Scripting is unavailable before credential submission, the server returns `DisabledByServer`, or no scriptable session/login controls become available.
- Before fallback, close the incomplete scripting connection when possible, resolve `Description` to a system ID, and launch `sapshcut.exe` with system, client, user, password, and language arguments.
- Never fall back after credentials were submitted, after SAP rejects a login, or when a secondary dialog appears.
- Treat SAP Shortcut success as launched but unverified because disabled Scripting prevents reading the authenticated session.
- Warn that SAP Shortcut places the password in the child process command line for a short period. Never print or log the command.
- Wait for SAP GUI and its login controls instead of using fixed sleeps as success criteria.
- Stop if SAP displays a secondary dialog after credential submission. Do not guess how to resolve multiple-logon, password-change, license, or security dialogs.
- Do not retry a rejected password automatically; repeated attempts can lock the SAP account.
- Treat the configuration file as sensitive even when validation fails.

## Result Contract

Scripting success means the created SAP session reports the requested client and a non-empty authenticated user. SAP Shortcut success means `sapshcut.exe` accepted the request, but authentication remains unverified. A validation-only run verifies configuration shape without starting or controlling SAP GUI. Any missing prerequisite, mapping error, rejected login, secondary dialog, or executable failure returns a nonzero exit code and leaves SAP windows available for manual inspection.
