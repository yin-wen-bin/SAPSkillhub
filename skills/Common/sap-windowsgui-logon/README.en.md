---
title: SAP Windows GUI Logon
summary: Prefer SAP GUI Scripting for logon and automatically fall back to SAP Shortcut before credential submission.
tags:
  - SAP GUI
  - logon automation
  - Windows
  - PowerShell
  - Python
  - SAP Shortcut
systems:
  - SAP ERP
  - SAP S/4HANA
  - SAP GUI for Windows
---

## Overview

This skill reads an SAP environment Description, Client, User, Password, and Logon Language from a local JSON configuration and uses two methods in order. It first logs on through pywin32 and SAP GUI Scripting. If Scripting is unavailable before credentials are submitted, it automatically falls back to `sapshcut.exe`.

The Scripting method uses SAP technical control IDs and verifies the client and authenticated user. The SAP Shortcut method does not require GUI Scripting, but can only confirm that the launch request was accepted; it cannot verify authentication.

## Use Cases

- Log on to a fixed SAP Logon environment on the local computer.
- Establish an authenticated session before another SAP GUI automation workflow.
- Validate the required login configuration fields and formats.
- Supply an explicit `saplogon.exe` path for a nonstandard SAP GUI installation.
- Attempt logon through SAP Shortcut when the target server disables SAP GUI Scripting.

## Prerequisites

- Windows with SAP GUI for Windows installed.
- Python 3.11 or later with `pywin32==311` from `scripts/requirements.txt`.
- SAP GUI Scripting enabled on client and server for the preferred method; `sapshcut.exe` for fallback.
- An SAP Logon connection whose Description exactly matches the configuration.
- A Description that maps to a System ID in `SAPUILandscape.xml`, or optional `System` in the configuration, for fallback.
- Authorization for the configured account to log on to the target SAP client.
- Windows PowerShell 5.1 or later.

## Usage

Copy the example configuration to the default per-user location:

```powershell
$configDirectory = Join-Path $env:USERPROFILE ".sap-windowsgui-logon"
New-Item -ItemType Directory -Path $configDirectory -Force | Out-Null
Copy-Item "assets\config.example.json" (Join-Path $configDirectory "config.json")
```

Edit `config.json` locally. Do not paste the password into chat, logs, or command-line arguments. Validate the file offline before the first live run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -ValidateOnly
```

Log on after validation succeeds:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1"
```

Pass a path when using a non-default configuration:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -ConfigPath "C:\secure\sap-logon.json"
```

## Inputs

The configuration must be UTF-8 JSON, and every field must be a string:

| Field | Required | Description |
| --- | --- | --- |
| `Description` | Yes | Exact Description of an SAP Logon connection. |
| `Client` | Yes | Three-digit client such as `100`; retain leading zeros. |
| `User` | Yes | SAP user name. |
| `Password` | Yes | SAP password; the script never prints this field. |
| `LogonLanguage` | Yes | Two-letter logon language such as `EN`, `DE`, or `ZH`. |
| `System` | No | Three-character SAP system ID; provide only when local Landscape mapping is unavailable. |

Optional command-line parameters:

| Parameter | Default | Description |
| --- | --- | --- |
| `-ConfigPath` | `%USERPROFILE%\.sap-windowsgui-logon\config.json` | Local configuration path. |
| `-TimeoutSeconds` | `60` | Total time allowed for SAP startup and authentication. |
| `-SapLogonPath` | Auto-discovered | Full `saplogon.exe` path for a nonstandard installation. |
| `-SapShcutPath` | Auto-discovered | Full `sapshcut.exe` path for a nonstandard installation. |
| `-DisableSapshcutFallback` | Off | Disable SAP Shortcut fallback to prevent password exposure in a child process command line. |
| `-ValidateOnly` | Off | Validate configuration without starting or controlling SAP. |

## Outputs

- Scripting success: exit code `0`, an authenticated SAP GUI session, and the method, Description, and Client; authentication is verified.
- SAP Shortcut launch success: exit code `0`, the method, System ID, and Client; authentication remains unverified.
- Failure: exit code `1`, a password-free reason, and the SAP window left available for manual inspection.
- Validation: confirms only Description, Client, and Logon Language; it does not print User or Password.

## Limitations

- The configuration contains a plaintext password. Keep it outside the repository and restrict its NTFS permissions to the intended Windows user.
- SAP Shortcut passes the password through a child process command line. A privileged local process may read it while the process runs; use `-DisableSapshcutFallback` when this risk is unacceptable.
- SAP GUI for HTML, SAP Fiori, web content in SAP Business Client, and non-Windows platforms are unsupported.
- `Description` must exactly match an existing SAP Logon connection.
- Automatic fallback occurs only before credential submission. A rejected password, post-submission error, or secondary dialog never causes a second attempt.
- When the server disables Scripting, the skill cannot verify whether SAP Shortcut completed authentication.
- The script stops on multiple-logon, password-change, license, or security dialogs and does not choose an option automatically.
- A rejected login is not retried because repeated failures can lock the SAP account.
- SSO, SNC, or other environments without the standard logon fields are not bypassed.

## Examples

Example configuration:

```json
{
  "Description": "QAS - Quality",
  "Client": "200",
  "User": "YOUR_SAP_USER",
  "Password": "YOUR_SAP_PASSWORD",
  "LogonLanguage": "EN"
}
```

Specify SAP Logon when it cannot be discovered automatically:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -SapLogonPath "C:\Program Files\SAP\FrontEnd\SAPgui\saplogon.exe"
```

Disable fallback when organizational policy prohibits command-line password exposure:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -DisableSapshcutFallback
```
